from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi.errors import RateLimitExceeded

from ..config import get_settings
from ..db.database import cleanup_expired_sessions, init_db, run_migrations
from .middleware import limiter, rate_limit_exception_handler
from .routes import router

logger.add("planweaver.log", rotation="10 MB", retention="7 days", level="INFO")

settings = get_settings()


def _bootstrap_database() -> None:
    init_db()
    run_migrations()
    cleaned = cleanup_expired_sessions()
    if cleaned:
        logger.info("Cleaned up %d expired sessions on startup", cleaned)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting PlanWeaver API v0.1.0")
    logger.info("CORS origins: %s", settings.cors_origins or "default localhost:3000")
    _bootstrap_database()
    yield


def _build_app() -> FastAPI:
    app = FastAPI(
        title="PlanWeaver API",
        description="Universal LLM Planning & Execution Engine",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

    origins = settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")
    app.get("/health", tags=["health"])(lambda: {"status": "healthy", "service": "planweaver"})

    static_dir = Path(__file__).parent.parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        logger.info("Static files mounted from %s at /", static_dir)
    else:
        logger.warning("Static directory not found: %s", static_dir)

    return app


app = _build_app()
