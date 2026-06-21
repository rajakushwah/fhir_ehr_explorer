"""Cohort-filter graph expansion (no concept required)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from app.db.neo4j import get_session
from app.services.graph_labels import wrap_graph_node
from app.services.location_filters import patient_location_drill_where, patient_location_where
from app.services.patient_display import patient_graph_label
from app.utils.expand_limits import resolve_expand_limit

RESOURCE_REL: dict[str, tuple[str, str]] = {
    "Observation": ("HAS_OBSERVATION", "Observation"),
    "Condition": ("HAS_CONDITION", "Condition"),
    "Encounter": ("HAS_ENCOUNTER", "Encounter"),
    "AllergyIntolerance": ("HAS_ALLERGY", "AllergyIntolerance"),
}


def cohort_key(filters: dict[str, Any]) -> str:
    payload = json.dumps(filters, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def build_graph_context(
    parsed,
    concept: Optional[dict[str, Any]],
    group_by: Optional[str] = None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "gender": parsed.gender,
        "state": parsed.state,
        "city": parsed.city,
        "country": parsed.country,
        "condition": parsed.condition,
        "patientId": parsed.patient_id,
    }
    if concept:
        filters["conceptSystem"] = concept["system"]
        filters["conceptCode"] = concept["code"]
        filters["conceptLabel"] = concept.get("label")

    ctx: dict[str, Any] = {
        "filters": filters,
        "cohortKey": cohort_key(filters),
    }
    if group_by:
        ctx["groupBy"] = group_by
    return ctx


def _match_prefix(filters: dict[str, Any]) -> str:
    if filters.get("conceptSystem") and filters.get("conceptCode"):
        return """
        MATCH (concept:Concept {system: $conceptSystem, code: $conceptCode})
        MATCH (concept)<-[:CODED_AS]-(:Condition)<-[:HAS_CONDITION]-(p:Patient)
        """
    return "MATCH (p:Patient)"


def _where_clause() -> str:
    return patient_location_where()


def _drill_where_clause() -> str:
    return patient_location_drill_where()


def _params(filters: dict[str, Any], extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    params = {
        "gender": filters.get("gender"),
        "state": filters.get("state"),
        "city": filters.get("city"),
        "country": filters.get("country"),
        "patientId": filters.get("patientId"),
        "conceptSystem": filters.get("conceptSystem"),
        "conceptCode": filters.get("conceptCode"),
    }
    if extra:
        params.update(extra)
    return params


def _filters_from_context(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("cohortFilters") or context.get("filters") or {}


def _resource_match_clause(context: dict[str, Any]) -> str:
    target = context.get("metricResource")
    if not target:
        return ""
    spec = RESOURCE_REL.get(target)
    if not spec:
        return ""
    rel, label = spec
    return f"MATCH (p)-[:{rel}]->(:{label})\n"


def _child_context(context: dict[str, Any], filters: dict[str, Any], key: str, **extra: Any) -> dict[str, Any]:
    child = {"cohortFilters": filters, "cohortKey": key, **extra}
    if context.get("metricResource"):
        child["metricResource"] = context["metricResource"]
    return child


def build_metric_resource_expand(node_type: str, context: dict[str, Any]) -> list[dict]:
    """Drill down from a resource count metric (e.g. 1,899 observations) into the cohort."""
    ctx = dict(context)
    filters = _filters_from_context(ctx)
    key = ctx.get("cohortKey") or cohort_key(filters)
    ctx["cohortFilters"] = filters
    ctx["cohortKey"] = key
    ctx["metricResource"] = node_type
    return build_cohort_gender_filters(ctx)


def build_cohort_patient_group(context: dict[str, Any]) -> list[dict]:
    filters = _filters_from_context(context)
    key = context.get("cohortKey") or cohort_key(filters)

    with get_session() as session:
        row = session.run(
            _match_prefix(filters)
            + _resource_match_clause(context)
            + _where_clause()
            + " RETURN count(DISTINCT p) AS patientCount",
            **_params(filters),
        ).single()
        count = int(row["patientCount"]) if row else 0
    if count == 0:
        return []

    return [wrap_graph_node({
        "id": f"ui:PatientGroup|cohort|{key}",
        "type": "PatientGroup",
        "label": f"Patients ({count:,})",
        "expandable": True,
        "context": {"cohortFilters": filters, "cohortKey": key},
    })]


def build_cohort_gender_filters(context: dict[str, Any]) -> list[dict]:
    filters = _filters_from_context(context)
    key = context.get("cohortKey") or cohort_key(filters)

    with get_session() as session:
        records = list(session.run(
            _match_prefix(filters)
            + _resource_match_clause(context)
            + _where_clause()
            + """
            AND p.gender IS NOT NULL
            WITH p.gender AS gender, count(DISTINCT p) AS cnt
            RETURN gender, cnt ORDER BY cnt DESC
            """,
            **_params(filters),
        ))

    return [wrap_graph_node({
        "id": f"ui:gender|{r['gender']}|cohort|{key}",
        "type": "Gender",
        "label": f"{str(r['gender']).capitalize()} ({int(r['cnt']):,})",
        "expandable": True,
        "context": _child_context(context, filters, key, gender=r["gender"]),
    }) for r in records]


def build_cohort_region_filters(context: dict[str, Any]) -> list[dict]:
    filters = _filters_from_context(context)
    key = context.get("cohortKey") or cohort_key(filters)
    gender = context.get("gender")

    with get_session() as session:
        records = list(session.run(
            _match_prefix(filters)
            + _resource_match_clause(context)
            + _where_clause()
            + """
            AND ($nodeGender IS NULL OR p.gender = $nodeGender)
            AND p.state IS NOT NULL
            WITH p.state AS state, count(DISTINCT p) AS cnt
            RETURN state, cnt ORDER BY cnt DESC
            """,
            **_params(filters, {"nodeGender": gender}),
        ))

    return [wrap_graph_node({
        "id": f"ui:region|{r['state']}|cohort|{key}",
        "type": "Region",
        "label": f"{r['state']} ({int(r['cnt']):,})",
        "expandable": True,
        "context": _child_context(
            context, filters, key, gender=gender, state=r["state"]
        ),
    }) for r in records]


def build_cohort_city_filters(context: dict[str, Any]) -> list[dict]:
    """City breakdown when state is already fixed in the cohort."""
    filters = _filters_from_context(context)
    key = context.get("cohortKey") or cohort_key(filters)
    gender = context.get("gender")

    with get_session() as session:
        records = list(session.run(
            _match_prefix(filters)
            + _resource_match_clause(context)
            + _where_clause()
            + """
            AND ($nodeGender IS NULL OR p.gender = $nodeGender)
            AND p.city IS NOT NULL AND p.city <> ''
            WITH p.city AS city, count(DISTINCT p) AS cnt
            RETURN city, cnt ORDER BY cnt DESC
            """,
            **_params(filters, {"nodeGender": gender}),
        ))

    return [wrap_graph_node({
        "id": f"ui:city|{r['city']}|cohort|{key}",
        "type": "Region",
        "label": f"{r['city']} ({int(r['cnt']):,})",
        "expandable": True,
        "context": _child_context(
            context, filters, key,
            gender=gender,
            state=filters.get("state") or context.get("state"),
            city=r["city"],
        ),
    }) for r in records]


def _cohort_filter_constrains_region(filters: dict[str, Any]) -> bool:
    return bool(filters.get("state") or filters.get("city"))


def _drill_params(
    filters: dict[str, Any],
    context: dict[str, Any],
    *,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    params = _params(
        filters,
        {
            "nodeGender": context.get("gender"),
            "nodeState": context.get("state"),
            "nodeCity": context.get("city"),
            "nodeCountry": context.get("country") or filters.get("country"),
        },
    )
    if limit is not None:
        params["limit"] = limit
    return params


def build_cohort_patients(context: dict[str, Any]) -> list[dict]:
    filters = _filters_from_context(context)
    limit = resolve_expand_limit(context)

    with get_session() as session:
        records = list(session.run(
            _match_prefix(filters)
            + _resource_match_clause(context)
            + _where_clause()
            + _drill_where_clause()
            + """
            RETURN DISTINCT p.fhirId AS fhirId, p.patientId AS patientId, p.name AS name, p.gender AS gender,
                   p.state AS state, p.city AS city
            ORDER BY coalesce(p.patientId, 999999999), p.fhirId
            LIMIT $limit
            """,
            **_drill_params(filters, context, limit=limit),
        ))

    return [wrap_graph_node({
        "id": f"ui:patient|{r['fhirId']}",
        "type": "Patient",
        "label": patient_graph_label(dict(r)),
        "name": r.get("name"),
        "patientId": r.get("patientId"),
        "gender": r.get("gender"),
        "city": r.get("city"),
        "state": r.get("state"),
        "expandable": True,
        "context": {"patientFhirId": r["fhirId"]},
    }) for r in records]
