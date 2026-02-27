from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


def get_identifier(request: Request) -> str:
    """Get client IP, exempting localhost and private networks"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    # Exempt localhost and private networks
    if client_ip in ["127.0.0.1", "localhost", "::1"]:
        return "localhost"
    if client_ip.startswith(("10.", "192.168.", "172.16.")):
        return "localhost"
    return client_ip


limiter = Limiter(key_func=get_identifier)


def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": str(exc.retry_after)
        },
        headers={"Retry-After": str(exc.retry_after)}
    )
