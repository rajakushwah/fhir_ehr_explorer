import logging
import sys

from app.config import (
    LOG_COHORT_LEVEL,
    LOG_GRAPH_LEVEL,
    LOG_HTTP_LEVEL,
    LOG_INGESTION_LEVEL,
    LOG_LEVEL,
    LOG_NEO4J_DRIVER_LEVEL,
    LOG_QUERY_LEVEL,
    LOG_SEARCH_LEVEL,
)

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def resolve_level(name: str, default: str = "INFO") -> int:
    return _LEVELS.get(name.upper(), _LEVELS.get(default.upper(), logging.INFO))


def setup_logging() -> None:
    root_level = resolve_level(LOG_LEVEL)

    logging.basicConfig(
        level=root_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    _configure_logger("http", LOG_HTTP_LEVEL)
    _configure_logger("neo4j.query", LOG_QUERY_LEVEL)
    _configure_logger("neo4j", LOG_NEO4J_DRIVER_LEVEL)
    _configure_logger("search", LOG_SEARCH_LEVEL)
    _configure_logger("cohort", LOG_COHORT_LEVEL)
    _configure_logger("graph.expand", LOG_GRAPH_LEVEL)
    _configure_logger("ingestion", LOG_INGESTION_LEVEL)
    _configure_logger("app", LOG_LEVEL)

    app_logger = logging.getLogger("app")
    app_logger.info(
        "Logging configured | root=%s | http=%s | query=%s | search=%s | cohort=%s | graph=%s",
        LOG_LEVEL,
        LOG_HTTP_LEVEL,
        LOG_QUERY_LEVEL,
        LOG_SEARCH_LEVEL,
        LOG_COHORT_LEVEL,
        LOG_GRAPH_LEVEL,
    )


def _configure_logger(name: str, level_name: str) -> None:
    logging.getLogger(name).setLevel(resolve_level(level_name))
