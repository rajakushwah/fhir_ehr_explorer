"""CLI for FHIR bundle ingestion."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from app.logging_config import setup_logging
from ingestion.config import (
    INGEST_MAP_WORKERS,
    INGEST_TX_BATCH_SIZE,
    INGEST_USE_PROCESSES,
    INGEST_WRITE_WORKERS,
    resolve_import_dir,
)
from ingestion.config import resolve_import_dir
from ingestion.pipeline import (
    apply_schema,
    clear_database,
    ingest_directory,
    ingest_directory_bulk_csv,
)
from ingestion.writers.csv_bulk import load_csv_into_neo4j, load_csv_relationships_only
from app.db.neo4j import get_session

app = typer.Typer(help="EHR Data Explorer — Synthea FHIR ingestion")
setup_logging()
logger = logging.getLogger("ingestion")


@app.command("init-db")
def init_db(db_name: str = typer.Option("fhirexplorer", help="Neo4j database name (no underscores)")):
    """Create Neo4j database if it does not exist."""
    from neo4j import GraphDatabase
    from app.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database="system") as session:
        session.run(f"CREATE DATABASE {db_name} IF NOT EXISTS").consume()
    typer.echo(f"Database '{db_name}' ready")
    driver.close()


@app.command("clear-data")
def clear_data(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete all nodes and relationships in NEO4J_DATABASE (destructive)."""
    from app.config import NEO4J_DATABASE

    if not yes and not typer.confirm(
        f"This will DELETE ALL DATA in database '{NEO4J_DATABASE}'. Continue?"
    ):
        raise typer.Abort()

    summary = clear_database()
    typer.echo(
        f"Dropped and recreated database with {summary['nodes_before']:,} nodes and "
        f"{summary['relationships_before']:,} relationships removed "
        f"in {summary['ms']}ms"
    )
    typer.echo("Run init-schema before re-importing.")


@app.command("init-schema")
def init_schema(
    schema: Path = typer.Option(
        Path(__file__).resolve().parent / "schema" / "constraints.cypher",
        help="Path to constraints Cypher file",
    ),
):
    """Apply Neo4j constraints and indexes."""
    apply_schema(schema)
    typer.echo(f"Schema applied from {schema}")


@app.command("load")
def load(
    input_dir: Path = typer.Argument(..., help="Directory of Synthea patient Bundle JSON files"),
    workers: int = typer.Option(
        INGEST_WRITE_WORKERS,
        help="Parallel Neo4j write workers (default from INGEST_WRITE_WORKERS)",
    ),
    limit: int = typer.Option(None, help="Max number of bundles to ingest"),
):
    """
    Fast ingest: process-pool mapping + batched Neo4j transactions.

    Optimizations enabled via .env:
    - INGEST_USE_PROCESSES=true  (parallel JSON/FHIR mapping)
    - INGEST_MAP_WORKERS=4
    - INGEST_TX_BATCH_SIZE=3     (patients per transaction)
    - Observation filtering      (skip social-history, survey, etc.)
    """
    if not input_dir.is_dir():
        raise typer.BadParameter(f"Not a directory: {input_dir}")

    typer.echo(
        f"Mode=fast | map_workers={INGEST_MAP_WORKERS} | "
        f"use_processes={INGEST_USE_PROCESSES} | write_workers={workers} | "
        f"tx_batch={INGEST_TX_BATCH_SIZE}"
    )
    if workers > 4:
        typer.echo(
            "Warning: >4 write workers often deadlock on shared Concept nodes. "
            "Prefer --workers 2 or use load-bulk for full dataset imports."
        )
    try:
        results = ingest_directory(input_dir, workers=workers, limit=limit)
    except Exception as exc:
        typer.echo(f"Ingestion failed: {exc}", err=True)
        typer.echo(
            "Try: python -m ingestion.cli load-bulk <fhir_dir>  "
            "or re-run with --workers 1"
        )
        raise typer.Exit(code=1) from exc

    total_patients = sum(r["counts"].get("Patient", 0) for r in results)
    typer.echo(f"Ingested {len(results)} bundles, {total_patients} patients")
    if len(results) < 557 and limit is None:
        typer.echo(
            "Warning: expected ~557 bundles for the full Synthea sample. "
            "Run scripts\\verify_ingestion.py to check counts."
        )


@app.command("load-csv")
def load_csv(
    import_dir: Path = typer.Option(
        None,
        help="Neo4j import directory with bulk_*.csv files (default: auto-detect)",
    ),
):
    """LOAD CSV files already exported to the Neo4j import directory (skip mapping)."""
    resolved = import_dir or resolve_import_dir()
    if not resolved.is_dir():
        raise typer.BadParameter(f"Not a directory: {resolved}")
    typer.echo(f"Loading CSV from {resolved}")
    with get_session() as session:
        load_csv_into_neo4j(session, import_dir=resolved)
    typer.echo("CSV load complete. Run scripts\\verify_ingestion.py to verify.")


