from typing import Optional

from app.db.neo4j import get_session
from app.utils.expand_limits import MAX_GRAPH_EXPAND_LIMIT, resolve_expand_limit
from app.services.graph_connectivity import (
    RESOURCE_LABELS,
    build_patient_concept_hubs,
    build_patient_location_hub,
    build_place_patients,
    build_shared_concept_patients,
)
from app.services.graph_labels import wrap_graph_node
from app.services.patient_display import patient_graph_label

CLINICAL_CATEGORIES = (
    ("conditions", "HAS_CONDITION", "Conditions", "#38bdf8"),
    ("observations", "HAS_OBSERVATION", "Observations", "#34d399"),
    ("allergies", "HAS_ALLERGY", "Allergies", "#fb923c"),
    ("encounters", "HAS_ENCOUNTER", "Encounters", "#f472b6"),
)

GRAPH_LEAF_LIMIT = 20

def _concept_key(system: str, code: str) -> str:
    return f"{system}|{code}"


def build_patient_group_from_concept(
    system: str,
    code: str,
    rel: str = "HAS_CONDITION",
):
    label = RESOURCE_LABELS.get(rel, "Condition")
    with get_session() as session:
        res = session.run(
            f"""
            MATCH (concept:Concept {{system: $system, code: $code}})
            MATCH (concept)<-[:CODED_AS]-(:{label})<-[:{rel}]-(p:Patient)
            WITH DISTINCT p
            RETURN count(p) AS patientCount
            """,
            system=system,
            code=code,
        )
        row = res.single()
        if not row or row["patientCount"] == 0:
            return []

        key = _concept_key(system, code)
        return [wrap_graph_node({
                "id": f"ui:PatientGroup|{key}",
                "type": "PatientGroup",
                "label": f"Patients ({row['patientCount']})",
                "expandable": True,
                "context": {
                    "conceptSystem": system,
                    "conceptCode": code,
                    "resourceRel": rel,
                },
            })]

def build_gender_filters(system: str, code: str):
    with get_session() as session:
        res = session.run(
            """
            MATCH (concept:Concept {system: $system, code: $code})
            MATCH (concept)<-[:CODED_AS]-(c:Condition)<-[:HAS_CONDITION]-(p:Patient)
            WHERE p.gender IS NOT NULL
            WITH p.gender AS gender, count(DISTINCT p) AS cnt
            RETURN gender, cnt ORDER BY cnt DESC
            """,
            system=system,
            code=code,
        )
        key = _concept_key(system, code)
        return [wrap_graph_node({
                "id": f"ui:gender|{r['gender']}|{key}",
                "type": "Gender",
                "label": f"{str(r['gender']).capitalize()} ({r['cnt']})",
                "expandable": True,
                "context": {
                    "conceptSystem": system,
                    "conceptCode": code,
                    "gender": r["gender"],
                },
            }) for r in res]

def build_region_filters(system: str, code: str, gender: Optional[str]):
    with get_session() as session:
        res = session.run(
            """
            MATCH (concept:Concept {system: $system, code: $code})
            MATCH (concept)<-[:CODED_AS]-(c:Condition)<-[:HAS_CONDITION]-(p:Patient)
            WHERE ($gender IS NULL OR p.gender = $gender)
              AND p.state IS NOT NULL
            WITH p.state AS state, count(DISTINCT p) AS cnt
            RETURN state, cnt ORDER BY cnt DESC
            """,
            system=system,
            code=code,
            gender=gender,
        )
        key = _concept_key(system, code)
        return [wrap_graph_node({
                "id": f"ui:region|{r['state']}|{key}",
                "type": "Region",
                "label": f"{r['state']} ({r['cnt']})",
                "expandable": True,
                "context": {
                    "conceptSystem": system,
                    "conceptCode": code,
                    "gender": gender,
                    "state": r["state"],
                },
            }) for r in res]

