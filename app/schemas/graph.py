from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExpandRequest(BaseModel):
    nodeType: str
    context: Dict[str, Any] = Field(default_factory=dict)
    limit: Optional[int] = Field(default=None, ge=1, le=500)


class NodeDetailRequest(BaseModel):
    nodeType: str
    context: Dict[str, Any] = Field(default_factory=dict)
    meta: Optional[Dict[str, Any]] = None


class NodeNeighborsRequest(BaseModel):
    nodeType: str
    context: Dict[str, Any] = Field(default_factory=dict)
    filterType: Optional[str] = None
    limit: Optional[int] = Field(default=50, ge=1, le=200)


class NodeRelationshipsRequest(BaseModel):
    nodeType: str
    context: Dict[str, Any] = Field(default_factory=dict)
    filterRel: Optional[str] = None
    limit: Optional[int] = Field(default=50, ge=1, le=200)


class AnalyticsFilters(BaseModel):
    gender: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    condition: Optional[str] = None
    conceptSystem: Optional[str] = None
    conceptCode: Optional[str] = None
    conceptLabel: Optional[str] = None


class ComorbidityRequest(BaseModel):
    filters: Dict[str, Any] = Field(default_factory=dict)
    minCoOccurrence: int = Field(default=2, ge=1, le=50)
    maxConcepts: int = Field(default=40, ge=5, le=80)


class SimilarPatientsRequest(BaseModel):
    patientFhirId: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=25)


class ConceptPatientsRequest(BaseModel):
    filters: Dict[str, Any] = Field(default_factory=dict)
    conceptSystem: str
    conceptCode: str
    conceptLabel: Optional[str] = None
