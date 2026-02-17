from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from .routes import router
from ..db.database import init_db
from ..config import get_settings

logger.add("planweaver.log", rotation="10 MB", retention="7 days", level="INFO")

settings = get_settings()

logger.info("Starting PlanWeaver API v0.1.0")
logger.info(f"CORS origins: {settings.cors_origins or 'default localhost:3000'}")

app = FastAPI(
    title="PlanWeaver API",
    description="Universal LLM Planning & Execution Engine",
    version="0.1.0"
)

cors_origins = settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "planweaver"}
