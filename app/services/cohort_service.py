"""Cohort search — structured + natural-language patient queries."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.config import MAX_PATIENT_RESULTS
from app.db.neo4j import get_session
from app.schemas.cohort import CohortSearchRequest, CohortSearchResponse, ParsedFilters, PatientSummary
from app.services.cohort_aggregation import count_matching_patients, run_aggregation
from app.services.cohort_aggregation_parser import (
    build_aggregation_interpretation,
    parse_aggregation_query,
)
from app.services.cohort_parser import (
    CONDITION_ALIASES,
    ParsedCohort,
    build_interpretation,
    parse_natural_query,
)
from app.schemas.cohort import AggregationResult, AggregationRow


def _merge_filters(req: CohortSearchRequest) -> ParsedCohort:
    parsed = parse_natural_query(req.query) if req.query else ParsedCohort()

    if req.condition:
        parsed.condition = req.condition
    if req.state:
        parsed.state = req.state
    if req.city:
        parsed.city = req.city
    if req.gender:
        parsed.gender = req.gender.lower()
    if req.minAge is not None:
        parsed.min_age = req.minAge
    if req.maxAge is not None:
        parsed.max_age = req.maxAge
    return parsed


def _age_from_birth(birth_date: Optional[str]) -> Optional[int]:
    if not birth_date:
        return None
    try:
        born = date.fromisoformat(birth_date[:10])
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        return None


def _condition_search_terms(condition: str) -> list[str]:
    term = condition.strip().lower()
    terms = [term]
    if term in CONDITION_ALIASES:
        terms.append(CONDITION_ALIASES[term])
    if term.endswith("ant") and len(term) > 5:
        terms.append(term[:-3] + "ancy")
    if term.startswith("preg"):
        terms.append("pregnan")
    return list(dict.fromkeys(terms))


def _resolve_concept(session, condition: str) -> Optional[dict[str, Any]]:
    for term in _condition_search_terms(condition):
        try:
            row = session.run(
                """
                CALL db.index.fulltext.queryNodes('conceptSearch', $q) YIELD node, score
                MATCH (node)<-[:CODED_AS]-(:Condition)
                RETURN node.system AS system, node.code AS code,
                       coalesce(node.display, node.text) AS label, score
                ORDER BY score DESC LIMIT 1
                """,
                q=term,
            ).single()
            if row:
                return dict(row)
        except Exception:
            pass

        row = session.run(
            """
            MATCH (c:Concept)<-[:CODED_AS]-(:Condition)
            WHERE toLower(coalesce(c.display, c.text, c.code)) CONTAINS toLower($q)
            WITH c,
                 CASE
                   WHEN toLower(coalesce(c.display, c.text, '')) CONTAINS 'normal pregnancy' THEN 0
                   WHEN toLower(coalesce(c.display, c.text, '')) CONTAINS 'finding' THEN 1
                   WHEN toLower(coalesce(c.display, c.text, '')) CONTAINS 'disorder' THEN 2
                   ELSE 3
                 END AS rank
            RETURN c.system AS system, c.code AS code,
                   coalesce(c.display, c.text) AS label, rank
            ORDER BY rank, label
            LIMIT 1
            """,
            q=term,
        ).single()
        if row:
            return dict(row)

    return None


def search_cohort(req: CohortSearchRequest) -> CohortSearchResponse:
    parsed = _merge_filters(req)
    limit = min(req.limit, MAX_PATIENT_RESULTS)
    agg = parse_aggregation_query(req.query or "", parsed) if req.query else None

    with get_session() as session:
        concept = None
        if parsed.condition:
            concept = _resolve_concept(session, parsed.condition)

        if agg and agg.is_aggregation:
            return _search_aggregation(session, agg, parsed, concept)

        patients, total_matched = _fetch_patient_list(session, parsed, concept, limit, req.offset)

    parsed_out = ParsedFilters(
        condition=parsed.condition,
        state=parsed.state,
        city=parsed.city,
        gender=parsed.gender,
        minAge=parsed.min_age,
        maxAge=parsed.max_age,
    )

    concept_out = None
    if concept:
        concept_out = {
            "conceptSystem": concept["system"],
            "conceptCode": concept["code"],
            "label": concept["label"],
        }

    return CohortSearchResponse(
        interpretation=build_interpretation(parsed),
        parsed=parsed_out,
        queryType="list",
        total=len(patients),
        totalMatched=total_matched,
        offset=req.offset,
        limit=limit,
        hasMore=(req.offset + len(patients)) < total_matched,
        patients=patients,
        concept=concept_out,
    )


def _search_aggregation(session, agg, parsed, concept) -> CohortSearchResponse:
    result = run_aggregation(session, agg, parsed, concept)
    parsed_out = ParsedFilters(
        condition=parsed.condition,
        state=parsed.state,
        city=parsed.city,
        gender=parsed.gender,
        minAge=parsed.min_age,
        maxAge=parsed.max_age,
    )
    interpretation = build_aggregation_interpretation(agg, parsed)
    if concept and concept.get("label"):
        interpretation = interpretation.replace(
            f"with {parsed.condition}",
            f"with {concept['label']}",
        ) if parsed.condition else f"{interpretation} ({concept['label']})"

    summary = result["summary"]
    if concept and concept.get("label") and parsed.condition:
        summary = f"{result['total']:,} patients with {concept['label']}"

    aggregation = AggregationResult(
        metric=agg.metric,
        target=agg.target,
        summary=summary,
        rows=[AggregationRow(label=r["label"], value=r["value"]) for r in result["rows"]],
    )
    return CohortSearchResponse(
        interpretation=interpretation,
        parsed=parsed_out,
        queryType="aggregation",
        total=int(result["total"]),
        totalMatched=int(result["total"]),
        patients=[],
        concept={
            "conceptSystem": concept["system"],
            "conceptCode": concept["code"],
            "label": concept["label"],
        } if concept else None,
        aggregation=aggregation,
    )


def _fetch_patient_list(session, parsed, concept, limit, offset=0):
    order_clause = "ORDER BY fhirId SKIP $offset LIMIT $limit"

    if concept:
        rows = session.run(
            f"""
            MATCH (concept:Concept {{system: $system, code: $code}})
            MATCH (concept)<-[:CODED_AS]-(cond:Condition)<-[:HAS_CONDITION]-(p:Patient)
            WHERE ($gender IS NULL OR p.gender = $gender)
              AND ($state IS NULL OR toLower(coalesce(p.state,'')) CONTAINS toLower($state)
                   OR toLower(coalesce(p.state,'')) = toLower($state))
              AND ($city IS NULL OR toLower(coalesce(p.city,'')) CONTAINS toLower($city))
            WITH DISTINCT p
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c2:Condition)-[:CODED_AS]->(cx:Concept)
            WITH p, collect(DISTINCT coalesce(cx.display, cx.text))[..5] AS conditions
            RETURN p.fhirId AS fhirId, p.gender AS gender, p.state AS state,
                   p.city AS city, p.birthDate AS birthDate, conditions
            {order_clause}
            """,
            system=concept["system"],
            code=concept["code"],
            gender=parsed.gender,
            state=parsed.state,
            city=parsed.city,
            limit=limit,
            offset=offset,
        )
    else:
        rows = session.run(
            f"""
            MATCH (p:Patient)
            WHERE ($gender IS NULL OR p.gender = $gender)
              AND ($state IS NULL OR toLower(coalesce(p.state,'')) CONTAINS toLower($state)
                   OR toLower(coalesce(p.state,'')) = toLower($state))
              AND ($city IS NULL OR toLower(coalesce(p.city,'')) CONTAINS toLower($city))
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(cx:Concept)
            WITH p, collect(DISTINCT coalesce(cx.display, cx.text))[..5] AS conditions
            RETURN p.fhirId AS fhirId, p.gender AS gender, p.state AS state,
                   p.city AS city, p.birthDate AS birthDate, conditions
            {order_clause}
            """,
            gender=parsed.gender,
            state=parsed.state,
            city=parsed.city,
            limit=limit,
            offset=offset,
        )

    patients: list[PatientSummary] = []
    for r in rows:
        age = _age_from_birth(r.get("birthDate"))
        if parsed.min_age is not None and (age is None or age < parsed.min_age):
            continue
        if parsed.max_age is not None and (age is None or age > parsed.max_age):
            continue
        patients.append(
            PatientSummary(
                fhirId=r["fhirId"],
                gender=r.get("gender"),
                state=r.get("state"),
                city=r.get("city"),
                birthDate=r.get("birthDate"),
                age=age,
                conditions=r.get("conditions") or [],
            )
        )

    total_matched = count_matching_patients(session, parsed, concept)
    if parsed.min_age is not None or parsed.max_age is not None:
        total_matched = len(patients)

    return patients, total_matched


def get_filter_options() -> dict[str, Any]:
    with get_session() as session:
        states = [r["state"] for r in session.run(
            "MATCH (p:Patient) WHERE p.state IS NOT NULL "
            "RETURN DISTINCT p.state AS state ORDER BY state"
        )]
        cities = [r["city"] for r in session.run(
            "MATCH (p:Patient) WHERE p.city IS NOT NULL "
            "RETURN DISTINCT p.city AS city ORDER BY city LIMIT 30"
        )]
        genders = [r["gender"] for r in session.run(
            "MATCH (p:Patient) WHERE p.gender IS NOT NULL "
            "RETURN DISTINCT p.gender AS gender"
        )]
        conditions = [dict(r) for r in session.run(
            """
            MATCH (c:Concept)<-[:CODED_AS]-(:Condition)
            RETURN c.system AS conceptSystem, c.code AS conceptCode,
                   coalesce(c.display, c.text) AS label
            ORDER BY label LIMIT 40
            """
        )]
    return {
        "states": states,
        "cities": cities,
        "genders": genders,
        "conditions": conditions,
    }
