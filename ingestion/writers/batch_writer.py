"""Write mapped bundle payloads to Neo4j in batched UNWIND transactions."""

from __future__ import annotations

from typing import Any

from ingestion.mappers.bundle_mapper import GraphPayload

BATCH = 500

LABELS = [
    "Organization",
    "Location",
    "Practitioner",
    "Patient",
    "Encounter",
    "Condition",
    "Observation",
    "Procedure",
    "MedicationRequest",
    "AllergyIntolerance",
    "Immunization",
    "DiagnosticReport",
]


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _write_nodes(session, label: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    prepared = [
        {"fhirId": row["fhirId"], "props": {k: v for k, v in row.items() if k != "fhirId"}}
        for row in rows
    ]
    for batch in _chunks(prepared, BATCH):
        session.run(
            f"""
            UNWIND $rows AS row
            MERGE (n:{label} {{fhirId: row.fhirId}})
            SET n += row.props
            """,
            rows=batch,
        )


def _write_concepts(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    unique = {(l["system"], l["code"]): l.get("display", l["code"]) for l in links}
    rows = sorted(
        [{"system": s, "code": c, "display": d, "text": d} for (s, c), d in unique.items()],
        key=lambda r: (r["system"], r["code"]),
    )
    for batch in _chunks(rows, BATCH):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (c:Concept {system: row.system, code: row.code})
            SET c.display = coalesce(row.display, c.display),
                c.text = coalesce(row.text, c.text)
            """,
            rows=batch,
        )


def _write_patient_links(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Patient {fhirId: row.patientFhirId})
            MATCH (r {fhirId: row.resourceFhirId})
            CALL apoc.merge.relationship(p, row.rel, {}, {}, r) YIELD rel
            RETURN count(rel)
            """,
            rows=batch,
        )


def _write_patient_links_no_apoc(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    grouped: dict[str, list[dict]] = {}
    for link in links:
        grouped.setdefault(link["rel"], []).append(link)

    rel_label = {
        "HAS_CONDITION": "Condition",
        "HAS_OBSERVATION": "Observation",
        "HAS_ENCOUNTER": "Encounter",
        "HAS_PROCEDURE": "Procedure",
        "HAS_MEDICATION": "MedicationRequest",
        "HAS_ALLERGY": "AllergyIntolerance",
        "HAS_IMMUNIZATION": "Immunization",
        "HAS_DIAGNOSTIC_REPORT": "DiagnosticReport",
    }

    for rel, batch_links in grouped.items():
        label = rel_label[rel]
        for batch in _chunks(batch_links, BATCH):
            session.run(
                f"""
                UNWIND $rows AS row
                MATCH (p:Patient {{fhirId: row.patientFhirId}})
                MATCH (r:{label} {{fhirId: row.resourceFhirId}})
                MERGE (p)-[:{rel}]->(r)
                """,
                rows=batch,
            )


def _write_concept_links(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (r {fhirId: row.resourceFhirId})
            MERGE (c:Concept {system: row.system, code: row.code})
            SET c.display = coalesce(row.display, c.display),
                c.text = coalesce(row.display, c.text)
            MERGE (r)-[:CODED_AS]->(c)
            """,
            rows=batch,
        )


def _write_encounter_links(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (r {fhirId: row.resourceFhirId})
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MERGE (r)-[:PART_OF_ENCOUNTER]->(e)
            """,
            rows=batch,
        )


def _write_org_links(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MATCH (o:Organization {fhirId: row.orgFhirId})
            MERGE (e)-[:AT_ORGANIZATION]->(o)
            """,
            rows=batch,
        )


def _write_location_links(session, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MATCH (l:Location {fhirId: row.locationFhirId})
            MERGE (e)-[:AT_LOCATION]->(l)
            """,
            rows=batch,
        )


def write_payload(session, payload: GraphPayload, use_apoc: bool = False) -> None:
    for label in LABELS:
        _write_nodes(session, label, payload.nodes.get(label, []))

    _write_concepts(session, payload.concept_links)

    if use_apoc:
        _write_patient_links(session, payload.patient_links)
    else:
        _write_patient_links_no_apoc(session, payload.patient_links)

    _write_concept_links(session, payload.concept_links)
    _write_encounter_links(session, payload.encounter_links)
    _write_org_links(session, payload.org_links)
    _write_location_links(session, payload.location_links)
