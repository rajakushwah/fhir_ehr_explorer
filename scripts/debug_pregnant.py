from app.services.cohort_parser import parse_natural_query
from app.services.cohort_aggregation_parser import parse_aggregation_query
from app.schemas.cohort import CohortSearchRequest
from app.services.cohort_service import search_cohort, _resolve_concept
from app.db.neo4j import get_session

q = "count patient who is pregnant"
parsed = parse_natural_query(q)
agg = parse_aggregation_query(q, parsed)
print("parsed condition:", parsed.condition)
print("agg:", agg.is_aggregation, agg.target)

with get_session() as session:
    rows = session.run(
        """
        MATCH (c:Concept)<-[:CODED_AS]-(:Condition)<-[:HAS_CONDITION]-(p:Patient)
        WHERE toLower(coalesce(c.display, c.text, '')) CONTAINS 'pregnan'
        RETURN coalesce(c.display, c.text) AS label, count(DISTINCT p) AS patients
        ORDER BY patients DESC LIMIT 15
        """
    ).data()
    print("patients by pregnancy concept:")
    for r in rows:
        print(f"  {r['patients']:3d}  {r['label']}")

    total = session.run(
        """
        MATCH (c:Concept)<-[:CODED_AS]-(:Condition)<-[:HAS_CONDITION]-(p:Patient)
        WHERE toLower(coalesce(c.display, c.text, '')) CONTAINS 'pregnan'
        RETURN count(DISTINCT p) AS cnt
        """
    ).single()["cnt"]
    print("distinct patients (any pregnancy-related condition):", total)

    obs = session.run(
        """
        MATCH (c:Concept)<-[:CODED_AS]-(:Observation)<-[:HAS_OBSERVATION]-(p:Patient)
        WHERE toLower(coalesce(c.display, c.text, '')) CONTAINS 'pregnan'
        RETURN count(DISTINCT p) AS cnt
        """
    ).single()["cnt"]
    print("distinct patients (pregnancy observation):", obs)

r = search_cohort(CohortSearchRequest(query=q))
print("API:", r.total, r.interpretation, r.aggregation.summary if r.aggregation else "")
