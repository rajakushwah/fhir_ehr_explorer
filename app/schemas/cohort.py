from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CohortSearchRequest(BaseModel):
    query: Optional[str] = None
    condition: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    minAge: Optional[int] = None
    maxAge: Optional[int] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ParsedFilters(BaseModel):
    condition: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    minAge: Optional[int] = None
    maxAge: Optional[int] = None


class PatientSummary(BaseModel):
    fhirId: str
    gender: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    birthDate: Optional[str] = None
    age: Optional[int] = None
    conditions: List[str] = []


class AggregationRow(BaseModel):
    label: str
    value: float


class AggregationResult(BaseModel):
    metric: str
    target: str
    summary: str
    rows: List[AggregationRow]


class CohortSearchResponse(BaseModel):
    interpretation: str
    parsed: ParsedFilters
    queryType: str = "list"  # list | aggregation
    total: int
    totalMatched: Optional[int] = None
    offset: int = 0
    limit: int = 50
    hasMore: bool = False
    patients: List[PatientSummary]
    concept: Optional[Dict[str, Any]] = None
    aggregation: Optional[AggregationResult] = None
