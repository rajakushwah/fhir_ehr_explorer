"""Shared graph hubs — patients connected through Place and Concept nodes."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from app.db.neo4j import get_session
from app.services.graph_labels import wrap_graph_node
from app.services.patient_display import patient_graph_label
from app.utils.expand_limits import resolve_expand_limit

RESOURCE_RELS = {
    "conditions": "HAS_CONDITION",
    "observations": "HAS_OBSERVATION",
    "allergies": "HAS_ALLERGY",
}

RESOURCE_LABELS = {
    "HAS_CONDITION": "Condition",
    "HAS_OBSERVATION": "Observation",
    "HAS_ALLERGY": "AllergyIntolerance",
}


def place_key(city: str, state: Optional[str], country: Optional[str]) -> str:
    payload = f"{city}|{state or ''}|{country or ''}".lower()
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def place_label(city: str, state: Optional[str], country: Optional[str]) -> str:
    parts = [city]
    if state:
        parts.append(state)
    if country:
        parts.append(country)
    return ", ".join(parts)


def build_patient_location_hub(patient_fhir_id: str) -> list[dict]:
    with get_session() as session:
        row = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})
            WHERE p.city IS NOT NULL AND p.city <> ''
            RETURN p.city AS city, p.state AS state, p.country AS country
            """,
            pid=patient_fhir_id,
        ).single()

    if not row:
        return []

    city, state, country = row["city"], row.get("state"), row.get("country")
    key = place_key(city, state, country)

    with get_session() as session:
        cnt = session.run(
            """
            MATCH (p:Patient)
            WHERE toLower(p.city) = toLower($city)
              AND ($state IS NULL OR p.state IS NULL OR toLower(p.state) = toLower($state))
              AND ($country IS NULL OR p.country IS NULL OR toLower(p.country) = toLower($country))
            RETURN count(p) AS c
            """,
            city=city,
            state=state,
            country=country,
        ).single()
        patient_count = int(cnt["c"]) if cnt else 1

    label = place_label(city, state, country)
    suffix = f" ({patient_count})" if patient_count > 1 else ""
    return [wrap_graph_node({
        "id": f"ui:Place|{key}",
        "type": "Location",
        "label": f"{label}{suffix}",
        "expandable": patient_count > 1,
        "context": {
            "placeKey": key,
            "city": city,
            "state": state,
            "country": country,
        },
        "meta": {"patientCount": patient_count, "shared": patient_count > 1},
    })]


def build_place_patients(context: dict[str, Any]) -> list[dict]:
    city = context.get("city")
    state = context.get("state")
    country = context.get("country")
    exclude = context.get("excludePatientFhirId")
    limit = resolve_expand_limit(context)

    if not city:
        return []

    with get_session() as session:
        records = list(session.run(
            """
            MATCH (p:Patient)
            WHERE toLower(p.city) = toLower($city)
              AND ($state IS NULL OR p.state IS NULL OR toLower(p.state) = toLower($state))
              AND ($country IS NULL OR p.country IS NULL OR toLower(p.country) = toLower($country))
              AND ($exclude IS NULL OR p.fhirId <> $exclude)
            RETURN DISTINCT p.fhirId AS fhirId, p.name AS name, p.gender AS gender, p.state AS state, p.city AS city
            ORDER BY p.fhirId
            LIMIT $limit
            """,
            city=city,
            state=state,
            country=country,
            exclude=exclude,
            limit=limit,
        ))

    return [wrap_graph_node({
        "id": f"ui:patient|{r['fhirId']}",
        "type": "Patient",
        "label": patient_graph_label(dict(r)),
        "expandable": True,
        "context": {"patientFhirId": r["fhirId"]},
        "meta": {"shared": True},
    }) for r in records]


