import logging
import time

from django.conf import settings


request_logger = logging.getLogger("request_log")


class RequestLoggingMiddleware:
    """
    Lightweight request/response access logger.

    Notes:
    - Logs only method/path/status/duration and basic actor info.
    - Never logs request/response body to avoid leaking sensitive data.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or "/"
        excluded_prefixes = getattr(settings, "REQUEST_LOGGING_EXCLUDE_PREFIXES", ())
        if any(path.startswith(prefix) for prefix in excluded_prefixes):
            return self.get_response(request)

        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        user_id = getattr(getattr(request, "user", None), "id", None)
        request_logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f user_id=%s ip=%s",
            request.method,
            path,
            getattr(response, "status_code", "unknown"),
            elapsed_ms,
            user_id if user_id is not None else "-",
            request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "-")),
        )
        return response

