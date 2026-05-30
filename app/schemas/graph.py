from typing import Any, Dict

from pydantic import BaseModel


class ExpandRequest(BaseModel):
    nodeType: str
    context: Dict[str, Any]
