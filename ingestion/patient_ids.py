"""Sequential short patient IDs stored on Patient.patientId (e.g. 16101)."""

from __future__ import annotations

from typing import Any

PATIENT_ID_START = 16101
SEQ_NODE_ID = "global"
BATCH_SIZE = 200


def backfill_patient_ids(session, *, start: int = PATIENT_ID_START) -> dict[str, Any]:
    """Assign patientId to all patients missing one, ordered by fhirId."""
    max_row = session.run(
        "MATCH (p:Patient) WHERE p.patientId IS NOT NULL RETURN max(p.patientId) AS maxId"
    ).single()
    next_id = int(max_row["maxId"]) + 1 if max_row and max_row["maxId"] is not None else start

    missing = [
        row["fhirId"]
        for row in session.run(
            """
            MATCH (p:Patient)
            WHERE p.patientId IS NULL
            RETURN p.fhirId AS fhirId
            ORDER BY fhirId
            """
        )
    ]

    updated = 0
    for index in range(0, len(missing), BATCH_SIZE):
        batch = missing[index : index + BATCH_SIZE]
        rows = [
            {"fhirId": fhir_id, "patientId": next_id + index + offset}
            for offset, fhir_id in enumerate(batch)
        ]
        session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Patient {fhirId: row.fhirId})
            WHERE p.patientId IS NULL
            SET p.patientId = row.patientId
            """,
            rows=rows,
        ).consume()
        updated += len(batch)

    if updated:
        session.run(
            """
            MERGE (seq:PatientIdSeq {id: $seqId})
            SET seq.next = $next
            """,
            seqId=SEQ_NODE_ID,
            next=next_id + updated,
        ).consume()

    return {
        "updated": updated,
        "maxId": (next_id + updated - 1) if updated else None,
    }


def allocate_patient_ids_tx(tx, fhir_ids: list[str]) -> None:
    """Assign patientId to newly merged patients without one (same transaction)."""
    if not fhir_ids:
        return

    unique_ids = sorted(set(fhir_ids))
    need = tx.run(
        """
        UNWIND $fhirIds AS fhirId
        MATCH (p:Patient {fhirId: fhirId})
        WHERE p.patientId IS NULL
        RETURN p.fhirId AS fhirId
        ORDER BY fhirId
        """,
        fhirIds=unique_ids,
    ).data()

    if not need:
        return

    count = len(need)
    start_row = tx.run(
        """
        MERGE (seq:PatientIdSeq {id: $seqId})
        ON CREATE SET seq.next = $start
        SET seq.next = seq.next + $count
        RETURN seq.next - $count AS startId
        """,
        seqId=SEQ_NODE_ID,
        start=PATIENT_ID_START,
        count=count,
    ).single()
    start_id = int(start_row["startId"])

    assignments = [
        {"fhirId": row["fhirId"], "patientId": start_id + index}
        for index, row in enumerate(need)
    ]
    tx.run(
        """
        UNWIND $rows AS row
        MATCH (p:Patient {fhirId: row.fhirId})
        WHERE p.patientId IS NULL
        SET p.patientId = row.patientId
        """,
        rows=assignments,
    )
