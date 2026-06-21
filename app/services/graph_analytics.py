"""Comorbidity intelligence and similar-patient analytics."""

from __future__ import annotations

from typing import Any, Optional

from app.db.neo4j import get_session
from app.services.analytics_clustering import (
    betweenness_centrality,
    community_labels,
    connected_communities,
)
from app.services.location_filters import patient_location_where
from app.services.graph_labels import wrap_graph_node
from app.services.patient_display import patient_graph_label

CONCEPT_ID_PREFIX = "concept"


def concept_node_id(system: str, code: str) -> str:
    return f"{CONCEPT_ID_PREFIX}|{system}|{code}"


def _cohort_match(filters: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if filters.get("conceptSystem") and filters.get("conceptCode"):
        match = """
        MATCH (concept:Concept {system: $conceptSystem, code: $conceptCode})
        MATCH (concept)<-[:CODED_AS]-(:Condition)<-[:HAS_CONDITION]-(p:Patient)
        """
    else:
        match = "MATCH (p:Patient)"
    where = patient_location_where()
    params = {
        "gender": filters.get("gender"),
        "state": filters.get("state"),
        "city": filters.get("city"),
        "country": filters.get("country"),
        "patientId": filters.get("patientId"),
        "conceptSystem": filters.get("conceptSystem"),
        "conceptCode": filters.get("conceptCode"),
    }
    return match + where, params


def _interpretation(filters: dict[str, Any], patient_count: int) -> str:
    parts: list[str] = []
    if filters.get("gender"):
        parts.append(str(filters["gender"]))
    if filters.get("condition") or filters.get("conceptLabel"):
        parts.append(f"with {filters.get('conceptLabel') or filters.get('condition')}")
    if filters.get("city"):
        parts.append(f"in {filters['city']}")
    elif filters.get("state"):
        parts.append(f"in {filters['state']}")
    if filters.get("country"):
        parts.append(f"({filters['country']})")
    cohort = " ".join(parts) if parts else "all patients"
    return f"Comorbidity map for {patient_count:,} {cohort} patients"


def analyze_comorbidity(
    filters: dict[str, Any],
    *,
    min_co_occurrence: int = 2,
    max_concepts: int = 40,
) -> dict[str, Any]:
    match, params = _cohort_match(filters)
    params["minCoOccurrence"] = max(1, min_co_occurrence)
    params["maxConcepts"] = max(5, min(max_concepts, 80))

    with get_session() as session:
        patient_count = session.run(
            match + " RETURN count(DISTINCT p) AS c",
            **params,
        ).single()["c"]
        patient_count = int(patient_count or 0)
        if patient_count == 0:
            return {
                "patientCount": 0,
                "interpretation": _interpretation(filters, 0),
                "concepts": [],
                "edges": [],
                "communities": [],
                "bridges": [],
                "graphNodes": [],
                "graphEdges": [],
            }

        concept_rows = list(session.run(
            match
            + """
            MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(c:Concept)
            WITH c, count(DISTINCT p) AS patientCount
            ORDER BY patientCount DESC, coalesce(c.display, c.text, c.code)
            LIMIT $maxConcepts
            RETURN c.system AS system,
                   c.code AS code,
                   coalesce(c.display, c.text, c.code) AS label,
                   patientCount
            """,
            **params,
        ))

        edge_rows = list(session.run(
            match
            + """
            MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(c1:Concept)
            MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(c2:Concept)
            WHERE c1.system + '|' + c1.code < c2.system + '|' + c2.code
            WITH c1, c2, count(DISTINCT p) AS weight
            WHERE weight >= $minCoOccurrence
            RETURN c1.system AS sourceSystem,
                   c1.code AS sourceCode,
                   coalesce(c1.display, c1.text, c1.code) AS sourceLabel,
                   c2.system AS targetSystem,
                   c2.code AS targetCode,
                   coalesce(c2.display, c2.text, c2.code) AS targetLabel,
                   weight
            ORDER BY weight DESC
            LIMIT 300
            """,
            **params,
        ))

    concepts: list[dict[str, Any]] = []
    concept_index: dict[str, dict[str, Any]] = {}
    for row in concept_rows:
        node_id = concept_node_id(row["system"], row["code"])
        prevalence = round(int(row["patientCount"]) / patient_count, 4) if patient_count else 0.0
        concept = {
            "id": node_id,
            "system": row["system"],
            "code": row["code"],
            "label": row["label"],
            "patientCount": int(row["patientCount"]),
            "prevalence": prevalence,
        }
        concepts.append(concept)
        concept_index[node_id] = concept

    edges: list[dict[str, Any]] = []
    for row in edge_rows:
        source_id = concept_node_id(row["sourceSystem"], row["sourceCode"])
        target_id = concept_node_id(row["targetSystem"], row["targetCode"])
        if source_id not in concept_index or target_id not in concept_index:
            continue
        edges.append({
            "id": f"{source_id}~{target_id}",
            "sourceId": source_id,
            "targetId": target_id,
            "sourceLabel": row["sourceLabel"],
            "targetLabel": row["targetLabel"],
            "weight": int(row["weight"]),
            "label": f"{int(row['weight'])} patients",
        })

    node_ids = [concept["id"] for concept in concepts]
    min_edge_weight = max(min_co_occurrence, max(2, patient_count // 20))
    communities = connected_communities(node_ids, edges, min_weight=min_edge_weight)
    centrality = betweenness_centrality(node_ids, edges) if len(node_ids) >= 3 else {node: 0.0 for node in node_ids}

    bridge_threshold = 0.05
    bridges: list[dict[str, Any]] = []
    for concept in concepts:
        node_id = concept["id"]
        score = round(centrality.get(node_id, 0.0), 4)
        concept["communityId"] = communities.get(node_id, 0)
        concept["betweenness"] = score
        concept["isBridge"] = score >= bridge_threshold and int(concept["patientCount"]) < patient_count
        if concept["isBridge"]:
            bridges.append({
                "id": node_id,
                "label": concept["label"],
                "betweenness": score,
                "communityId": concept["communityId"],
                "patientCount": concept["patientCount"],
            })

    bridges.sort(key=lambda item: (-item["betweenness"], item["label"]))
    community_summaries = community_labels(communities, concepts)

    graph_nodes = [
        {
            "id": node_id,
            "type": "Concept",
            "label": concept["label"],
            "shortLabel": concept["label"],
            "fullLabel": f"{concept['label']}\n({concept['patientCount']} patients)",
            "expandable": False,
            "context": {
                "conceptSystem": concept["system"],
                "conceptCode": concept["code"],
            },
            "meta": {
                "patientCount": concept["patientCount"],
                "prevalence": concept["prevalence"],
                "communityId": concept["communityId"],
                "betweenness": concept["betweenness"],
                "isBridge": concept["isBridge"],
            },
        }
        for node_id, concept in concept_index.items()
    ]

    graph_edges = [
        {
            "id": edge["id"],
            "source": edge["sourceId"],
            "target": edge["targetId"],
            "relType": "CO_OCCURS",
            "label": edge["label"],
            "weight": edge["weight"],
        }
        for edge in edges
    ]

    return {
        "patientCount": patient_count,
        "interpretation": _interpretation(filters, patient_count),
        "filters": filters,
        "minCoOccurrence": min_co_occurrence,
        "concepts": concepts,
        "edges": edges,
        "communities": community_summaries,
        "bridges": bridges[:8],
        "graphNodes": graph_nodes,
        "graphEdges": graph_edges,
    }


def find_similar_patients(
    patient_fhir_id: str,
    filters: Optional[dict[str, Any]] = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    filters = filters or {}
    match, params = _cohort_match(filters)
    params["patientFhirId"] = patient_fhir_id
    params["limit"] = max(1, min(limit, 25))

    with get_session() as session:
        anchor_row = session.run(
            """
            MATCH (anchor:Patient {fhirId: $patientFhirId})
            RETURN anchor.fhirId AS fhirId,
                   anchor.patientId AS patientId,
                   anchor.name AS name,
                   anchor.gender AS gender,
                   anchor.city AS city,
                   anchor.state AS state
            """,
            patientFhirId=patient_fhir_id,
        ).single()
        if not anchor_row:
            return {
                "anchorPatient": None,
                "patients": [],
                "graphNodes": [],
                "graphEdges": [],
            }

        rows = list(session.run(
            match
            + """
            AND p.fhirId <> $patientFhirId
            MATCH (anchor:Patient {fhirId: $patientFhirId})-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(c:Concept)
            WITH anchor, p, collect(DISTINCT c) AS anchorConcepts
            MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(c2:Concept)
            WITH anchor, p, anchorConcepts, collect(DISTINCT c2) AS otherConcepts
            WITH anchor, p, anchorConcepts, otherConcepts,
                 [x IN anchorConcepts WHERE x IN otherConcepts] AS sharedConcepts,
                 [x IN anchorConcepts WHERE NOT x IN otherConcepts] AS anchorOnly,
                 [x IN otherConcepts WHERE NOT x IN anchorConcepts] AS otherOnly
            WITH p,
                 size(sharedConcepts) AS sharedCount,
                 size(anchorConcepts) + size(otherConcepts) - size(sharedConcepts) AS unionCount,
                 sharedConcepts,
                 anchorOnly,
                 otherOnly
            WHERE sharedCount > 0 AND unionCount > 0
            WITH p,
                 sharedCount,
                 unionCount,
                 sharedCount * 1.0 / unionCount AS score,
                 sharedConcepts,
                 anchorOnly,
                 otherOnly
            ORDER BY score DESC, sharedCount DESC, p.fhirId
            LIMIT $limit
            RETURN p.fhirId AS fhirId,
                   p.patientId AS patientId,
                   p.name AS name,
                   p.gender AS gender,
                   p.city AS city,
                   p.state AS state,
                   score,
                   sharedCount,
                   [x IN sharedConcepts | coalesce(x.display, x.text, x.code)] AS sharedLabels,
                   [x IN otherOnly | coalesce(x.display, x.text, x.code)] AS uniqueLabels,
                   [x IN anchorOnly | coalesce(x.display, x.text, x.code)] AS anchorUniqueLabels
            """,
            **params,
        ))

    anchor_props = dict(anchor_row)
    anchor_patient = {
        "fhirId": anchor_props["fhirId"],
        "name": anchor_props.get("name"),
        "patientId": anchor_props.get("patientId"),
        "gender": anchor_props.get("gender"),
        "city": anchor_props.get("city"),
        "state": anchor_props.get("state"),
        "label": patient_graph_label(anchor_props),
    }

    patients: list[dict[str, Any]] = []
    graph_nodes: list[dict[str, Any]] = [
        wrap_graph_node({
            "id": f"ui:patient|{anchor_patient['fhirId']}",
            "type": "Patient",
            "label": anchor_patient["label"],
            "name": anchor_patient.get("name"),
            "patientId": anchor_patient.get("patientId"),
            "gender": anchor_patient.get("gender"),
            "city": anchor_patient.get("city"),
            "state": anchor_patient.get("state"),
            "expandable": True,
            "context": {"patientFhirId": anchor_patient["fhirId"]},
            "meta": {"anchor": True},
        })["data"]
    ]
    graph_edges: list[dict[str, Any]] = []

    for row in rows:
        props = dict(row)
        score = round(float(props["score"]), 3)
        patient = {
            "fhirId": props["fhirId"],
            "name": props.get("name"),
            "patientId": props.get("patientId"),
            "gender": props.get("gender"),
            "city": props.get("city"),
            "state": props.get("state"),
            "label": patient_graph_label(props),
            "score": score,
            "sharedCount": int(props["sharedCount"]),
            "sharedConditions": list(props.get("sharedLabels") or []),
            "uniqueConditions": list(props.get("uniqueLabels") or []),
            "anchorUniqueConditions": list(props.get("anchorUniqueLabels") or []),
        }
        patients.append(patient)
        node_id = f"ui:patient|{patient['fhirId']}"
        node_data = wrap_graph_node({
            "id": node_id,
            "type": "Patient",
            "label": patient["label"],
            "name": patient.get("name"),
            "patientId": patient.get("patientId"),
            "gender": patient.get("gender"),
            "city": patient.get("city"),
            "state": patient.get("state"),
            "expandable": True,
            "context": {"patientFhirId": patient["fhirId"]},
            "meta": {
                "similarity": score,
                "sharedCount": patient["sharedCount"],
                "sharedConditions": patient["sharedConditions"],
            },
        })["data"]
        node_data["fullLabel"] = f"{node_data['fullLabel']}\n(similarity {int(score * 100)}%)"
        graph_nodes.append(node_data)
        graph_edges.append({
            "id": f"similar|{anchor_patient['fhirId']}|{patient['fhirId']}",
            "source": f"ui:patient|{anchor_patient['fhirId']}",
            "target": node_id,
            "relType": "SIMILAR_TO",
            "label": f"{int(score * 100)}% similar",
            "weight": score,
        })

    return {
        "anchorPatient": anchor_patient,
        "patients": patients,
        "graphNodes": graph_nodes,
        "graphEdges": graph_edges,
    }


def get_concept_cohort_patients(
    filters: dict[str, Any],
    concept_system: str,
    concept_code: str,
    *,
    concept_label: Optional[str] = None,
) -> dict[str, Any]:
    """Return cohort patients with vs without a selected condition concept."""
    match, params = _cohort_match(filters)
    params["targetSystem"] = concept_system
    params["targetCode"] = concept_code

    with get_session() as session:
        cohort_rows = list(session.run(
            match
            + """
            RETURN DISTINCT p.fhirId AS fhirId,
                   p.patientId AS patientId,
                   p.name AS name,
                   p.gender AS gender,
                   p.city AS city,
                   p.state AS state
            ORDER BY coalesce(p.name, p.fhirId)
            """,
            **params,
        ))

        with_rows = list(session.run(
            match
            + """
            MATCH (p)-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(target:Concept)
            WHERE target.system = $targetSystem AND target.code = $targetCode
            RETURN DISTINCT p.fhirId AS fhirId,
                   p.patientId AS patientId,
                   p.name AS name,
                   p.gender AS gender,
                   p.city AS city,
                   p.state AS state,
                   coalesce(target.display, target.text, target.code) AS conceptLabel
            ORDER BY coalesce(p.name, p.fhirId)
            """,
            **params,
        ))

    cohort_total = len(cohort_rows)
    with_ids = {row["fhirId"] for row in with_rows}
    label = concept_label or (with_rows[0]["conceptLabel"] if with_rows else concept_code)
    concept_id = concept_node_id(concept_system, concept_code)

    with_patients: list[dict[str, Any]] = []
    without_patients: list[dict[str, Any]] = []

    for row in cohort_rows:
        props = dict(row)
        entry = {
            "fhirId": props["fhirId"],
            "name": props.get("name"),
            "patientId": props.get("patientId"),
            "gender": props.get("gender"),
            "city": props.get("city"),
            "state": props.get("state"),
            "label": patient_graph_label(props),
            "hasCondition": props["fhirId"] in with_ids,
        }
        if entry["hasCondition"]:
            with_patients.append(entry)
        else:
            without_patients.append(entry)

    graph_nodes: list[dict[str, Any]] = [
        {
            "id": concept_id,
            "type": "Concept",
            "label": label,
            "shortLabel": label,
            "fullLabel": f"{label}\n({len(with_patients)}/{cohort_total} patients)",
            "expandable": False,
            "context": {"conceptSystem": concept_system, "conceptCode": concept_code},
            "meta": {
                "drilldownCenter": True,
                "withCount": len(with_patients),
                "cohortTotal": cohort_total,
            },
        }
    ]
    graph_edges: list[dict[str, Any]] = []

    all_patients = with_patients + without_patients
    for patient in all_patients:
        node_id = f"ui:patient|{patient['fhirId']}"
        graph_nodes.append(wrap_graph_node({
            "id": node_id,
            "type": "Patient",
            "label": patient["label"],
            "name": patient.get("name"),
            "patientId": patient.get("patientId"),
            "gender": patient.get("gender"),
            "city": patient.get("city"),
            "state": patient.get("state"),
            "expandable": True,
            "context": {"patientFhirId": patient["fhirId"]},
            "meta": {
                "hasCondition": patient["hasCondition"],
                "drilldownPatient": True,
            },
        })["data"])
        if patient["hasCondition"]:
            graph_edges.append({
                "id": f"drill|{patient['fhirId']}|{concept_code}",
                "source": node_id,
                "target": concept_id,
                "relType": "HAS_CONDITION",
                "label": "HAS_CONDITION",
            })

    return {
        "concept": {
            "id": concept_id,
            "system": concept_system,
            "code": concept_code,
            "label": label,
        },
        "cohortTotal": cohort_total,
        "withCount": len(with_patients),
        "withoutCount": len(without_patients),
        "withPatients": with_patients,
        "withoutPatients": without_patients,
        "summary": f"{len(with_patients)} of {cohort_total} patients have {label}",
        "graphNodes": graph_nodes,
        "graphEdges": graph_edges,
    }
