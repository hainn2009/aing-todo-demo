# tests/conftest.py
import os
import pytest
import psycopg2
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()


@pytest.fixture(scope="session")
def db_conn():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME_TEST", "todo_app_test"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def clean_db(db_conn):
    yield
    db_conn.rollback()
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM todos")
        cur.execute("DELETE FROM todo_lists")
        cur.execute("DELETE FROM users")
    db_conn.commit()


@pytest.fixture(scope="session")
def client():
    os.environ["DB_NAME"] = os.getenv("DB_NAME_TEST", "todo_app_test")
    from app.main import app
    from app.db import init_db
    init_db()
    return TestClient(app)
