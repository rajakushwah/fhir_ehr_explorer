"""Neo4j session wrapper that logs Cypher execution time."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from app.config import LOG_QUERY_DETAIL

logger = logging.getLogger("neo4j.query")


def _short_query(cypher: str) -> str:
    line = re.sub(r"\s+", " ", cypher.strip().split("\n", 1)[0])
    return line[:72] + ("…" if len(line) > 72 else "")


def _safe_params(params: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not params:
        return {}
    safe = {}
    for key, value in params.items():
        if key.startswith("_"):
            continue
        text = str(value)
        safe[key] = text if len(text) <= 80 else text[:77] + "…"
    return safe


def log_query(
    operation: str,
    ms: float,
    row_count: Optional[int] = None,
    cypher: str = "",
    params: Optional[dict[str, Any]] = None,
) -> None:
    rows = "?" if row_count is None else str(row_count)
    if logger.isEnabledFor(logging.DEBUG):
        detail = _short_query(cypher) if LOG_QUERY_DETAIL and cypher else operation
        logger.debug(
            "[QUERY] %s | %.1fms | rows=%s | %s | params=%s",
            operation,
            ms,
            rows,
            detail,
            _safe_params(params),
        )
    elif logger.isEnabledFor(logging.INFO):
        logger.info("[QUERY] %s | %.1fms | rows=%s", operation, ms, rows)


class TimedResult:
    """Wraps a neo4j Result and logs timing when data is consumed."""

    def __init__(
        self,
        result: Any,
        operation: str,
        t0: float,
        cypher: str = "",
        params: Optional[dict[str, Any]] = None,
    ):
        self._result = result
        self._operation = operation
        self._t0 = t0
        self._cypher = cypher
        self._params = params
        self._logged = False

    def _finalize(self, row_count: Optional[int]) -> None:
        if self._logged:
            return
        self._logged = True
        ms = (time.perf_counter() - self._t0) * 1000
        log_query(self._operation, ms, row_count, self._cypher, self._params)

    def __iter__(self):
        rows = list(self._result)
        self._finalize(len(rows))
        return iter(rows)

    def single(self):
        row = self._result.single()
        self._finalize(0 if row is None else 1)
        return row

    def peek(self):
        return self._result.peek()

    def consume(self):
        summary = self._result.consume()
        counters = getattr(summary, "counters", None)
        rows = None
        if counters is not None:
            rows = (
                getattr(counters, "nodes_created", 0)
                + getattr(counters, "nodes_deleted", 0)
                + getattr(counters, "relationships_created", 0)
            )
        self._finalize(rows)
        return summary

    def __getattr__(self, name: str):
        return getattr(self._result, name)


class TimedSession:
    """Transparent session wrapper — drop-in for neo4j session.run()."""

    def __init__(self, session: Any):
        self._session = session

    def run(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> TimedResult:
        op = kwargs.pop("_log_op", None) or _short_query(query)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "[QUERY] %s | start | params=%s",
                op,
                _safe_params(parameters),
            )
        t0 = time.perf_counter()
        result = self._session.run(query, parameters, **kwargs)
        return TimedResult(result, op, t0, query, parameters)

    def execute_write(self, transaction_function, *args, **kwargs):
        return self._session.execute_write(transaction_function, *args, **kwargs)

    def execute_read(self, transaction_function, *args, **kwargs):
        return self._session.execute_read(transaction_function, *args, **kwargs)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> TimedSession:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __getattr__(self, name: str):
        return getattr(self._session, name)
