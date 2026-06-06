from neo4j import GraphDatabase

from app.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from app.db.timed_session import TimedSession
from app.utils.neo4j_errors import connectivity_status

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD),
)


def get_session() -> TimedSession:
    return TimedSession(driver.session(database=NEO4J_DATABASE))


def verify_connectivity() -> bool:
    return connectivity_status()["ok"]
