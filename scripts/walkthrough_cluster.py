"""Metabolic cluster walkthrough — female diabetics in MA (4 patients)."""
from app.db.neo4j import get_session
from app.services.graph_analytics import analyze_comorbidity

FILTERS = {
    "gender": "female",
    "state": "MA",
    "conceptSystem": "http://snomed.info/sct",
    "conceptCode": "44054006",
}

PATIENT_IDS = [
    "1cfa5a70-7f3c-4227-5cf1-e182fcff4cd4",
    "30db29cb-a1c0-272e-bfed-ce88ebc23b2d",
    "4b10c406-d391-31dc-cefd-5812b6832cf9",
    "76b289fd-e825-734c-8446-316f59643593",
]

CLUSTER_KEYWORDS = (
    "metabolic syndrome",
    "hypertriglyceridemia",
    "hyperglycemia",
    "diabetic retinopathy",
    "stress",
    "diabetes",
)

with get_session() as session:
    for pid in PATIENT_IDS:
        name = session.run(
            "MATCH (p:Patient {fhirId: $pid}) RETURN p.name AS n, p.city AS city",
            pid=pid,
        ).single()
        rows = session.run(
            """
            MATCH (p:Patient {fhirId: $pid})-[:HAS_CONDITION]->(:Condition)-[:CODED_AS]->(c:Concept)
            RETURN coalesce(c.display, c.text, c.code) AS condition
            ORDER BY condition
            """,
            pid=pid,
        ).data()
        print(f"=== {name['n'] or pid[:8]} ({name['city']}) ===")
        for row in rows:
            label = row["condition"]
            if any(keyword in label.lower() for keyword in CLUSTER_KEYWORDS):
                print(f"  • {label}")
        print(f"  ({len(rows)} total conditions)\n")

co = analyze_comorbidity(FILTERS, max_concepts=40)
print("=== CLUSTER SUMMARY (analytics) ===")
for concept in co["concepts"]:
    if any(keyword in concept["label"].lower() for keyword in CLUSTER_KEYWORDS):
        pct = int(concept["prevalence"] * 100)
        bridge = "bridge" if concept["isBridge"] else "core"
        print(
            f"  {concept['label']}: {concept['patientCount']}/4 ({pct}%) "
            f"| cluster {concept['communityId']} | {bridge}"
        )

print("\n=== COMMUNITIES ===")
for community in co["communities"]:
    print(f"  Cluster {community['id']}: {community['label']} ({community['conceptCount']} conditions)")
