from fastapi import APIRouter, HTTPException

from app.schemas.cohort import CohortSearchRequest, CohortSearchResponse
from app.services.cohort_service import get_filter_options, search_cohort

router = APIRouter(prefix="/cohort")


@router.get("/filters")
def cohort_filters():
    try:
        return get_filter_options()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/search", response_model=CohortSearchResponse)
def cohort_search(req: CohortSearchRequest):
    if not req.query and not any([req.condition, req.state, req.city, req.gender]):
        raise HTTPException(status_code=400, detail="Provide a query or at least one filter")
    try:
        return search_cohort(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cohort search failed: {exc}") from exc
