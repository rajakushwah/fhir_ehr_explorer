"""CLI for FHIR bundle ingestion."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from ingestion.pipeline import apply_schema, ingest_directory

app = typer.Typer(help="EHR Data Explorer — Synthea FHIR ingestion")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


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
    """Apply Neo4j constraints and indexes to fhir_explorer database."""
    apply_schema(schema)
    typer.echo(f"Schema applied from {schema}")


@app.command("load")
def load(
    input_dir: Path = typer.Argument(..., help="Directory of Synthea patient Bundle JSON files"),
    workers: int = typer.Option(1, help="Parallel worker threads (use 1 for stable bulk load)"),
    limit: int = typer.Option(None, help="Max number of bundles to ingest"),
):
    """Ingest patient bundles into Neo4j."""
    if not input_dir.is_dir():
        raise typer.BadParameter(f"Not a directory: {input_dir}")

    results = ingest_directory(input_dir, workers=workers, limit=limit)
    total_patients = sum(r["counts"].get("Patient", 0) for r in results)
    typer.echo(f"Ingested {len(results)} bundles, {total_patients} patients")


if __name__ == "__main__":
    app()
