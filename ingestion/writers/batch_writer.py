"""Write mapped bundle payloads to Neo4j — single transaction, combined Cypher."""

from __future__ import annotations

from typing import Any

from ingestion.config import INGEST_CYPHER_BATCH_SIZE
from ingestion.mappers.bundle_mapper import GraphPayload
from ingestion.patient_ids import allocate_patient_ids_tx

BATCH = INGEST_CYPHER_BATCH_SIZE

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

PATIENT_REL_LABEL = {
    "HAS_CONDITION": "Condition",
    "HAS_OBSERVATION": "Observation",
    "HAS_ENCOUNTER": "Encounter",
    "HAS_PROCEDURE": "Procedure",
    "HAS_MEDICATION": "MedicationRequest",
    "HAS_ALLERGY": "AllergyIntolerance",
    "HAS_IMMUNIZATION": "Immunization",
    "HAS_DIAGNOSTIC_REPORT": "DiagnosticReport",
}


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _run(tx, query: str, **params: Any) -> None:
    tx.run(query, **params)


def _write_patient_nodes(tx, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    prepared = [
        {"fhirId": row["fhirId"], "props": {k: v for k, v in row.items() if k != "fhirId"}}
        for row in rows
    ]
    merged_ids: list[str] = []
    for batch in _chunks(prepared, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MERGE (n:Patient {fhirId: row.fhirId})
            SET n += row.props
            """,
            rows=batch,
        )
        merged_ids.extend(row["fhirId"] for row in batch)
    allocate_patient_ids_tx(tx, merged_ids)


def _write_nodes(tx, label: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    prepared = [
        {"fhirId": row["fhirId"], "props": {k: v for k, v in row.items() if k != "fhirId"}}
        for row in rows
    ]
    for batch in _chunks(prepared, BATCH):
        _run(
            tx,
            f"""
            UNWIND $rows AS row
            MERGE (n:{label} {{fhirId: row.fhirId}})
            SET n += row.props
            """,
            rows=batch,
        )


def _write_patient_links(tx, links: list[dict[str, str]]) -> None:
    if not links:
        return
    grouped: dict[str, list[dict]] = {}
    for link in links:
        grouped.setdefault(link["rel"], []).append(link)

    for rel, batch_links in grouped.items():
        label = PATIENT_REL_LABEL[rel]
        for batch in _chunks(batch_links, BATCH):
            _run(
                tx,
                f"""
                UNWIND $rows AS row
                MATCH (p:Patient {{fhirId: row.patientFhirId}})
                MATCH (r:{label} {{fhirId: row.resourceFhirId}})
                MERGE (p)-[:{rel}]->(r)
                """,
                rows=batch,
            )


def _dedupe_concept_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for link in links:
        key = (link["resourceFhirId"], link["system"], link["code"])
        unique[key] = link
    return sorted(
        unique.values(),
        key=lambda row: (row["system"], row["code"], row["resourceFhirId"]),
    )


def merge_concepts_tx(tx, concepts: list[dict[str, str]]) -> None:
    """MERGE shared Concept nodes once (serial phase — avoids parallel deadlocks)."""
    if not concepts:
        return
    sorted_rows = sorted(concepts, key=lambda row: (row["system"], row["code"]))
    for batch in _chunks(sorted_rows, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MERGE (c:Concept {system: row.system, code: row.code})
            SET c.display = coalesce(row.display, c.display),
                c.text = coalesce(row.display, c.text)
            """,
            rows=batch,
        )


def link_concept_relationships_tx(tx, links: list[dict[str, str]]) -> None:
    """Link resources to pre-merged concepts (sorted for stable lock order)."""
    if not links:
        return
    rows = _dedupe_concept_links(links)
    for batch in _chunks(rows, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MATCH (c:Concept {system: row.system, code: row.code})
            MATCH (r {fhirId: row.resourceFhirId})
            MERGE (r)-[:CODED_AS]->(c)
            """,
            rows=batch,
        )


def _write_concept_links(tx, links: list[dict[str, str]]) -> None:
    """MERGE concepts and CODED_AS in one pass (single-writer / legacy path)."""
    if not links:
        return
    rows = _dedupe_concept_links(links)
    for batch in _chunks(rows, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MERGE (c:Concept {system: row.system, code: row.code})
            SET c.display = coalesce(row.display, c.display),
                c.text = coalesce(row.display, c.text)
            WITH c, row
            MATCH (r {fhirId: row.resourceFhirId})
            MERGE (r)-[:CODED_AS]->(c)
            """,
            rows=batch,
        )


def _write_encounter_links(tx, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MATCH (r {fhirId: row.resourceFhirId})
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MERGE (r)-[:PART_OF_ENCOUNTER]->(e)
            """,
            rows=batch,
        )


def _write_org_links(tx, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MATCH (o:Organization {fhirId: row.orgFhirId})
            MERGE (e)-[:AT_ORGANIZATION]->(o)
            """,
            rows=batch,
        )


def _write_location_links(tx, links: list[dict[str, str]]) -> None:
    if not links:
        return
    for batch in _chunks(links, BATCH):
        _run(
            tx,
            """
            UNWIND $rows AS row
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MATCH (l:Location {fhirId: row.locationFhirId})
            MERGE (e)-[:AT_LOCATION]->(l)
            """,
            rows=batch,
        )


def write_payload_tx(tx, payload: GraphPayload, *, concepts_premerged: bool = False) -> None:
    """Write one patient payload inside an existing transaction."""
    for label in LABELS:
        if label == "Patient":
            _write_patient_nodes(tx, payload.nodes.get(label, []))
        else:
            _write_nodes(tx, label, payload.nodes.get(label, []))

    _write_patient_links(tx, payload.patient_links)
    if concepts_premerged:
        link_concept_relationships_tx(tx, payload.concept_links)
    else:
        _write_concept_links(tx, payload.concept_links)
    _write_encounter_links(tx, payload.encounter_links)
    _write_org_links(tx, payload.org_links)
    _write_location_links(tx, payload.location_links)


def write_payloads_tx(
    tx,
    payloads: list[GraphPayload],
    *,
    concepts_premerged: bool = False,
) -> None:
    """Write multiple patient payloads in a single transaction."""
    for payload in payloads:
        write_payload_tx(tx, payload, concepts_premerged=concepts_premerged)


def write_payload(session, payload: GraphPayload) -> None:
    session.execute_write(write_payload_tx, payload)


def write_payloads_batch(
    session,
    payloads: list[GraphPayload],
    *,
    concepts_premerged: bool = False,
) -> None:
    session.execute_write(write_payloads_tx, payloads, concepts_premerged=concepts_premerged)


def merge_concepts_batch(session, concepts: list[dict[str, str]]) -> None:
    session.execute_write(merge_concepts_tx, concepts)
