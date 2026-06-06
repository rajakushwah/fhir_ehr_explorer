# EHR Data Explorer

Standalone FHIR patient graph explorer with Synthea R4 ingestion into Neo4j.

- **Backend:** FastAPI on port **8002**
- **Frontend:** React + Cytoscape.js on port **5174**
- **Database:** Neo4j database `fhirexplorer` (local; Neo4j does not allow `_` in database names)

## Quick Start

```powershell
cd C:\Users\ADMIN\Documents\graphDB\ehr_data_explorer
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env with Neo4j credentials
```

### 1. Apply schema

```powershell
python -m ingestion.cli init-schema
```

### 2. Ingest Synthea bundles

```powershell
# Fast parallel ingest (process pool + batched transactions + observation filter)
python -m ingestion.cli load "C:\Users\ADMIN\Downloads\synthea_sample_data_fhir_r4_nov2021\fhir" --workers 4

# Fastest bulk load (LOAD CSV — best for large initial imports)
python -m ingestion.cli load-bulk "C:\Users\ADMIN\Downloads\synthea_sample_data_fhir_r4_nov2021\fhir"
```

See [docs/INGESTION_PERFORMANCE.md](./docs/INGESTION_PERFORMANCE.md) for tuning (Neo4j heap, workers, observation filters).

### 3. Verify

```powershell
python scripts\verify_ingestion.py
```

### 4. Run API

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

### 5. Run UI (dev)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5174

See [ARCHITECTURE.md](./ARCHITECTURE.md) for a short overview of what we build and how the system works.

## Graph Model

```
Patient -[:HAS_CONDITION]-> Condition -[:CODED_AS]-> Concept
Patient -[:HAS_OBSERVATION]-> Observation -[:CODED_AS]-> Concept
Patient -[:HAS_ENCOUNTER]-> Encounter
Resource -[:PART_OF_ENCOUNTER]-> Encounter
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health + Neo4j connectivity |
| POST | `/search` | Search `Concept` nodes |
| POST | `/graph/expand` | Progressive graph expansion |

## Environment

| Variable | Description |
|---|---|
| `NEO4J_URI` | Bolt URI (default `bolt://localhost:7687`) |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASS` | Neo4j password |
| `NEO4J_DATABASE` | Database name (`fhirexplorer`) |

## Logging

Set levels in `.env` using `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.

| Variable | Default | What it controls |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root / app startup logs |
| `LOG_HTTP_LEVEL` | same as `LOG_LEVEL` | Request in/out + `X-Response-Time-Ms` header |
| `LOG_QUERY_LEVEL` | `INFO` | Neo4j Cypher timing (`[QUERY] op \| 12.3ms \| rows=5`) |
| `LOG_SEARCH_LEVEL` | same as `LOG_LEVEL` | `/search` handler |
| `LOG_COHORT_LEVEL` | same as `LOG_LEVEL` | `/cohort/*` handlers |
| `LOG_GRAPH_LEVEL` | same as `LOG_LEVEL` | `/graph/expand` handler |
| `LOG_INGESTION_LEVEL` | same as `LOG_LEVEL` | Ingestion CLI |
| `LOG_NEO4J_DRIVER_LEVEL` | `WARNING` | Neo4j driver internals |
| `LOG_QUERY_DETAIL` | `false` | With `LOG_QUERY_LEVEL=DEBUG`, log Cypher + params |

Example — verbose debugging:

```env
LOG_LEVEL=DEBUG
LOG_QUERY_LEVEL=DEBUG
LOG_QUERY_DETAIL=true
```

Sample log output:

```
12:01:03 | INFO    | http | >>> POST /search
12:01:03 | INFO    | search | [START] search | query='diabetes'
12:01:03 | INFO    | neo4j.query | [QUERY] search/fulltext | 8.2ms | rows=3
12:01:03 | INFO    | search | [OK]    search | 9.1ms | query='diabetes' | count=3
12:01:03 | INFO    | http | <<< POST /search | status=200 | 10.4ms
```