def build_patients(
    system: str,
    code: str,
    gender: Optional[str],
    state: Optional[str],
    context: Optional[dict] = None,
):
    limit = resolve_expand_limit(context or {})
    with get_session() as session:
        res = session.run(
            """
            MATCH (concept:Concept {system: $system, code: $code})
            MATCH (concept)<-[:CODED_AS]-(c:Condition)<-[:HAS_CONDITION]-(p:Patient)
            WHERE ($gender IS NULL OR p.gender = $gender)
              AND ($state IS NULL OR p.state = $state)
            RETURN DISTINCT p.fhirId AS fhirId, p.patientId AS patientId, p.name AS name, p.gender AS gender, p.state AS state
            ORDER BY p.fhirId
            LIMIT $limit
            """,
            system=system,
            code=code,
            gender=gender,
            state=state,
            limit=limit,
        )
        return [wrap_graph_node({
                "id": f"ui:patient|{r['fhirId']}",
                "type": "Patient",
                "label": patient_graph_label(dict(r)),
                "name": r.get("name"),
                "patientId": r.get("patientId"),
                "gender": r.get("gender"),
                "state": r.get("state"),
                "expandable": True,
                "context": {"patientFhirId": r["fhirId"]},
            }) for r in res]

def build_patient_conditions(patient_fhir_id: str):
    with get_session() as session:
        res = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})-[:HAS_CONDITION]->(c:Condition)
            OPTIONAL MATCH (c)-[:CODED_AS]->(concept:Concept)
            RETURN c.fhirId AS fhirId, concept.system AS conceptSystem, concept.code AS conceptCode,
                   coalesce(concept.display, concept.text, 'Condition') AS label,
                   c.clinicalStatus AS clinicalStatus,
                   c.verificationStatus AS verificationStatus,
                   c.onsetDateTime AS onset
            LIMIT $limit
            """,
            pid=patient_fhir_id,
            limit=GRAPH_LEAF_LIMIT,
        )
        nodes = []
        for r in res:
            if not r.get("conceptSystem"):
                continue
            nodes.append(wrap_graph_node({
                "id": f"ui:Condition|{r['fhirId']}",
                "type": "Condition",
                "label": r["label"],
                "expandable": True,
                "context": {
                    "conceptSystem": r.get("conceptSystem"),
                    "conceptCode": r.get("conceptCode"),
                },
                "meta": {
                    "clinicalStatus": r.get("clinicalStatus"),
                    "verificationStatus": r.get("verificationStatus"),
                    "onset": r.get("onset"),
                },
            }))
        return nodes


def _observation_expand_limit(patient_fhir_id: str, context: dict | None = None) -> int:
    meta_total = ((context or {}).get("meta") or {}).get("total")
    if meta_total is not None:
        return max(1, min(int(meta_total), MAX_GRAPH_EXPAND_LIMIT))

    with get_session() as session:
        row = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})-[:HAS_OBSERVATION]->(o:Observation)
            RETURN count(o) AS c
            """,
            pid=patient_fhir_id,
        ).single()
        total = int(row["c"]) if row and row["c"] else 0
        return max(1, min(total, MAX_GRAPH_EXPAND_LIMIT))


def build_patient_observations(
    patient_fhir_id: str,
    limit: int | None = None,
    *,
    context: dict | None = None,
):
    if limit is None:
        limit = _observation_expand_limit(patient_fhir_id, context)

    with get_session() as session:
        res = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})-[:HAS_OBSERVATION]->(o:Observation)
            OPTIONAL MATCH (o)-[:CODED_AS]->(concept:Concept)
            WITH o, concept,
                 coalesce(toString(o.valueNum), o.valueString, '') AS rawValue
            RETURN o.fhirId AS fhirId, concept.system AS conceptSystem, concept.code AS conceptCode,
                   coalesce(concept.display, concept.text, 'Observation') AS label,
                   coalesce(toString(o.valueNum), o.valueString, '') AS value,
                   o.effectiveDateTime AS date
            ORDER BY o.effectiveDateTime DESC
            LIMIT $limit
            """,
            pid=patient_fhir_id,
            limit=limit,
        )
        nodes = []
        for r in res:
            value = r.get("value") or ""
            display = r["label"] or "Observation"
            if value:
                display = f"{display}: {value[:20]}" if len(value) > 20 else f"{display}: {value}"
            has_concept = bool(r.get("conceptSystem") and r.get("conceptCode"))
            nodes.append(wrap_graph_node({
                "id": f"ui:Observation|{r['fhirId']}",
                "type": "Observation",
                "label": display,
                "expandable": has_concept,
                "context": {
                    "conceptSystem": r.get("conceptSystem"),
                    "conceptCode": r.get("conceptCode"),
                } if has_concept else {},
                "meta": {"date": r.get("date"), "value": value or None},
            }))
        return nodes


def build_patient_allergies(patient_fhir_id: str, limit: int = GRAPH_LEAF_LIMIT):
    with get_session() as session:
        res = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})-[:HAS_ALLERGY]->(a:AllergyIntolerance)
            OPTIONAL MATCH (a)-[:CODED_AS]->(concept:Concept)
            RETURN a.fhirId AS fhirId, concept.system AS conceptSystem, concept.code AS conceptCode,
                   coalesce(concept.display, concept.text, 'Allergy') AS label,
                   a.clinicalStatus AS status
            LIMIT $limit
            """,
            pid=patient_fhir_id,
            limit=limit,
        )
        nodes = []
        for r in res:
            if not r.get("conceptSystem"):
                continue
            nodes.append(wrap_graph_node({
                "id": f"ui:Allergy|{r['fhirId']}",
                "type": "AllergyIntolerance",
                "label": r["label"],
                "expandable": True,
                "context": {
                    "conceptSystem": r.get("conceptSystem"),
                    "conceptCode": r.get("conceptCode"),
                },
                "meta": {"status": r.get("status")},
            }))
        return nodes


