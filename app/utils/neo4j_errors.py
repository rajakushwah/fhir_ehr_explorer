"""Neo4j error classification for API responses and logs."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

from app.config import NEO4J_DATABASE, NEO4J_URI

logger = logging.getLogger("neo4j")


def is_neo4j_error(exc: BaseException) -> bool:
    if isinstance(exc, Neo4jError):
        return True
    text = str(exc).lower()
    return any(
        phrase in text
        for phrase in (
            "connection refused",
            "failed to establish connection",
            "couldn't connect",
            "service unavailable",
            "database not found",
            "unauthorized",
            "authentication failure",
        )
    )


def neo4j_user_message(exc: BaseException) -> str:
    if isinstance(exc, ServiceUnavailable):
        return (
            "Neo4j is not running. Start your local Neo4j instance "
            f"(expected at {NEO4J_URI}) and try again."
        )
    if isinstance(exc, AuthError):
        return (
            "Neo4j authentication failed. Check NEO4J_USER and NEO4J_PASS in .env."
        )
    if "DatabaseNotFound" in type(exc).__name__ or "database not found" in str(exc).lower():
        return (
            f"Neo4j database '{NEO4J_DATABASE}' not found. "
            "Run: python -m ingestion.cli init-db"
        )
    text = str(exc).lower()
    if "connection refused" in text or "failed to establish connection" in text:
        return (
            "Cannot connect to Neo4j. Ensure Neo4j is started and "
            f"NEO4J_URI is correct ({NEO4J_URI})."
        )
    if "unauthorized" in text or "authentication" in text:
        return "Neo4j authentication failed. Check credentials in .env."
    return f"Neo4j error: {exc}"


def neo4j_status_code(exc: BaseException) -> int:
    if isinstance(exc, (ServiceUnavailable, AuthError)):
        return 503
    text = str(exc).lower()
    if any(p in text for p in ("connection refused", "failed to establish", "couldn't connect")):
        return 503
    if "not found" in text and "database" in text:
        return 503
    return 500


def log_neo4j_failure(operation: str, exc: BaseException) -> str:
    message = neo4j_user_message(exc)
    logger.error("[FAIL]  %s | %s", operation, message)
    logger.debug("Neo4j exception detail", exc_info=exc)
    return message


def raise_neo4j_http(operation: str, exc: BaseException) -> None:
    message = log_neo4j_failure(operation, exc)
    raise HTTPException(
        status_code=neo4j_status_code(exc),
        detail=message,
    ) from exc


def handle_db_error(operation: str, exc: Exception) -> None:
    if is_neo4j_error(exc):
        raise_neo4j_http(operation, exc)
    logger.exception("[FAIL]  %s | unexpected error", operation)
    raise HTTPException(status_code=500, detail=f"{operation} failed: {exc}") from exc


def connectivity_status() -> dict[str, Any]:
    from app.db.neo4j import get_session

    try:
        with get_session() as session:
            session.run("RETURN 1", _log_op="connectivity/ping").consume()
        return {"ok": True, "error": None}
    except Exception as exc:
        message = neo4j_user_message(exc)
        logger.warning("[NEO4J] offline | %s", message)
        return {"ok": False, "error": message}
