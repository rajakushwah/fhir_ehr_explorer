"""Ingest Synthea patient bundles into Neo4j — optimized pipeline."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from neo4j.exceptions import ServiceUnavailable, TransientError

from app.db.neo4j import get_session
from ingestion.config import (
    INGEST_MAP_WORKERS,
    INGEST_TX_BATCH_SIZE,
    INGEST_USE_PROCESSES,
    INGEST_WRITE_WORKERS,
    get_map_options,
    resolve_import_dir,
)
from ingestion.mappers.bundle_mapper import GraphPayload, map_bundle
from ingestion.mappers.payload_codec import payload_from_dict, payload_to_dict
from ingestion.parsers.bundle_parser import iter_bundle_files, load_bundle
from ingestion.writers.batch_writer import write_payloads_batch
from ingestion.writers.csv_bulk import export_payloads_to_csv, load_csv_into_neo4j

logger = logging.getLogger("ingestion")

MAX_RETRIES = 5


def _map_bundle_worker(path_str: str) -> dict[str, Any]:
    """Top-level worker for ProcessPoolExecutor (Windows pickling)."""
    path = Path(path_str)
    bundle = load_bundle(path)
    payload = map_bundle(bundle, get_map_options())
    return {"file": path.name, "payload": payload_to_dict(payload)}


def _map_files(files: list[Path]) -> list[dict[str, Any]]:
    paths = [str(path) for path in files]
    if INGEST_USE_PROCESSES and len(paths) > 1 and INGEST_MAP_WORKERS > 1:
        logger.info("[START] map_bundles | files=%d | workers=%d | mode=process", len(paths), INGEST_MAP_WORKERS)
        with ProcessPoolExecutor(max_workers=INGEST_MAP_WORKERS) as pool:
            return list(pool.map(_map_bundle_worker, paths))

    logger.info("[START] map_bundles | files=%d | workers=1 | mode=thread", len(paths))
    return [_map_bundle_worker(path_str) for path_str in paths]


def _chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _write_mapped_batch(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads = [payload_from_dict(item["payload"]) for item in batch]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with get_session() as session:
                write_payloads_batch(session, payloads)
            break
        except (TransientError, ServiceUnavailable) as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = attempt * 2
            names = ", ".join(item["file"] for item in batch[:3])
            logger.warning("Retry %d/%d for batch [%s...]: %s", attempt, MAX_RETRIES, names, exc)
            time.sleep(wait)

    results = []
    for item, payload in zip(batch, payloads):
        counts = {label: len(nodes) for label, nodes in payload.nodes.items()}
        results.append({"file": item["file"], "counts": counts})
    return results


def apply_schema(schema_path: Path) -> None:
    statements = [
        s.strip()
        for s in schema_path.read_text(encoding="utf-8").split(";")
        if s.strip() and not s.strip().startswith("//")
    ]
    logger.info("[START] apply_schema | statements=%d", len(statements))
    t0 = time.perf_counter()
    with get_session() as session:
        for i, stmt in enumerate(statements, start=1):
            session.run(stmt, _log_op=f"schema/{i}").consume()
    logger.info("[OK]    apply_schema | %.1fms", (time.perf_counter() - t0) * 1000)


def ingest_directory(
    input_dir: Path,
    workers: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    Fast ingest path:
    1. Process-pool map JSON bundles (CPU)
    2. Batch writes in single Neo4j transactions (I/O)
    """
    write_workers = workers if workers is not None else INGEST_WRITE_WORKERS
    files = list(iter_bundle_files(input_dir))
    if limit:
        files = files[:limit]

    if not files:
        logger.warning("No bundle JSON files found in %s", input_dir)
        return []

    t0 = time.perf_counter()
    mapped = _map_files(files)
    map_ms = (time.perf_counter() - t0) * 1000
    logger.info("[OK]    map_bundles | %.1fms | files=%d", map_ms, len(mapped))

    batches = list(_chunked(mapped, INGEST_TX_BATCH_SIZE))
    results: list[dict] = []

    logger.info(
        "[START] write_bundles | batches=%d | tx_batch=%d | write_workers=%d",
        len(batches),
        INGEST_TX_BATCH_SIZE,
        write_workers,
    )

    write_t0 = time.perf_counter()
    if write_workers <= 1 or len(batches) <= 1:
        for batch in batches:
            batch_results = _write_mapped_batch(batch)
            for item in batch_results:
                logger.info("[OK]    ingest_bundle | %s | counts=%s", item["file"], item["counts"])
            results.extend(batch_results)
    else:
        with ThreadPoolExecutor(max_workers=write_workers) as pool:
            futures = {pool.submit(_write_mapped_batch, batch): batch for batch in batches}
            for fut in as_completed(futures):
                batch_results = fut.result()
                for item in batch_results:
                    logger.info("[OK]    ingest_bundle | %s | counts=%s", item["file"], item["counts"])
                results.extend(batch_results)

    total_ms = (time.perf_counter() - t0) * 1000
    write_ms = (time.perf_counter() - write_t0) * 1000
    logger.info(
        "[OK]    ingest_directory | total=%.1fms | write=%.1fms | patients=%d",
        total_ms,
        write_ms,
        sum(r["counts"].get("Patient", 0) for r in results),
    )

    return [
        {
            "file": r["file"],
            "seconds": round(total_ms / 1000 / max(len(results), 1), 2),
            "counts": r["counts"],
        }
        for r in results
    ]


def ingest_directory_bulk_csv(
    input_dir: Path,
    limit: int | None = None,
    import_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Fastest path for large initial loads:
    1. Process-pool map all bundles
    2. Export combined CSV to Neo4j import dir
    3. LOAD CSV with MERGE (few round-trips)
    """
    files = list(iter_bundle_files(input_dir))
    if limit:
        files = files[:limit]
    if not files:
        raise ValueError(f"No bundle JSON files found in {input_dir}")

    t0 = time.perf_counter()
    mapped = _map_files(files)
    payloads = [payload_from_dict(item["payload"]) for item in mapped]

    target_dir = export_payloads_to_csv(payloads, import_dir=import_dir)
    logger.info("[START] csv_bulk_load | import_dir=%s", target_dir)

    with get_session() as session:
        load_csv_into_neo4j(session, import_dir=target_dir)

    elapsed = time.perf_counter() - t0
    patient_count = sum(len(p.nodes.get("Patient", [])) for p in payloads)
    summary = {
        "files": len(files),
        "patients": patient_count,
        "import_dir": str(target_dir),
        "seconds": round(elapsed, 2),
    }
    logger.info("[OK]    ingest_bulk_csv | %s", summary)
    return summary
