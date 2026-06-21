"""Cohort search — structured + natural-language patient queries."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.config import MAX_PATIENT_RESULTS
from app.db.neo4j import get_session
from app.schemas.cohort import CohortSearchRequest, CohortSearchResponse, ParsedFilters, PatientSummary
from app.services.cohort_aggregation import count_matching_patients, run_aggregation
from app.services.cohort_graph import build_graph_context
from app.services.cohort_aggregation_parser import (
    build_aggregation_interpretation,
    parse_aggregation_query,
)
from app.services.cohort_critical import search_critical_patients
from app.services.location_filters import location_params, patient_location_where
from app.services.cohort_critical_parser import (
    build_critical_interpretation,
    parse_critical_query,
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
    if req.country:
        parsed.country = req.country
    if req.gender:
        parsed.gender = req.gender.lower()
    if req.patientId:
        parsed.patient_id = req.patientId.strip() or None
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
    critical = parse_critical_query(req.query or "", parsed) if req.query else None
    agg = parse_aggregation_query(req.query or "", parsed) if req.query else None

    with get_session() as session:
        concept = None
        if parsed.condition:
            concept = _resolve_concept(session, parsed.condition)

        if critical and critical.is_critical_search:
            return _search_critical(session, parsed, critical, concept, limit, req.offset)

        if agg and agg.is_aggregation:
            return _search_aggregation(session, agg, parsed, concept)

        patients, total_matched = _fetch_patient_list(session, parsed, concept, limit, req.offset)

    return _build_list_response(parsed, concept, patients, total_matched, limit, req.offset)


def _build_list_response(parsed, concept, patients, total_matched, limit, offset):
    parsed_out = ParsedFilters(
        condition=parsed.condition,
        state=parsed.state,
        city=parsed.city,
        country=parsed.country,
        gender=parsed.gender,
        patientId=parsed.patient_id,
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
        offset=offset,
        limit=limit,
        hasMore=(offset + len(patients)) < total_matched,
        patients=patients,
        concept=concept_out,
        graphContext=build_graph_context(parsed, concept),
    )


def _search_critical(session, parsed, critical, concept, limit, offset) -> CohortSearchResponse:
    patients, total_matched = search_critical_patients(
        session, parsed, critical, limit, offset, concept
    )
    parsed_out = ParsedFilters(
        condition=parsed.condition,
        state=parsed.state,
        city=parsed.city,
        country=parsed.country,
        gender=parsed.gender,
        patientId=parsed.patient_id,
        minAge=parsed.min_age,
        maxAge=parsed.max_age,
        criticalMode=critical.severity,
    )
    concept_out = None
    if concept:
        concept_out = {
            "conceptSystem": concept["system"],
            "conceptCode": concept["code"],
            "label": concept["label"],
        }
    graph_ctx = build_graph_context(parsed, concept)
    graph_ctx["criticalMode"] = critical.severity
    return CohortSearchResponse(
        interpretation=build_critical_interpretation(critical, parsed),
        parsed=parsed_out,
        queryType="list",
        total=len(patients),
        totalMatched=total_matched,
        offset=offset,
        limit=limit,
        hasMore=(offset + len(patients)) < total_matched,
        patients=patients,
        concept=concept_out,
        graphContext=graph_ctx,
    )


def _search_aggregation(session, agg, parsed, concept) -> CohortSearchResponse:
    result = run_aggregation(session, agg, parsed, concept)
    parsed_out = ParsedFilters(
        condition=parsed.condition,
        state=parsed.state,
        city=parsed.city,
        country=parsed.country,
        gender=parsed.gender,
        patientId=parsed.patient_id,
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
        groupBy=agg.group_by,
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
        graphContext=build_graph_context(parsed, concept, agg.group_by),
    )


def _fetch_patient_list(session, parsed, concept, limit, offset=0):
    order_clause = "ORDER BY fhirId SKIP $offset LIMIT $limit"

    if concept:
        rows = session.run(
            f"""
            MATCH (concept:Concept {{system: $conceptSystem, code: $conceptCode}})
            MATCH (concept)<-[:CODED_AS]-(cond:Condition)<-[:HAS_CONDITION]-(p:Patient)
            {patient_location_where()}
            WITH DISTINCT p
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c2:Condition)-[:CODED_AS]->(cx:Concept)
            WITH p, collect(DISTINCT coalesce(cx.display, cx.text))[..5] AS conditions
            RETURN p.fhirId AS fhirId, p.patientId AS patientId, p.name AS name, p.gender AS gender, p.state AS state,
                   p.city AS city, p.country AS country, p.birthDate AS birthDate, conditions
            {order_clause}
            """,
            **location_params(
                gender=parsed.gender,
                state=parsed.state,
                city=parsed.city,
                country=parsed.country,
                patient_id=parsed.patient_id,
                concept_system=concept["system"],
                concept_code=concept["code"],
                extra={"limit": limit, "offset": offset},
            ),
        )
    else:
        rows = session.run(
            f"""
            MATCH (p:Patient)
            {patient_location_where()}
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(cx:Concept)
            WITH p, collect(DISTINCT coalesce(cx.display, cx.text))[..5] AS conditions
            RETURN p.fhirId AS fhirId, p.patientId AS patientId, p.name AS name, p.gender AS gender, p.state AS state,
                   p.city AS city, p.country AS country, p.birthDate AS birthDate, conditions
            {order_clause}
            """,
            **location_params(
                gender=parsed.gender,
                state=parsed.state,
                city=parsed.city,
                country=parsed.country,
                patient_id=parsed.patient_id,
                extra={"limit": limit, "offset": offset},
            ),
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
                patientId=r.get("patientId"),
                name=r.get("name"),
                gender=r.get("gender"),
                state=r.get("state"),
                city=r.get("city"),
                country=r.get("country"),
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
        countries = [r["country"] for r in session.run(
            "MATCH (p:Patient) WHERE p.country IS NOT NULL AND p.country <> '' "
            "RETURN DISTINCT p.country AS country ORDER BY country"
        )]
        if not countries:
            has_patients = session.run(
                "MATCH (p:Patient) RETURN count(p) AS c LIMIT 1"
            ).single()
            if has_patients and int(has_patients["c"]) > 0:
                countries = ["US"]
        genders = [r["gender"] for r in session.run(
            "MATCH (p:Patient) WHERE p.gender IS NOT NULL "
            "RETURN DISTINCT p.gender AS gender"
        )]
        conditions = [dict(r) for r in session.run(
            """
            MATCH (c:Concept)<-[:CODED_AS]-(:Condition)
            WITH coalesce(c.display, c.text) AS label, c
            ORDER BY label, c.code
            WITH label, collect({conceptSystem: c.system, conceptCode: c.code})[0] AS pick
            RETURN pick.conceptSystem AS conceptSystem, pick.conceptCode AS conceptCode, label
            ORDER BY label LIMIT 50
            """
        )]
    return {
        "states": states,
        "cities": cities,
        "countries": countries,
        "genders": genders,
        "conditions": conditions,
    }
