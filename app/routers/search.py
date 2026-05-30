from fastapi import APIRouter, HTTPException

from app.schemas.search import SearchRequest
from app.services.search_service import search_concepts

router = APIRouter()


@router.post("/search")
def search(req: SearchRequest):
    return search_concepts(req.query)
