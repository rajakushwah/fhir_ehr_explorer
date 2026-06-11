"""Export mapped payloads to CSV and LOAD CSV into Neo4j (fast initial bulk)."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from ingestion.config import INGEST_CYPHER_BATCH_SIZE, resolve_import_dir
from ingestion.mappers.bundle_mapper import GraphPayload
from ingestion.writers.batch_writer import LABELS, PATIENT_REL_LABEL

logger = logging.getLogger("ingestion")

NODE_COLUMNS: dict[str, list[str]] = {
    "Organization": ["fhirId", "name"],
    "Location": ["fhirId", "name", "city", "state"],
    "Practitioner": ["fhirId", "name"],
    "Patient": ["fhirId", "name", "gender", "birthDate", "city", "state", "country", "postalCode", "race", "ethnicity"],
    "Encounter": [
        "fhirId", "status", "class", "periodStart", "periodEnd",
        "typeDisplay", "typeSystem", "typeCode",
    ],
    "Condition": [
        "fhirId", "status", "clinicalStatus", "verificationStatus",
        "onsetDateTime", "abatementDateTime",
    ],
    "Observation": [
        "fhirId", "status", "effectiveDateTime", "valueNum", "valueUnit",
        "valueString", "category",
    ],
    "Procedure": ["fhirId", "status", "performedDateTime"],
    "MedicationRequest": ["fhirId", "status", "authoredOn", "intent", "medSystem", "medCode", "medDisplay"],
    "AllergyIntolerance": ["fhirId", "status", "clinicalStatus", "verificationStatus", "type", "category"],
    "Immunization": ["fhirId", "status", "occurrenceDateTime"],
    "DiagnosticReport": ["fhirId", "status", "effectiveDateTime", "category"],
}


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(value)
    return str(value)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in fieldnames})
    return len(rows)


def export_payloads_to_csv(payloads: list[GraphPayload], import_dir: Path | None = None) -> Path:
    import_dir = import_dir or resolve_import_dir()
    import_dir.mkdir(parents=True, exist_ok=True)

    node_accum: dict[str, dict[str, dict]] = {label: {} for label in LABELS}
    patient_links: list[dict[str, str]] = []
    concept_links: list[dict[str, str]] = []
    encounter_links: list[dict[str, str]] = []
    org_links: list[dict[str, str]] = []
    location_links: list[dict[str, str]] = []

    for payload in payloads:
        for label in LABELS:
            for row in payload.nodes.get(label, []):
                node_accum[label][row["fhirId"]] = row
        patient_links.extend(payload.patient_links)
        concept_links.extend(payload.concept_links)
        encounter_links.extend(payload.encounter_links)
        org_links.extend(payload.org_links)
        location_links.extend(payload.location_links)

    counts: dict[str, int] = {}
    for label, columns in NODE_COLUMNS.items():
        rows = list(node_accum[label].values())
        counts[label] = _write_csv(import_dir / f"bulk_{label.lower()}.csv", columns, rows)

    counts["concept_links"] = _write_csv(
        import_dir / "bulk_concept_links.csv",
        ["resourceFhirId", "system", "code", "display"],
        concept_links,
    )
    counts["encounter_links"] = _write_csv(
        import_dir / "bulk_encounter_links.csv",
        ["resourceFhirId", "encounterFhirId"],
        encounter_links,
    )
    counts["org_links"] = _write_csv(
        import_dir / "bulk_org_links.csv",
        ["encounterFhirId", "orgFhirId"],
        org_links,
    )
    counts["location_links"] = _write_csv(
        import_dir / "bulk_location_links.csv",
        ["encounterFhirId", "locationFhirId"],
        location_links,
    )

    for rel in PATIENT_REL_LABEL:
        rel_rows = [row for row in patient_links if row["rel"] == rel]
        counts[rel] = _write_csv(
            import_dir / f"bulk_{rel.lower()}.csv",
            ["patientFhirId", "resourceFhirId"],
            rel_rows,
        )

    logger.info("[OK]    csv_export | dir=%s | counts=%s", import_dir, counts)
    return import_dir


def _load_nodes(session, label: str, columns: list[str], filename: str) -> None:
    numeric_cols = {"valueNum"}
    set_parts = []
    for col in columns:
        if col == "fhirId":
            continue
        if col in numeric_cols:
            set_parts.append(
                f"n.{col} = CASE WHEN row.{col} <> '' THEN toFloat(row.{col}) ELSE null END"
            )
        else:
            set_parts.append(
                f"n.{col} = CASE WHEN row.{col} <> '' THEN row.{col} ELSE null END"
            )
    set_clause = ", ".join(set_parts)

    session.run(
        f"""
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE (n:{label} {{fhirId: row.fhirId}})
        SET {set_clause}
        """,
        file=f"file:///{filename}",
        _log_op=f"bulk_load/{label}",
    ).consume()


BULK_TX_ROWS = max(INGEST_CYPHER_BATCH_SIZE, 5000)


def _load_csv_in_transactions(
    session,
    filename: str,
    inner_cypher: str,
    op_name: str,
    *,
    batch_size: int = BULK_TX_ROWS,
) -> None:
    """Run large LOAD CSV operations in sub-transactions (avoids single huge tx)."""
    session.run(
        f"""
        LOAD CSV WITH HEADERS FROM $file AS row
        CALL {{
            WITH row
            {inner_cypher}
        }} IN TRANSACTIONS OF $batchSize ROWS
        """,
        file=f"file:///{filename}",
        batchSize=batch_size,
        _log_op=op_name,
    ).consume()


def _load_rel_csv(session, filename: str, inner_cypher: str, op_name: str) -> None:
    _load_csv_in_transactions(session, filename, inner_cypher, op_name)


def _load_csv_concept_links(session, import_dir: Path) -> None:
    if not (import_dir / "bulk_concept_links.csv").exists():
        return
    _load_csv_in_transactions(
        session,
        "bulk_concept_links.csv",
        """
        MERGE (c:Concept {system: row.system, code: row.code})
        SET c.display = coalesce(row.display, c.display),
            c.text = coalesce(row.display, c.text)
        """,
        "bulk_load/concepts",
    )
    _load_csv_in_transactions(
        session,
        "bulk_concept_links.csv",
        """
        MATCH (c:Concept {system: row.system, code: row.code})
        MATCH (r {fhirId: row.resourceFhirId})
        MERGE (r)-[:CODED_AS]->(c)
        """,
        "bulk_load/concept_links",
    )


def _load_csv_relationships(session, import_dir: Path) -> None:
    for rel, target_label in PATIENT_REL_LABEL.items():
        csv_name = f"bulk_{rel.lower()}.csv"
        if (import_dir / csv_name).exists():
            _load_rel_csv(
                session,
                csv_name,
                f"""
                MATCH (p:Patient {{fhirId: row.patientFhirId}})
                MATCH (r:{target_label} {{fhirId: row.resourceFhirId}})
                MERGE (p)-[:{rel}]->(r)
                """,
                f"bulk_load/{rel}",
            )

    link_specs = [
        (
            "bulk_encounter_links.csv",
            """
            MATCH (r {fhirId: row.resourceFhirId})
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MERGE (r)-[:PART_OF_ENCOUNTER]->(e)
            """,
            "bulk_load/encounter_links",
        ),
        (
            "bulk_org_links.csv",
            """
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MATCH (o:Organization {fhirId: row.orgFhirId})
            MERGE (e)-[:AT_ORGANIZATION]->(o)
            """,
            "bulk_load/org_links",
        ),
        (
            "bulk_location_links.csv",
            """
            MATCH (e:Encounter {fhirId: row.encounterFhirId})
            MATCH (l:Location {fhirId: row.locationFhirId})
            MERGE (e)-[:AT_LOCATION]->(l)
            """,
            "bulk_load/location_links",
        ),
    ]
    for filename, inner_cypher, op_name in link_specs:
        if (import_dir / filename).exists():
            _load_rel_csv(session, filename, inner_cypher, op_name)


def load_csv_relationships_only(session, import_dir: Path | None = None) -> None:
    """Load patient and resource relationships only (skip node + concept CSV)."""
    import_dir = import_dir or resolve_import_dir()
    _load_csv_relationships(session, import_dir)
    logger.info("[OK]    csv_load_rels | dir=%s | batch=%d", import_dir, INGEST_CYPHER_BATCH_SIZE)


def load_csv_into_neo4j(session, import_dir: Path | None = None) -> None:
    import_dir = import_dir or resolve_import_dir()

    for label, columns in NODE_COLUMNS.items():
        csv_name = f"bulk_{label.lower()}.csv"
        if (import_dir / csv_name).exists():
            _load_nodes(session, label, columns, csv_name)

    _load_csv_concept_links(session, import_dir)
    _load_csv_relationships(session, import_dir)

    logger.info("[OK]    csv_load | dir=%s | batch=%d", import_dir, INGEST_CYPHER_BATCH_SIZE)
