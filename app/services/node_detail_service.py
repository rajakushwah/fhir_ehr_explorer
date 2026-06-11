"""Fetch node properties, neighbors, and relationships from Neo4j for the inspector."""

from __future__ import annotations

from typing import Any, Optional

from app.db.neo4j import get_session

SKIP_KEYS = {"elementId", "id", "identity"}

FHIR_LABELS = {
    "Patient",
    "Condition",
    "Observation",
    "AllergyIntolerance",
    "Encounter",
    "Procedure",
    "MedicationRequest",
    "Immunization",
    "DiagnosticReport",
    "Concept",
    "Place",
    "Organization",
    "Practitioner",
    "Location",
}


def _clean_props(props: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in props.items():
        if k in SKIP_KEYS or v is None or v == "":
            continue
        out[k] = v
    return out


def _resolve_match(node_type: str, context: dict[str, Any]) -> Optional[tuple[str, dict[str, Any]]]:
    if node_type == "Patient" and context.get("patientFhirId"):
        return "Patient", {"fhirId": context["patientFhirId"]}

    if node_type == "Condition" and context.get("conditionFhirId"):
        return "Condition", {"fhirId": context["conditionFhirId"]}
    if node_type == "Condition" and context.get("fhirId"):
        return "Condition", {"fhirId": context["fhirId"]}

    if node_type == "Observation" and context.get("observationFhirId"):
        return "Observation", {"fhirId": context["observationFhirId"]}
    if node_type == "Observation" and context.get("fhirId"):
        return "Observation", {"fhirId": context["fhirId"]}

    if node_type == "AllergyIntolerance" and context.get("allergyFhirId"):
        return "AllergyIntolerance", {"fhirId": context["allergyFhirId"]}

    if node_type == "Encounter" and context.get("encounterFhirId"):
        return "Encounter", {"fhirId": context["encounterFhirId"]}

    if node_type == "Concept" and context.get("conceptSystem") and context.get("conceptCode"):
        return "Concept", {"system": context["conceptSystem"], "code": context["conceptCode"]}

    if node_type == "Location" and context.get("placeKey"):
        return "Place", {"key": context["placeKey"]}

    if node_type == "Place" and context.get("placeKey"):
        return "Place", {"key": context["placeKey"]}

    return None


def _ui_properties(node_type: str, context: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    props = dict(meta or {})
    for k, v in (context or {}).items():
        if k not in props and v is not None and v != "":
            props[k] = v
    if node_type and "type" not in props:
        props["type"] = node_type
    return _clean_props(props)


def get_node_detail(node_type: str, context: dict[str, Any], meta: Optional[dict] = None) -> dict:
    resolved = _resolve_match(node_type, context)
    if not resolved:
        return {
            "type": node_type,
            "properties": _ui_properties(node_type, context, meta or {}),
            "fromDatabase": False,
            "neighborSummary": [],
            "relationshipSummary": [],
        }

    label, match_props = resolved
    with get_session() as session:
        row = session.run(
            f"MATCH (n:{label}) WHERE "
            + " AND ".join(f"n.{k} = ${k}" for k in match_props)
            + " RETURN properties(n) AS props LIMIT 1",
            **match_props,
        ).single()

        if not row:
            return {
                "type": node_type,
                "properties": _ui_properties(node_type, context, meta or {}),
                "fromDatabase": False,
                "neighborSummary": [],
                "relationshipSummary": [],
            }

        props = _clean_props(dict(row["props"]))
        element_key = list(match_props.values())[0]
        neighbor_summary = _neighbor_type_summary(session, label, match_props)
        rel_summary = _relationship_summary(session, label, match_props)

    return {
        "type": node_type,
        "neo4jLabel": label,
        "elementKey": str(element_key),
        "properties": props,
        "fromDatabase": True,
        "neighborSummary": neighbor_summary,
        "relationshipSummary": rel_summary,
    }


def _neighbor_type_summary(session, label: str, match_props: dict) -> list[dict]:
    where = " AND ".join(f"n.{k} = ${k}" for k in match_props)
    records = session.run(
        f"""
        MATCH (n:{label}) WHERE {where}
        OPTIONAL MATCH (n)-[r]->(m)
        WITH labels(m)[0] AS nodeType, count(DISTINCT m) AS cnt
        WHERE nodeType IS NOT NULL
        RETURN nodeType, cnt
        UNION
        MATCH (n:{label}) WHERE {where}
        OPTIONAL MATCH (n)<-[r]-(m)
        WITH labels(m)[0] AS nodeType, count(DISTINCT m) AS cnt
        WHERE nodeType IS NOT NULL
        RETURN nodeType, cnt
        """,
        **match_props,
    )
    merged: dict[str, int] = {}
    for r in records:
        merged[r["nodeType"]] = merged.get(r["nodeType"], 0) + int(r["cnt"])
    return [
        {"type": t, "count": c}
        for t, c in sorted(merged.items(), key=lambda x: (-x[1], x[0]))
    ]


def _relationship_summary(session, label: str, match_props: dict) -> list[dict]:
    where = " AND ".join(f"n.{k} = ${k}" for k in match_props)
    records = session.run(
        f"""
        MATCH (n:{label}) WHERE {where}
        OPTIONAL MATCH (n)-[r]->()
        WITH type(r) AS rel, count(r) AS cnt
        WHERE rel IS NOT NULL
        RETURN rel, cnt, 'out' AS direction
        UNION
        MATCH (n:{label}) WHERE {where}
        OPTIONAL MATCH (n)<-[r]-()
        WITH type(r) AS rel, count(r) AS cnt
        WHERE rel IS NOT NULL
        RETURN rel, cnt, 'in' AS direction
        """,
        **match_props,
    )
    merged: dict[str, int] = {}
    for r in records:
        merged[r["rel"]] = merged.get(r["rel"], 0) + int(r["cnt"])
    return [
        {"rel": rel, "count": cnt}
        for rel, cnt in sorted(merged.items(), key=lambda x: (-x[1], x[0]))
    ]


def get_node_neighbors(
    node_type: str,
    context: dict[str, Any],
    filter_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    resolved = _resolve_match(node_type, context)
    if not resolved:
        return []

    label, match_props = resolved
    where = " AND ".join(f"n.{k} = ${k}" for k in match_props)
    type_clause = "AND $filterType IN labels(m)" if filter_type else ""

    with get_session() as session:
        records = list(session.run(
            f"""
            MATCH (n:{label}) WHERE {where}
            MATCH (n)-[r]->(m)
            WHERE m IS NOT NULL {type_clause}
            RETURN labels(m)[0] AS nodeType,
                   type(r) AS rel,
                   'out' AS direction,
                   properties(m) AS props
            LIMIT $limit
            UNION
            MATCH (n:{label}) WHERE {where}
            MATCH (n)<-[r]-(m)
            WHERE m IS NOT NULL {type_clause}
            RETURN labels(m)[0] AS nodeType,
                   type(r) AS rel,
                   'in' AS direction,
                   properties(m) AS props
            LIMIT $limit
            """,
            filterType=filter_type,
            limit=limit,
            **match_props,
        ))

    neighbors = []
    for r in records:
        props = _clean_props(dict(r["props"]))
        node_type_name = r["nodeType"]
        key = props.get("fhirId") or props.get("key") or props.get("code") or "?"
        neighbors.append({
            "nodeType": node_type_name,
            "rel": r["rel"],
            "direction": r["direction"],
            "label": _neighbor_label(node_type_name, props),
            "properties": props,
            "key": str(key),
        })
    return neighbors[:limit]


def _neighbor_label(node_type: str, props: dict) -> str:
    if node_type == "Patient":
        g = props.get("gender") or "?"
        loc = props.get("city") or props.get("state") or "?"
        return f"Patient ({g}, {loc})"
    if node_type == "Concept":
        return props.get("display") or props.get("text") or props.get("code") or "Concept"
    if node_type == "Place":
        return props.get("label") or props.get("city") or "Place"
    for field in ("typeDisplay", "display", "text", "class", "status"):
        if props.get(field):
            return str(props[field])
    return props.get("fhirId") or node_type


def get_node_relationships(
    node_type: str,
    context: dict[str, Any],
    filter_rel: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    resolved = _resolve_match(node_type, context)
    if not resolved:
        return []

    label, match_props = resolved
    where = " AND ".join(f"n.{k} = ${k}" for k in match_props)
    rel_clause = "AND type(r) = $filterRel" if filter_rel else ""

    with get_session() as session:
        records = list(session.run(
            f"""
            MATCH (n:{label}) WHERE {where}
            MATCH (n)-[r]->(m)
            WHERE m IS NOT NULL {rel_clause}
            RETURN type(r) AS rel,
                   labels(n)[0] AS sourceType,
                   properties(n) AS sourceProps,
                   labels(m)[0] AS targetType,
                   properties(m) AS targetProps
            LIMIT $limit
            UNION
            MATCH (n:{label}) WHERE {where}
            MATCH (n)<-[r]-(m)
            WHERE m IS NOT NULL {rel_clause}
            RETURN type(r) AS rel,
                   labels(m)[0] AS sourceType,
                   properties(m) AS sourceProps,
                   labels(n)[0] AS targetType,
                   properties(n) AS targetProps
            LIMIT $limit
            """,
            filterRel=filter_rel,
            limit=limit,
            **match_props,
        ))

    rels = []
    for r in records:
        src_props = _clean_props(dict(r["sourceProps"]))
        tgt_props = _clean_props(dict(r["targetProps"]))
        rels.append({
            "rel": r["rel"],
            "sourceType": r["sourceType"],
            "sourceLabel": _neighbor_label(r["sourceType"], src_props),
            "sourceKey": str(src_props.get("fhirId") or src_props.get("key") or src_props.get("code") or "?"),
            "targetType": r["targetType"],
            "targetLabel": _neighbor_label(r["targetType"], tgt_props),
            "targetKey": str(tgt_props.get("fhirId") or tgt_props.get("key") or tgt_props.get("code") or "?"),
        })
    return rels[:limit]