@app.command("load-csv-rels")
def load_csv_rels(
    import_dir: Path = typer.Option(
        None,
        help="Neo4j import directory with bulk_*.csv files (default: auto-detect)",
    ),
):
    """Load only relationship CSVs (HAS_CONDITION, etc.) — use when nodes exist but links are missing."""
    resolved = import_dir or resolve_import_dir()
    if not resolved.is_dir():
        raise typer.BadParameter(f"Not a directory: {resolved}")
    typer.echo(f"Loading relationship CSVs from {resolved}")
    with get_session() as session:
        load_csv_relationships_only(session, import_dir=resolved)
    typer.echo("Relationship load complete. Run scripts\\verify_ingestion.py to verify.")


@app.command("backfill-country")
def backfill_country(
    value: str = typer.Option("US", help="Country code to set on patients missing country"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Set patient.country on existing Patient nodes that lack it (Synthea default: US)."""
    if not yes and not typer.confirm(
        f"Set country='{value}' on all Patient nodes where country is missing?"
    ):
        raise typer.Abort()

    with get_session() as session:
        row = session.run(
            """
            MATCH (p:Patient)
            WHERE p.country IS NULL OR p.country = ''
            SET p.country = $value
            RETURN count(p) AS updated
            """,
            value=value,
        ).single()
        updated = int(row["updated"]) if row else 0
    typer.echo(f"Updated {updated:,} patients with country='{value}'")


@app.command("backfill-places")
def backfill_places(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Create shared Place nodes and LIVES_IN links from patient city/state/country."""
    if not yes and not typer.confirm(
        "Create Place nodes and LIVES_IN relationships from patient addresses?"
    ):
        raise typer.Abort()

    from app.services.graph_connectivity import backfill_place_nodes

    places = backfill_place_nodes()
    typer.echo(f"Created/updated {places:,} shared Place nodes with LIVES_IN links.")


@app.command("backfill-patient-names")
def backfill_patient_names(
    input_dir: Path = typer.Argument(..., help="Directory of Synthea FHIR JSON bundles"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Set Patient.name from FHIR official HumanName in bundle files."""
    from ingestion.fhir_utils import official_patient_name
    from ingestion.parsers.bundle_parser import BundleIndex, iter_bundle_files, load_bundle

    resolved = input_dir.resolve()
    if not resolved.is_dir():
        raise typer.BadParameter(f"Not a directory: {resolved}")

    if not yes and not typer.confirm(
        f"Update Patient.name from official FHIR names in {resolved}?"
    ):
        raise typer.Abort()

    updates: list[dict[str, str]] = []
    skipped = 0
    for path in iter_bundle_files(resolved):
        bundle = load_bundle(path)
        index = BundleIndex(bundle)
        patients = index.by_type.get("Patient") or []
        if not patients:
            skipped += 1
            continue
        patient = patients[0]
        name = official_patient_name(patient.get("name"))
        pid = patient.get("id")
        if not pid or not name:
            skipped += 1
            continue
        updates.append({"fhirId": pid, "name": name})

    if not updates:
        typer.echo("No patient names found to backfill.")
        raise typer.Exit(0)

    with get_session() as session:
        row = session.run(
            """
            UNWIND $rows AS row
            MATCH (p:Patient {fhirId: row.fhirId})
            SET p.name = row.name
            RETURN count(p) AS updated
            """,
            rows=updates,
        ).single()
        updated = int(row["updated"]) if row else 0

    typer.echo(
        f"Updated {updated:,} patients with names from {len(updates):,} bundles "
        f"({skipped:,} bundles skipped)."
    )


@app.command("backfill-patient-ids")
def backfill_patient_ids_cmd(
    start: int = typer.Option(16101, help="First patientId to assign when none exist yet"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Assign sequential short patientId values (16101, 16102, …) to Patient nodes."""
    if not yes and not typer.confirm(
        f"Assign short patient IDs starting from {start} to patients missing patientId?"
    ):
        raise typer.Abort()

    from ingestion.patient_ids import backfill_patient_ids

    with get_session() as session:
        result = backfill_patient_ids(session, start=start)
    typer.echo(f"Assigned patientId to {result['updated']:,} patients.")
    if result["maxId"] is not None:
        typer.echo(f"Highest patientId is {result['maxId']:,}.")


@app.command("load-bulk")
def load_bulk(
    input_dir: Path = typer.Argument(..., help="Directory of Synthea patient Bundle JSON files"),
    limit: int = typer.Option(None, help="Max number of bundles to ingest"),
    import_dir: Path = typer.Option(
        None,
        help="Neo4j import directory (default: auto-detect Neo4j Desktop import folder)",
    ),
):
    """
    Fastest bulk ingest via LOAD CSV (best for large initial loads).

    1. Maps all bundles in parallel (process pool)
    2. Writes CSV files to Neo4j import directory
    3. LOAD CSV MERGE into fhirexplorer

    Ensure Neo4j can read the import dir. Neo4j Desktop uses:
    %USERPROFILE%\\.Neo4jDesktop2\\Data\\dbmss\\dbms-<id>\\import
    """
    if not input_dir.is_dir():
        raise typer.BadParameter(f"Not a directory: {input_dir}")

    resolved = import_dir or resolve_import_dir()
    typer.echo(f"Mode=bulk-csv | import_dir={resolved}")
    summary = ingest_directory_bulk_csv(input_dir, limit=limit, import_dir=resolved)
    typer.echo(
        f"Bulk loaded {summary['files']} bundles, {summary['patients']} patients "
        f"in {summary['seconds']}s"
    )


if __name__ == "__main__":
    app()
