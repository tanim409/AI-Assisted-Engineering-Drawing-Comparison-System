"""PostgreSQL connection helpers."""
import os
from contextlib import contextmanager

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "engineering_drawings")


def _connection_kwargs(database: str) -> dict:
    return {
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "dbname": database,
    }


_db_checked = False

def ensure_database_exists():
    """Create the configured PostgreSQL database when it is missing (local dev only)."""
    global _db_checked
    if _db_checked or POSTGRES_DATABASE == "postgres":
        return
    _db_checked = True
    try:
        with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (POSTGRES_DATABASE,))
                if not cursor.fetchone():
                    cursor.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(POSTGRES_DATABASE)))
    except Exception:
        # Ignore database creation errors on managed cloud platforms like Supabase
        pass


def get_raw_connection():
    if not _db_checked:
        ensure_database_exists()
    return psycopg.connect(**_connection_kwargs(POSTGRES_DATABASE), row_factory=dict_row)



@contextmanager
def connect():
    """Yield a PostgreSQL connection and commit or roll back its transaction."""
    conn = get_raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
