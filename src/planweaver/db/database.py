from sqlalchemy import and_, create_engine, event, inspect, or_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from threading import Lock
from typing import Dict, Any
from .models import (
    Base,
    ExecutionLog,
    NormalizedPlanRecord,
    OptimizedVariant,
    PairwiseComparisonRecord,
    PlanModel,
    PlanEvaluationRecord,
    PlanRating,
    SessionModel,
    UserRating,
)
from ..config import get_settings
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)
_db_init_lock = Lock()
_db_initialized = False

settings = get_settings()

engine_kwargs: Dict[str, Any] = {
    "echo": False,
}
if "sqlite" in settings.database_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_kwargs)

if "sqlite" in settings.database_url:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def ensure_db_ready(force: bool = False) -> None:
    """
    Ensure the database schema and migrations are applied.

    This is safe to call repeatedly and is used by integration-style entry
    points that may operate outside the API lifespan hooks.
    """
    global _db_initialized

    if _db_initialized and not force:
        return

    with _db_init_lock:
        if _db_initialized and not force:
            return

        init_db()
        run_migrations()

        inspector = inspect(engine)
        if "sessions" not in inspector.get_table_names():
            raise RuntimeError("Database initialization failed: missing 'sessions' table")

        _db_initialized = True


MIGRATIONS = [
    {
        "version": 1,
        "name": "add_sessions_expires_at",
        "up": "ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP NULL",
    },
    {
        "version": 2,
        "name": "add_sessions_candidate_plans",
        "up": "ALTER TABLE sessions ADD COLUMN candidate_plans JSON",
    },
    {
        "version": 3,
        "name": "add_sessions_candidate_revisions",
        "up": "ALTER TABLE sessions ADD COLUMN candidate_revisions JSON",
    },
    {
        "version": 4,
        "name": "add_sessions_planning_outcomes",
        "up": "ALTER TABLE sessions ADD COLUMN planning_outcomes JSON",
    },
    {
        "version": 5,
        "name": "add_sessions_context_suggestions",
        "up": "ALTER TABLE sessions ADD COLUMN context_suggestions JSON",
    },
    {
        "version": 6,
        "name": "add_sessions_selected_candidate_id",
        "up": "ALTER TABLE sessions ADD COLUMN selected_candidate_id VARCHAR(36)",
    },
    {
        "version": 7,
        "name": "add_sessions_approved_candidate_id",
        "up": "ALTER TABLE sessions ADD COLUMN approved_candidate_id VARCHAR(36)",
    },
    {
        "version": 8,
        "name": "add_session_messages",
        "up": """
            CREATE TABLE IF NOT EXISTS session_messages (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                intent VARCHAR(50),
                metadata JSON DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_session_messages_created_at ON session_messages(created_at);
        """,
    },
    {
        "version": 9,
        "name": "add_plan_embeddings_table",
        "up": """
            CREATE TABLE IF NOT EXISTS plan_embeddings (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                user_intent_embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_plan_embeddings_session_id ON plan_embeddings(session_id);
        """,
    },
    {
        "version": 10,
        "name": "add_execution_outcomes_table",
        "up": """
            CREATE TABLE IF NOT EXISTS execution_outcomes (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                outcome_type VARCHAR(50),
                summary TEXT,
                metadata JSON DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_execution_outcomes_session_id ON execution_outcomes(session_id);
        """,
    },
    {
        "version": 11,
        "name": "add_plan_templates_table",
        "up": """
            CREATE TABLE IF NOT EXISTS plan_templates (
                id VARCHAR(36) PRIMARY KEY,
                template_name VARCHAR(255) NOT NULL,
                user_intent_pattern VARCHAR(500),
                execution_graph_template JSON,
                metadata JSON DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_plan_templates_name ON plan_templates(template_name);
        """,
    },
    {
        "version": 12,
        "name": "add_decision_records_table",
        "up": """
            CREATE TABLE IF NOT EXISTS decision_records (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                decision_point VARCHAR(255),
                debate_outcome JSON,
                selected_option VARCHAR(255),
                rationale TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_decision_records_session_id ON decision_records(session_id);
        """,
    },
    {
        "version": 13,
        "name": "add_precondition_results_table",
        "up": """
            CREATE TABLE IF NOT EXISTS precondition_results (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                step_id INTEGER NOT NULL,
                precondition_type VARCHAR(50),
                check_expression VARCHAR(500),
                probe_result BOOLEAN,
                probe_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_precondition_results_session_id ON precondition_results(session_id);
        """,
    },
    {
        "version": 14,
        "name": "add_session_metadata_column",
        "up": """
            ALTER TABLE sessions ADD COLUMN metadata JSON DEFAULT '{}';
        """,
    },
]


