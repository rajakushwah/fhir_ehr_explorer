import logging

from fastapi import APIRouter, HTTPException

from app.schemas.cohort import CohortSearchRequest, CohortSearchResponse
from app.services.cohort_service import get_filter_options, search_cohort
from app.utils.neo4j_errors import handle_db_error
from app.utils.timing import timed_step

router = APIRouter(prefix="/cohort")
logger = logging.getLogger("cohort")


@router.get("/filters")
def cohort_filters():
    with timed_step(logger, "cohort/filters"):
        try:
            return get_filter_options()
        except HTTPException:
            raise
        except Exception as exc:
            handle_db_error("cohort/filters", exc)


@router.post("/search", response_model=CohortSearchResponse)
def cohort_search(req: CohortSearchRequest):
    if not req.query and not any([req.condition, req.state, req.city, req.gender]):
        raise HTTPException(status_code=400, detail="Provide a query or at least one filter")

    with timed_step(
        logger,
        "cohort/search",
        query=req.query,
        condition=req.condition,
        state=req.state,
        gender=req.gender,
    ) as metrics:
        try:
            result = search_cohort(req)
            metrics["summary"] = f"queryType={result.queryType} total={result.totalMatched}"
            return result
        except HTTPException:
            raise
        except Exception as exc:
            handle_db_error("cohort/search", exc)
