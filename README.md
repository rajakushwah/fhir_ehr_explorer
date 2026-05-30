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
python -m ingestion.cli load "C:\Users\ADMIN\Downloads\synthea_sample_data_fhir_latest" --workers 4
```

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
