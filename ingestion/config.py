"""Ingestion performance and filtering settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _csv_set(value: str) -> frozenset[str]:
    return frozenset(
        part.strip().lower().replace(" ", "-")
        for part in value.split(",")
        if part.strip()
    )


def _int_or_none(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value)


# Parallel mapping (CPU-bound JSON parse + FHIR map)
INGEST_MAP_WORKERS = int(os.getenv("INGEST_MAP_WORKERS", "4"))
# Parallel Neo4j writers (I/O-bound); keep <= 6 on Neo4j Desktop
INGEST_WRITE_WORKERS = int(os.getenv("INGEST_WRITE_WORKERS", "4"))
# Patients committed per Neo4j transaction
INGEST_TX_BATCH_SIZE = int(os.getenv("INGEST_TX_BATCH_SIZE", "3"))
# Rows per UNWIND Cypher batch
INGEST_CYPHER_BATCH_SIZE = int(os.getenv("INGEST_CYPHER_BATCH_SIZE", "1000"))
# Use ProcessPoolExecutor for mapping (recommended on Windows)
INGEST_USE_PROCESSES = os.getenv("INGEST_USE_PROCESSES", "true").lower() in ("1", "true", "yes")

# Observation filtering — biggest speed win for Synthea bundles
INGEST_SKIP_OBSERVATION_CATEGORIES = _csv_set(
    os.getenv(
        "INGEST_SKIP_OBSERVATION_CATEGORIES",
        "social-history,survey,therapy,activity",
    )
)
INGEST_KEEP_OBSERVATION_CATEGORIES = _csv_set(os.getenv("INGEST_KEEP_OBSERVATION_CATEGORIES", ""))
INGEST_MAX_OBSERVATIONS_PER_PATIENT = _int_or_none(
    os.getenv("INGEST_MAX_OBSERVATIONS_PER_PATIENT", "400")
)

# Neo4j LOAD CSV import directory (Neo4j Desktop: dbms-*/import)
NEO4J_IMPORT_DIR = os.getenv("NEO4J_IMPORT_DIR", "")


def resolve_import_dir() -> Path:
    if NEO4J_IMPORT_DIR:
        path = Path(NEO4J_IMPORT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    desktop_root = Path.home() / ".Neo4jDesktop2" / "Data" / "dbmss"
    if desktop_root.is_dir():
        candidates = sorted(desktop_root.glob("dbms-*/import"), key=lambda p: p.stat().st_mtime, reverse=True)
        for candidate in candidates:
            if candidate.is_dir():
                return candidate

    fallback = Path(__file__).resolve().parent.parent / "data" / "neo4j_import"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


@dataclass(frozen=True)
class MapOptions:
    skip_observation_categories: frozenset[str] = INGEST_SKIP_OBSERVATION_CATEGORIES
    keep_observation_categories: frozenset[str] = INGEST_KEEP_OBSERVATION_CATEGORIES
    max_observations_per_patient: int | None = INGEST_MAX_OBSERVATIONS_PER_PATIENT


def get_map_options() -> MapOptions:
    return MapOptions()
