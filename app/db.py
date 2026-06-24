# app/db.py
import os
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def init_db() -> None:
    global _pool
    _pool = psycopg2.pool.SimpleConnectionPool(
        1,
        10,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "todo_app"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def get_conn() -> psycopg2.extensions.connection:
    assert _pool is not None, "DB not initialised — call init_db() first"
    return _pool.getconn()


def put_conn(conn: psycopg2.extensions.connection) -> None:
    assert _pool is not None
    _pool.putconn(conn)
