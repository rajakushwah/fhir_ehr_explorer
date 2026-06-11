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
