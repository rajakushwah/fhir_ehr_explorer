from neo4j import GraphDatabase

from app.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD),
)


def get_session():
    return driver.session(database=NEO4J_DATABASE)


def verify_connectivity() -> bool:
    try:
        driver.verify_connectivity()
        with get_session() as session:
            session.run("RETURN 1")
        return True
    except Exception:
        return False
