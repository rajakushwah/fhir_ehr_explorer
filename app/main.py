import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import NEO4J_DATABASE
from app.logging_config import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import cohort, graph, search
from app.utils.neo4j_errors import connectivity_status

setup_logging()
logger = logging.getLogger("app")

app = FastAPI(
    title="EHR Data Explorer",
    description="FHIR patient graph explorer — search clinical concepts and expand patient relationships",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    neo4j = connectivity_status()
    if neo4j["ok"]:
        logger.info(
            "EHR Data Explorer started | Neo4j connected | database=%s",
            NEO4J_DATABASE,
        )
    else:
        logger.warning("EHR Data Explorer started | Neo4j OFFLINE | %s", neo4j["error"])


app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, tags=["SEARCH"])
app.include_router(graph.router, tags=["GRAPH"])
app.include_router(cohort.router, tags=["COHORT"])

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/health")
def health():
    neo4j = connectivity_status()
    return {
        "status": "ok" if neo4j["ok"] else "degraded",
        "backend": "ok",
        "neo4j": neo4j["ok"],
        "neo4jError": neo4j["error"],
    }


if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_frontend():
        return FileResponse(FRONTEND_DIST / "index.html")
