import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DB_FILE = (ROOT_DIR / "purchasing_agent.db").resolve()

# Anchor SQLite database path to project root so working directory changes don't cause table-missing errors
raw_url = os.getenv("DATABASE_URL")
if not raw_url or raw_url == "sqlite:///./purchasing_agent.db":
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"
else:
    DATABASE_URL = raw_url

# Enable SQLite foreign key constraint enforcement
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_override=None):
    """Creates all database tables registered with Base.metadata.
    
    Ensures all model modules are imported and registered before create_all() executes.
    """
    import app.models  # noqa: F401
    import app.models.product  # noqa: F401
    import app.models.inventory  # noqa: F401
    import app.models.demand_forecast  # noqa: F401
    import app.models.supplier  # noqa: F401
    import app.models.supplier_product  # noqa: F401
    import app.models.purchase_recommendation  # noqa: F401
    import app.models.evaluation_history  # noqa: F401
    import app.models.purchase_order  # noqa: F401
    import app.models.purchasing_budget  # noqa: F401

    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)
