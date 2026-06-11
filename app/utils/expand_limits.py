"""Resolve per-request limits for graph expansion."""

from __future__ import annotations

import os
from typing import Any

from app.config import MAX_PATIENT_RESULTS

MAX_GRAPH_EXPAND_LIMIT = int(os.getenv("MAX_GRAPH_EXPAND_LIMIT", "500"))


def resolve_expand_limit(context: dict[str, Any] | None, *, default: int | None = None) -> int:
    """Clamp patient/child expand limit from API context."""
    fallback = default if default is not None else MAX_PATIENT_RESULTS
    if not context:
        return min(fallback, MAX_GRAPH_EXPAND_LIMIT)

    raw = context.get("limit")
    if raw is None:
        return min(fallback, MAX_GRAPH_EXPAND_LIMIT)

    try:
        value = int(raw)
    except (TypeError, ValueError):
        return min(fallback, MAX_GRAPH_EXPAND_LIMIT)

    return max(1, min(value, MAX_GRAPH_EXPAND_LIMIT))
