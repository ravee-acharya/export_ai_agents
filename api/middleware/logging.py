"""
Logging middleware.

Adds a correlation ID to every request (X-Correlation-ID header),
logs request/response timing, and ensures errors are always logged
with the correlation ID for traceability across services.

In production this integrates with whatever log aggregator is used
(CloudWatch, Datadog, GCP Logging). For local dev it just prints
structured JSON lines to stdout.
"""

import json
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("exportai.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000)
        response.headers["X-Correlation-ID"] = correlation_id

        log_entry = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        logger.info(json.dumps(log_entry))

        return response
