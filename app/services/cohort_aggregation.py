"""Run Neo4j aggregation queries from parsed natural-language intent."""

from __future__ import annotations

from typing import Any, Optional

from app.services.cohort_aggregation_parser import ParsedAggregation
from app.services.cohort_parser import ParsedCohort
from app.services.location_filters import location_params, patient_location_where


def _patient_match_prefix(concept: Optional[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    if concept:
        return (
            """
            MATCH (concept:Concept {system: $system, code: $code})
            MATCH (concept)<-[:CODED_AS]-(:Condition)<-[:HAS_CONDITION]-(p:Patient)
            """,
            {"system": concept["system"], "code": concept["code"]},
        )
    return "MATCH (p:Patient)", {}


def _patient_where() -> str:
    return patient_location_where()


def _patient_params(parsed: ParsedCohort, extra: Optional[dict] = None) -> dict[str, Any]:
    return location_params(
        gender=parsed.gender,
        state=parsed.state,
        city=parsed.city,
        country=parsed.country,
        patient_id=parsed.patient_id,
        extra=extra,
    )


def run_aggregation(
    session,
    agg: ParsedAggregation,
    parsed: ParsedCohort,
    concept: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if agg.metric == "avg" and agg.target == "Patient":
        return _avg_patient_age(session, parsed, concept)

    if agg.target == "Patient":
        if agg.group_by == "gender":
            return _group_patient_count(session, parsed, concept, "gender")
        if agg.group_by == "state":
            return _group_patient_count(session, parsed, concept, "state")
        if agg.group_by == "city":
            return _group_patient_count(session, parsed, concept, "city")
        return _count_patients(session, parsed, concept)

    if agg.target == "Condition":
        return _count_resource(session, parsed, concept, "Condition", "HAS_CONDITION")

    if agg.target == "Observation":
        return _count_resource(session, parsed, concept, "Observation", "HAS_OBSERVATION")

    if agg.target == "Encounter":
        return _count_resource(session, parsed, concept, "Encounter", "HAS_ENCOUNTER")

    if agg.target == "AllergyIntolerance":
        return _count_resource(session, parsed, concept, "AllergyIntolerance", "HAS_ALLERGY")

    if agg.target == "Concept":
        return _count_concepts(session)

    return _count_patients(session, parsed, concept)


def _count_patients(session, parsed: ParsedCohort, concept: Optional[dict]) -> dict[str, Any]:
    prefix, extra = _patient_match_prefix(concept)
    row = session.run(
        prefix + _patient_where() + " RETURN count(DISTINCT p) AS value",
        **_patient_params(parsed, extra),
    ).single()
    value = int(row["value"]) if row else 0
    return {
        "rows": [{"label": "Total", "value": value}],
        "total": value,
        "summary": f"{value:,} patients",
    }


def _group_patient_count(
    session,
    parsed: ParsedCohort,
    concept: Optional[dict],
    field: str,
) -> dict[str, Any]:
    prefix, extra = _patient_match_prefix(concept)
    prop = f"p.{field}"
    rows = session.run(
        prefix
        + _patient_where()
        + f"""
        WITH p, coalesce(toString({prop}), 'Unknown') AS label
        RETURN label, count(DISTINCT p) AS value
        ORDER BY value DESC
        """,
        **_patient_params(parsed, extra),
    )
    result_rows = [{"label": r["label"], "value": int(r["value"])} for r in rows]
    total = sum(r["value"] for r in result_rows)
    return {
        "rows": result_rows,
        "total": total,
        "summary": f"{total:,} patients across {len(result_rows)} groups",
    }


def _count_resource(
    session,
    parsed: ParsedCohort,
    concept: Optional[dict],
    label: str,
    rel: str,
) -> dict[str, Any]:
    prefix, extra = _patient_match_prefix(concept)
    row = session.run(
        prefix
        + _patient_where()
        + f"""
        MATCH (p)-[:{rel}]->(r:{label})
        RETURN count(r) AS value
        """,
        **_patient_params(parsed, extra),
    ).single()
    value = int(row["value"]) if row else 0
    name = label.lower() + "s"
    return {
        "rows": [{"label": "Total", "value": value}],
        "total": value,
        "summary": f"{value:,} {name}",
    }


def _count_concepts(session) -> dict[str, Any]:
    row = session.run("MATCH (c:Concept) RETURN count(c) AS value").single()
    value = int(row["value"]) if row else 0
    return {
        "rows": [{"label": "Total", "value": value}],
        "total": value,
        "summary": f"{value:,} clinical concepts",
    }


def _avg_patient_age(session, parsed: ParsedCohort, concept: Optional[dict]) -> dict[str, Any]:
    prefix, extra = _patient_match_prefix(concept)
    rows = session.run(
        prefix
        + _patient_where()
        + """
        WITH p WHERE p.birthDate IS NOT NULL
        RETURN count(p) AS n,
               avg(duration.between(date(p.birthDate), date()).years) AS value
        """,
        **_patient_params(parsed, extra),
    ).single()
    n = int(rows["n"]) if rows and rows["n"] else 0
    avg = round(float(rows["value"]), 1) if rows and rows["value"] is not None else 0
    return {
        "rows": [{"label": "Average age", "value": avg}],
        "total": n,
        "summary": f"Average age {avg} years (n={n:,})",
    }


def count_matching_patients(session, parsed: ParsedCohort, concept: Optional[dict]) -> int:
    result = _count_patients(session, parsed, concept)
    return int(result["total"])