def build_patient_concept_hubs(patient_fhir_id: str, category: str, limit: int = 40) -> list[dict]:
    rel = RESOURCE_RELS.get(category)
    label = RESOURCE_LABELS.get(rel or "")
    if not rel or not label:
        return []

    with get_session() as session:
        records = list(session.run(
            f"""
            MATCH (p:Patient {{fhirId: $pid}})-[:{rel}]->(r:{label})-[:CODED_AS]->(concept:Concept)
            WITH concept, count(r) AS patientCount
            RETURN concept.system AS system, concept.code AS code,
                   coalesce(concept.display, concept.text, 'Concept') AS label,
                   patientCount AS localCount
            ORDER BY localCount DESC, label
            LIMIT $limit
            """,
            pid=patient_fhir_id,
            limit=limit,
        ))

    nodes = []
    for r in records:
        if not r.get("system") or not r.get("code"):
            continue
        system, code = r["system"], r["code"]
        with get_session() as session:
            global_row = session.run(
                f"""
                MATCH (concept:Concept {{system: $system, code: $code}})
                MATCH (concept)<-[:CODED_AS]-(:{label})<-[:{rel}]-(p:Patient)
                RETURN count(DISTINCT p) AS globalCount
                """,
                system=system,
                code=code,
            ).single()
            global_count = int(global_row["globalCount"]) if global_row else int(r["localCount"])

        display = r["label"]
        local = int(r["localCount"])
        suffix = f" ({global_count} patients)" if global_count > 1 else f" ({local})"
        nodes.append(wrap_graph_node({
            "id": f"ui:Concept|{system}|{code}",
            "type": "Concept",
            "label": f"{display}{suffix}",
            "expandable": global_count > 1,
            "context": {
                "conceptSystem": system,
                "conceptCode": code,
                "resourceRel": rel,
                "originPatientFhirId": patient_fhir_id,
            },
            "meta": {
                "localCount": local,
                "globalCount": global_count,
                "shared": global_count > 1,
                "category": category,
            },
        }))
    return nodes


def build_shared_concept_patients(context: dict[str, Any]) -> list[dict]:
    system = context.get("conceptSystem")
    code = context.get("conceptCode")
    rel = context.get("resourceRel") or "HAS_CONDITION"
    label = RESOURCE_LABELS.get(rel)
    exclude = context.get("originPatientFhirId")
    limit = resolve_expand_limit(context)

    if not system or not code or not label:
        return []

    with get_session() as session:
        records = list(session.run(
            f"""
            MATCH (concept:Concept {{system: $system, code: $code}})
            MATCH (concept)<-[:CODED_AS]-(:{label})<-[:{rel}]-(p:Patient)
            WHERE ($exclude IS NULL OR p.fhirId <> $exclude)
            RETURN DISTINCT p.fhirId AS fhirId, p.name AS name, p.gender AS gender, p.city AS city, p.state AS state
            ORDER BY p.fhirId
            LIMIT $limit
            """,
            system=system,
            code=code,
            exclude=exclude,
            limit=limit,
        ))

    return [wrap_graph_node({
        "id": f"ui:patient|{r['fhirId']}",
        "type": "Patient",
        "label": patient_graph_label(dict(r)),
        "expandable": True,
        "context": {"patientFhirId": r["fhirId"]},
        "meta": {"shared": True, "viaConcept": True},
    }) for r in records]


def backfill_place_nodes() -> int:
    """Create shared Place nodes and LIVES_IN links from patient address properties."""
    with get_session() as session:
        result = session.run(
            """
            MATCH (p:Patient)
            WHERE p.city IS NOT NULL AND p.city <> ''
            WITH p,
                 p.city AS city,
                 coalesce(p.state, '') AS state,
                 coalesce(p.country, '') AS country,
                 p.city + '|' + coalesce(p.state, '') + '|' + coalesce(p.country, '') AS key
            MERGE (loc:Place {key: key})
            SET loc.city = city,
                loc.state = CASE WHEN state = '' THEN null ELSE state END,
                loc.country = CASE WHEN country = '' THEN null ELSE country END,
                loc.label = city
                    + CASE WHEN state <> '' THEN ', ' + state ELSE '' END
                    + CASE WHEN country <> '' THEN ', ' + country ELSE '' END
            MERGE (p)-[:LIVES_IN]->(loc)
            RETURN count(DISTINCT loc) AS places, count(*) AS links
            """
        ).single()
        return int(result["places"]) if result else 0