def get_db_version(db: Session) -> int:
    """Get the current database version from the migrations table."""
    try:
        result = db.execute(text("SELECT version FROM db_version ORDER BY version DESC LIMIT 1"))
        row = result.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def run_migrations():
    """Run any pending database migrations."""
    db = SessionLocal()
    try:
        # Create migrations table if not exists
        db.execute(
            text("""
            CREATE TABLE IF NOT EXISTS db_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        db.commit()

        current_version = get_db_version(db)

        for migration in MIGRATIONS:
            if migration["version"] > current_version:
                logger.info(f"Running migration v{migration['version']}: {migration['name']}")
                try:
                    # Split multi-statement migrations for SQLite compatibility
                    statements = [s.strip() for s in migration["up"].split(";") if s.strip()]

                    for statement in statements:
                        db.execute(text(statement))

                    # Record migration
                    db.execute(
                        text("INSERT INTO db_version (version) VALUES (:version)"),
                        {"version": migration["version"]},
                    )
                    db.commit()
                    logger.info(f"Migration v{migration['version']} completed")
                except Exception as e:
                    db.rollback()
                    # Ignore if column already exists (for SQLite)
                    if "duplicate column" not in str(e).lower():
                        logger.warning(f"Migration v{migration['version']} failed: {e}")
                    else:
                        # Mark as applied anyway
                        db.execute(
                            text("INSERT INTO db_version (version) VALUES (:version)"),
                            {"version": migration["version"]},
                        )
                        db.commit()

    finally:
        db.close()


def cleanup_expired_sessions() -> int:
    """Delete sessions that have expired based on TTL setting."""
    ttl_days = settings.session_ttl_days
    if ttl_days <= 0:
        logger.info("Session TTL disabled (ttl_days <= 0)")
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)

    db = SessionLocal()
    try:
        # Delete execution logs first (foreign key constraint)
        expired_sessions = (
            db.query(SessionModel)
            .filter(
                or_(
                    SessionModel.expires_at < cutoff,
                    and_(
                        SessionModel.expires_at.is_(None),
                        SessionModel.updated_at < cutoff,
                    ),
                )
            )
            .all()
        )

        session_ids = [s.id for s in expired_sessions]
        deleted_count = len(session_ids)

        if session_ids:
            db.query(ExecutionLog).filter(ExecutionLog.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(OptimizedVariant).filter(OptimizedVariant.session_id.in_(session_ids)).delete(
                synchronize_session=False
            )
            db.query(NormalizedPlanRecord).filter(NormalizedPlanRecord.session_id.in_(session_ids)).delete(
                synchronize_session=False
            )
            db.query(PlanEvaluationRecord).filter(PlanEvaluationRecord.session_id.in_(session_ids)).delete(
                synchronize_session=False
            )
            db.query(PairwiseComparisonRecord).filter(PairwiseComparisonRecord.session_id.in_(session_ids)).delete(
                synchronize_session=False
            )
            db.query(PlanRating).filter(PlanRating.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(UserRating).filter(UserRating.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(PlanModel).filter(PlanModel.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(SessionModel).filter(SessionModel.id.in_(session_ids)).delete(synchronize_session=False)
            db.commit()
            logger.info(f"Cleaned up {deleted_count} expired sessions (older than {ttl_days} days)")

        return deleted_count
    except Exception:
        db.rollback()
        logger.exception("Error cleaning up expired sessions")
        return 0
    finally:
        db.close()


def get_db():
    ensure_db_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine():
    return engine


def get_session() -> Session:
    ensure_db_ready()
    return SessionLocal()
