from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from .routes import router
from ..db.database import init_db, cleanup_expired_sessions, run_migrations
from ..config import get_settings
from slowapi.errors import RateLimitExceeded
from .middleware import limiter, rate_limit_exception_handler

logger.add("planweaver.log", rotation="10 MB", retention="7 days", level="INFO")

settings = get_settings()

logger.info("Starting PlanWeaver API v0.1.0")
logger.info(f"CORS origins: {settings.cors_origins or 'default localhost:3000'}")


def bootstrap_database() -> None:
    init_db()
    logger.info("Database initialized")

    run_migrations()
    logger.info("Database migrations completed")

    cleanup_count = cleanup_expired_sessions()
    if cleanup_count > 0:
        logger.info(f"Cleaned up {cleanup_count} expired sessions on startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_database()
    yield


app = FastAPI(
    title="PlanWeaver API",
    description="Universal LLM Planning & Execution Engine",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

cors_origins = settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

# Mount static files for UI
static_dir = Path(__file__).parent.parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Static files mounted from {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "planweaver"}
