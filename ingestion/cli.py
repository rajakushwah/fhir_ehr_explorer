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
from ingestion.pipeline import apply_schema, ingest_directory, ingest_directory_bulk_csv

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
    results = ingest_directory(input_dir, workers=workers, limit=limit)
    total_patients = sum(r["counts"].get("Patient", 0) for r in results)
    typer.echo(f"Ingested {len(results)} bundles, {total_patients} patients")


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
