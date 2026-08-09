"""Database connection and session management.

Works with both SQL Server (development) and Postgres (production).
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import get_settings


def get_engine():
    settings = get_settings()
    url = settings.effective_database_url

    # Postgres needs different pool settings
    if url.startswith("postgresql"):
        return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    else:
        return create_engine(url, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine)

# Detect if we're running on Postgres (production) or SQL Server (dev)
IS_POSTGRES = engine.url.get_backend_name() == "postgresql"


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_query(query: str, params: dict = None) -> list[dict]:
    """Execute a SQL query and return results as a list of dicts.

    Handles SQL dialect differences between SQL Server and Postgres:
    - ISNULL → COALESCE
    - TOP N → LIMIT N
    """
    if IS_POSTGRES:
        # Convert SQL Server syntax to Postgres
        query = query.replace("ISNULL(", "COALESCE(")
        query = query.replace("CONCAT(", "CONCAT(")

        # Convert TOP N to LIMIT N
        import re
        top_match = re.search(r'SELECT\s+TOP\s*\(?\s*:?(\w+)\s*\)?', query, re.IGNORECASE)
        if top_match:
            limit_param = top_match.group(1)
            query = re.sub(r'SELECT\s+TOP\s*\(?\s*:?\w+\s*\)?', 'SELECT', query, count=1, flags=re.IGNORECASE)
            # Add LIMIT at the end (before any trailing whitespace)
            query = query.rstrip() + f" LIMIT :{limit_param}" if limit_param.isalpha() else query.rstrip() + f" LIMIT {limit_param}"

        # Convert OFFSET...FETCH to LIMIT...OFFSET
        fetch_match = re.search(r'OFFSET\s+(\d+)\s+ROWS\s+FETCH\s+NEXT\s+:?(\w+)\s+ROWS\s+ONLY', query, re.IGNORECASE)
        if fetch_match:
            offset_val = fetch_match.group(1)
            limit_param = fetch_match.group(2)
            query = re.sub(
                r'OFFSET\s+\d+\s+ROWS\s+FETCH\s+NEXT\s+:?\w+\s+ROWS\s+ONLY',
                f"LIMIT :{limit_param} OFFSET {offset_val}",
                query, flags=re.IGNORECASE
            )

        # Remove schema prefixes (Neon uses default public schema)
        query = query.replace("mart.", "")

    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
