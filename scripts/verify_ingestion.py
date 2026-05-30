#!/usr/bin/env python3
"""Post-ingestion verification for fhir_explorer database."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from neo4j.exceptions import ServiceUnavailable

load_dotenv(ROOT / ".env")

from app.config import NEO4J_DATABASE, NEO4J_URI
from app.db.neo4j import get_session


def main() -> int:
    checks = [
        ("Patients", "MATCH (p:Patient) RETURN count(p) AS c"),
        ("Conditions", "MATCH (c:Condition) RETURN count(c) AS c"),
        ("Observations", "MATCH (o:Observation) RETURN count(o) AS c"),
        ("Concepts", "MATCH (c:Concept) RETURN count(c) AS c"),
        (
            "Orphan conditions",
            "MATCH (c:Condition) WHERE NOT (c)<-[:HAS_CONDITION]-(:Patient) RETURN count(c) AS c",
        ),
    ]

    print("=== Ingestion verification ===")
    print(f"  Neo4j: {NEO4J_URI}  database={NEO4J_DATABASE}")

    with get_session() as session:
        for name, cypher in checks:
            row = session.run(cypher).single()
            print(f"  {name}: {row['c']}")

        sample = session.run(
            """
            MATCH (concept:Concept)
            WHERE toLower(concept.display) CONTAINS 'diabetes'
            RETURN concept.system AS system, concept.code AS code, concept.display AS display
            LIMIT 3
            """
        )
        print("\nSample diabetes concepts:")
        for r in sample:
            print(f"  - {r['display']} ({r['code']})")

    return 0


def _print_neo4j_offline_help() -> None:
    print("\nERROR: Cannot connect to Neo4j at bolt://localhost:7687")
    print("  Connection refused — the database server is not running.")
    print("\nFix:")
    print("  1. Open Neo4j Desktop (or your local Neo4j install)")
    print("  2. Start your local DBMS instance")
    print("  3. Confirm database 'fhirexplorer' shows status Online")
    print("  4. Re-run: python scripts\\verify_ingestion.py")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ServiceUnavailable:
        _print_neo4j_offline_help()
        raise SystemExit(1)
