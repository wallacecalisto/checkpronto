
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail={
        "message": "Muitas tentativas em pouco tempo. Aguarde um minuto antes de tentar de novo.",
        "code": "RATE_LIMITED",
    },
)


class RateLimiter:

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                raise _RATE_LIMITED
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def _client_key(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


login_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
pin_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


def enforce_login_rate_limit(request: Request) -> None:
    login_rate_limiter.check(_client_key(request))


def enforce_pin_rate_limit(request: Request) -> None:
    pin_rate_limiter.check(_client_key(request))
