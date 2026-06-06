# Ingestion Performance Guide

Optimized ingestion for Synthea FHIR bundles (~557 patients in `synthea_sample_data_fhir_r4_nov2021`).

## Quick commands

```powershell
cd C:\Users\ADMIN\Documents\graphDB\ehr_data_explorer
.\.venv\Scripts\Activate.ps1

# Recommended: fast parallel ingest (process pool + batched transactions)
python -m ingestion.cli load "C:\Users\ADMIN\Downloads\synthea_sample_data_fhir_r4_nov2021\fhir" --workers 4

# Fastest for large initial loads: LOAD CSV bulk path
python -m ingestion.cli load-bulk "C:\Users\ADMIN\Downloads\synthea_sample_data_fhir_r4_nov2021\fhir"
```

## Optimizations implemented

| Optimization | What it does |
|---|---|
| **Single transaction per batch** | `INGEST_TX_BATCH_SIZE` patients committed together (default 3) |
| **Combined Cypher** | Concept nodes + `CODED_AS` links in one UNWIND pass |
| **Larger UNWIND batches** | `INGEST_CYPHER_BATCH_SIZE=1000` rows per query |
| **Process pool mapping** | Parallel CPU-bound JSON parse + FHIR mapping |
| **Thread pool writes** | Parallel Neo4j I/O with separate sessions |
| **Observation filtering** | Skips social-history, survey, therapy, activity; caps at 400/patient |
| **LOAD CSV bulk mode** | `load-bulk` exports CSV to Neo4j import dir, then MERGE via LOAD CSV |

## Environment variables

```env
# Parallel mapping (CPU)
INGEST_USE_PROCESSES=true
INGEST_MAP_WORKERS=4

# Parallel Neo4j writes (I/O) — keep 2-6 on Neo4j Desktop
INGEST_WRITE_WORKERS=4
INGEST_TX_BATCH_SIZE=3
INGEST_CYPHER_BATCH_SIZE=1000

# Observation filtering (biggest speed win)
INGEST_SKIP_OBSERVATION_CATEGORIES=social-history,survey,therapy,activity
INGEST_MAX_OBSERVATIONS_PER_PATIENT=400
# Optional: only keep specific categories (overrides skip when set)
# INGEST_KEEP_OBSERVATION_CATEGORIES=laboratory,vital-signs,exam

# Neo4j LOAD CSV import directory (auto-detected for Neo4j Desktop)
# NEO4J_IMPORT_DIR=C:\Users\ADMIN\.Neo4jDesktop2\Data\dbmss\dbms-<id>\import
```

## Increase Neo4j heap (Neo4j Desktop)

Default Desktop heap is ~1 GB — a major bottleneck for bulk ingest.

1. Open **Neo4j Desktop**
2. Select your `fhir_explorer` instance
3. Click the **⋯** menu → **Settings** (or **Manage** → **Settings**)
4. Find **Memory** / `dbms.memory.heap.max_size`
5. Set to **2G** or **4G** (e.g. `2G` for 8 GB RAM machine, `4G` for 16 GB+)
6. **Stop** then **Start** the database

Also consider:
- `dbms.memory.pagecache.size=512m` (or `1G` for larger datasets)

## Which mode to use?

| Mode | Command | Best for |
|---|---|---|
| **Fast** (default) | `load` | Incremental adds, re-runs, mixed workloads |
| **Bulk CSV** | `load-bulk` | First-time load of hundreds of patients |

`load-bulk` writes CSV files into the Neo4j import folder, then runs `LOAD CSV ... MERGE`. Fewer Python→Neo4j round trips.

## Expected throughput

With observation filtering + 4 workers + 2 GB heap:

- **Before:** ~30–90 s/patient sequential
- **After:** ~5–15 s/patient effective (varies by bundle size)
- **557 patients:** roughly 1–3 hours with `load`, faster with `load-bulk`

## Troubleshooting

| Symptom | Fix |
|---|---|
| `TransientError` / deadlocks | Lower `INGEST_WRITE_WORKERS` to 2 |
| Out of memory | Increase Neo4j heap; lower `INGEST_TX_BATCH_SIZE` to 1 |
| `LOAD CSV` file not found | Set `NEO4J_IMPORT_DIR` to your Desktop `import` folder |
| Auth errors | Check `NEO4J_PASS` in `.env` |
