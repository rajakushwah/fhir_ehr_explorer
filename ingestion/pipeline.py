"""Ingest Synthea patient bundles into Neo4j."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from neo4j.exceptions import ServiceUnavailable, TransientError

from app.db.neo4j import get_session
from ingestion.mappers.bundle_mapper import map_bundle
from ingestion.parsers.bundle_parser import iter_bundle_files, load_bundle
from ingestion.writers.batch_writer import write_payload

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


def apply_schema(schema_path: Path) -> None:
    statements = [
        s.strip()
        for s in schema_path.read_text(encoding="utf-8").split(";")
        if s.strip() and not s.strip().startswith("//")
    ]
    with get_session() as session:
        for stmt in statements:
            session.run(stmt)


def ingest_bundle(path: Path) -> dict:
    t0 = time.perf_counter()
    bundle = load_bundle(path)
    payload = map_bundle(bundle)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with get_session() as session:
                write_payload(session, payload)
            break
        except (TransientError, ServiceUnavailable) as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = attempt * 2
            logger.warning("Retry %d/%d for %s: %s", attempt, MAX_RETRIES, path.name, exc)
            time.sleep(wait)

    elapsed = time.perf_counter() - t0
    counts = {label: len(nodes) for label, nodes in payload.nodes.items()}
    return {"file": path.name, "seconds": round(elapsed, 2), "counts": counts}


def ingest_directory(input_dir: Path, workers: int = 4, limit: int | None = None) -> list[dict]:
    files = list(iter_bundle_files(input_dir))
    if limit:
        files = files[:limit]

    results: list[dict] = []
    if workers <= 1:
        for fp in files:
            logger.info("Ingesting %s", fp.name)
            results.append(ingest_bundle(fp))
        return results

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(ingest_bundle, fp): fp for fp in files}
        for fut in as_completed(futures):
            fp = futures[fut]
            try:
                res = fut.result()
                logger.info("Done %s in %.1fs", fp.name, res["seconds"])
                results.append(res)
            except Exception:
                logger.exception("Failed %s", fp.name)
                raise
    return results
