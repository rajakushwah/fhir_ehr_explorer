from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CohortSearchRequest(BaseModel):
    query: Optional[str] = None
    condition: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    minAge: Optional[int] = None
    maxAge: Optional[int] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ParsedFilters(BaseModel):
    condition: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    minAge: Optional[int] = None
    maxAge: Optional[int] = None
    criticalMode: Optional[str] = None


class CriticalFinding(BaseModel):
    label: str
    value: float
    unit: Optional[str] = None
    severity: str = "critical"
    direction: str = "high"
    date: Optional[str] = None
    code: Optional[str] = None


class PatientSummary(BaseModel):
    fhirId: str
    gender: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    birthDate: Optional[str] = None
    age: Optional[int] = None
    conditions: List[str] = []
    isCritical: bool = False
    criticalFindings: List[CriticalFinding] = []


class AggregationRow(BaseModel):
    label: str
    value: float


class AggregationResult(BaseModel):
    metric: str
    target: str
    summary: str
    groupBy: Optional[str] = None
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
    graphContext: Optional[Dict[str, Any]] = None