def build_patient_encounters(patient_fhir_id: str, limit: int = GRAPH_LEAF_LIMIT):
    with get_session() as session:
        res = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN e.fhirId AS fhirId,
                   coalesce(e.typeDisplay, e.class, 'Encounter') AS label,
                   e.periodStart AS start, e.periodEnd AS end, e.status AS status
            ORDER BY e.periodStart DESC
            LIMIT $limit
            """,
            pid=patient_fhir_id,
            limit=limit,
        )
        return [wrap_graph_node({
                "id": f"ui:Encounter|{r['fhirId']}",
                "type": "Encounter",
                "label": r["label"],
                "expandable": False,
                "context": {"encounterFhirId": r["fhirId"]},
                "meta": {
                    "start": r.get("start"),
                    "end": r.get("end"),
                    "status": r.get("status"),
                },
            }) for r in res]


def build_patient_clinical_categories(patient_fhir_id: str):
    """Bloom-style category hubs instead of dumping all clinical nodes at once."""
    with get_session() as session:
        row = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)
            WITH p, count(c) AS condCount
            OPTIONAL MATCH (p)-[:HAS_OBSERVATION]->(o:Observation)
            WITH p, condCount, count(o) AS obsCount
            OPTIONAL MATCH (p)-[:HAS_ALLERGY]->(a:AllergyIntolerance)
            WITH p, condCount, obsCount, count(a) AS allergyCount
            OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN condCount, obsCount, allergyCount, count(e) AS encCount
            """,
            pid=patient_fhir_id,
        ).single()

    if not row:
        return []

    counts = {
        "conditions": row["condCount"] or 0,
        "observations": row["obsCount"] or 0,
        "allergies": row["allergyCount"] or 0,
        "encounters": row["encCount"] or 0,
    }

    nodes = []
    nodes.extend(build_patient_location_hub(patient_fhir_id))

    for key, _rel, title, _color in CLINICAL_CATEGORIES:
        cnt = counts.get(key, 0)
        if cnt == 0:
            continue
        if key == "observations":
            suffix = f" ({cnt})"
        else:
            shown = min(cnt, GRAPH_LEAF_LIMIT)
            suffix = f" ({shown} of {cnt})" if cnt > GRAPH_LEAF_LIMIT else f" ({cnt})"
        nodes.append(wrap_graph_node({
            "id": f"ui:ClinicalCategory|{key}|{patient_fhir_id}",
            "type": "ClinicalCategory",
            "label": f"{title}{suffix}",
            "expandable": True,
            "context": {"patientFhirId": patient_fhir_id, "category": key},
            "meta": {"total": cnt, "category": key},
        }))
    return nodes


def build_clinical_category_expand(
    patient_fhir_id: str,
    category: str,
    context: dict | None = None,
):
    context = context or {}
    if category in ("observations", "conditions", "allergies"):
        limit = 40
        if category == "observations":
            limit = min(_observation_expand_limit(patient_fhir_id, context), 40)
        return build_patient_concept_hubs(patient_fhir_id, category, limit=limit)

    if category == "encounters":
        return build_patient_encounters(patient_fhir_id)

    return []