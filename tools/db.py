"""
Database connection utilities for JaxAI tools.
"""

import os

# Global reference to db_pool from main.py - set during app initialization
_db_pool = None


def set_db_pool(pool):
    """Set the database pool reference from main.py"""
    global _db_pool
    _db_pool = pool


def get_db_connection():
    """Get database connection from the pool or create direct connection as fallback"""
    global _db_pool

    # Try to use the shared pool first
    if _db_pool is not None:
        try:
            conn = _db_pool.getconn()
            return conn
        except Exception:
            pass

    # Fallback to direct connection
    import psycopg2
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "store_visits"),
        user=os.environ.get("DB_USER", "store_tracker"),
        password=os.environ.get("DB_PASSWORD")
    )
    return conn


def release_db_connection(conn):
    """Release connection back to pool or close it"""
    global _db_pool

    if _db_pool is not None:
        try:
            _db_pool.putconn(conn)
            return
        except Exception:
            pass

    # Fallback: just close the connection
    try:
        conn.close()
    except Exception:
        pass
