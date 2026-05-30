import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASS", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "fhirexplorer")

MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "25"))
MAX_PATIENT_RESULTS = int(os.getenv("MAX_PATIENT_RESULTS", "50"))
