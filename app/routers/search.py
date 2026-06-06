import logging

from fastapi import APIRouter, HTTPException

from app.schemas.search import SearchRequest
from app.services.search_service import search_concepts
from app.utils.neo4j_errors import handle_db_error
from app.utils.timing import timed_step

router = APIRouter()
logger = logging.getLogger("search")


@router.post("/search")
def search(req: SearchRequest):
    query = req.query.strip() if req.query else ""
    if not query:
        return []

    with timed_step(logger, "search", query=query) as metrics:
        try:
            results = search_concepts(query)
            metrics["summary"] = f"count={len(results)}"
            return results
        except HTTPException:
            raise
        except Exception as exc:
            handle_db_error("search", exc)
