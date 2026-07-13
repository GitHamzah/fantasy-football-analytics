"""SQL Server connection and data-loading helpers."""

import urllib
import pandas as pd
from sqlalchemy import create_engine, text
from src.config import load_config


def get_engine():
    """Build and return a SQLAlchemy engine from config."""
    cfg = load_config()["database"]

    params = urllib.parse.quote_plus(
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']},{cfg['port']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"TrustServerCertificate={'yes' if cfg.get('trust_cert', True) else 'no'};"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


def load_to_raw(df: pd.DataFrame, table_name: str, if_exists: str = "replace") -> int:
    """Land a DataFrame into the raw schema.

    Args:
        df: Source DataFrame from nflreadpy.
        table_name: Target table name (without schema prefix).
        if_exists: 'replace' for full refresh, 'append' for incremental.

    Returns:
        Row count written.
    """
    engine = get_engine()
    full_table = f"raw.{table_name}"

    # Ensure raw schema exists
    with engine.begin() as conn:
        conn.execute(text(
            "IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'raw') "
            "EXEC('CREATE SCHEMA raw')"
        ))

    # SQL Server limit: 2100 parameters per INSERT batch.
    # Calculate safe chunksize based on column count.
    num_cols = len(df.columns)
    safe_chunksize = max(1, 2000 // num_cols)

    df.to_sql(
        name=table_name,
        schema="raw",
        con=engine,
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=safe_chunksize,
    )
    row_count = len(df)
    print(f"  → {full_table}: {row_count:,} rows loaded")
    return row_count


def execute_sql_file(filepath: str) -> None:
    """Execute a .sql file against the database.

    Splits on GO statements to handle multi-batch scripts.
    """
    engine = get_engine()
    with open(filepath, "r") as f:
        script = f.read()

    # Split on GO (case-insensitive, standalone on its own line)
    import re
    batches = re.split(r"^\s*GO\s*$", script, flags=re.MULTILINE | re.IGNORECASE)

    with engine.begin() as conn:
        for batch in batches:
            batch = batch.strip()
            if batch:
                conn.execute(text(batch))