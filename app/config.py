import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASS", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "fhirexplorer")

MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "25"))
MAX_PATIENT_RESULTS = int(os.getenv("MAX_PATIENT_RESULTS", "50"))

# Logging — see .env.example for levels: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_HTTP_LEVEL = os.getenv("LOG_HTTP_LEVEL", LOG_LEVEL).upper()
LOG_QUERY_LEVEL = os.getenv("LOG_QUERY_LEVEL", "INFO").upper()
LOG_SEARCH_LEVEL = os.getenv("LOG_SEARCH_LEVEL", LOG_LEVEL).upper()
LOG_COHORT_LEVEL = os.getenv("LOG_COHORT_LEVEL", LOG_LEVEL).upper()
LOG_GRAPH_LEVEL = os.getenv("LOG_GRAPH_LEVEL", LOG_LEVEL).upper()
LOG_INGESTION_LEVEL = os.getenv("LOG_INGESTION_LEVEL", LOG_LEVEL).upper()
LOG_NEO4J_DRIVER_LEVEL = os.getenv("LOG_NEO4J_DRIVER_LEVEL", "WARNING").upper()
# Set true to log full Cypher text (best with LOG_QUERY_LEVEL=DEBUG)
LOG_QUERY_DETAIL = os.getenv("LOG_QUERY_DETAIL", "false").lower() in ("1", "true", "yes")
