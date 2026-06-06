"""Service and router timing helpers."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from fastapi import HTTPException


@contextmanager
def timed_step(
    logger: logging.Logger,
    operation: str,
    **context: Any,
) -> Iterator[dict[str, Any]]:
    details = " | ".join(f"{key}={value!r}" for key, value in context.items())
    logger.info("[START] %s | %s", operation, details or "-")

    t0 = time.perf_counter()
    metrics: dict[str, Any] = {"duration_ms": 0.0}

    try:
        yield metrics
    except HTTPException:
        metrics["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        raise
    except Exception as exc:
        metrics["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        logger.exception(
            "[FAIL]  %s | %.1fms | %s | error=%s",
            operation,
            metrics["duration_ms"],
            details or "-",
            exc,
        )
        raise
    else:
        metrics["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        extra = metrics.get("summary", "")
        logger.info(
            "[OK]    %s | %.1fms | %s%s",
            operation,
            metrics["duration_ms"],
            details or "-",
            f" | {extra}" if extra else "",
        )
