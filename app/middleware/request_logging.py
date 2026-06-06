import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("http")

SKIP_PATHS = {"/favicon.ico"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in SKIP_PATHS or path.startswith("/assets"):
            return await call_next(request)

        method = request.method
        query = request.url.query
        path_display = f"{path}?{query}" if query and logger.isEnabledFor(logging.DEBUG) else path

        t0 = time.perf_counter()
        logger.info(">>> %s %s", method, path_display)

        try:
            response = await call_next(request)
            ms = (time.perf_counter() - t0) * 1000
            log_fn = logger.error if response.status_code >= 500 else logger.info
            log_fn(
                "<<< %s %s | status=%d | %.1fms",
                method,
                path,
                response.status_code,
                ms,
            )
            response.headers["X-Response-Time-Ms"] = f"{ms:.1f}"
            return response
        except Exception:
            ms = (time.perf_counter() - t0) * 1000
            logger.exception("<<< %s %s | FAILED | %.1fms", method, path, ms)
            raise
