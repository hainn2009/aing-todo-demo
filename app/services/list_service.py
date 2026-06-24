# app/services/list_service.py
from datetime import datetime, timezone
import psycopg2.extensions


def create_list(
    conn: psycopg2.extensions.connection,
    owner_id: str,
    name: str,
    is_shared: bool = False,
) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO todo_lists (id, owner_id, name, is_shared)
            VALUES (gen_random_uuid(), %s, %s, %s)
            RETURNING id, owner_id, name, is_shared, archived_at
            """,
            (owner_id, name, is_shared),
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_list(row)


def get_list(conn: psycopg2.extensions.connection, list_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, owner_id, name, is_shared, archived_at FROM todo_lists WHERE id = %s",
            (list_id,),
        )
        row = cur.fetchone()
        return _row_to_list(row) if row else None


def archive_list(conn: psycopg2.extensions.connection, list_id: str) -> dict | None:
    # BR-L01: after archive, no new todos allowed (enforced in todo_service.create_todo)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE todo_lists SET archived_at = %s
            WHERE id = %s AND archived_at IS NULL
            RETURNING id, owner_id, name, is_shared, archived_at
            """,
            (datetime.now(timezone.utc), list_id),
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_list(row) if row else None


def _row_to_list(row: tuple) -> dict:
    return {
        "id": str(row[0]),
        "owner_id": str(row[1]),
        "name": row[2],
        "is_shared": row[3],
        "archived_at": row[4].isoformat() if row[4] else None,
    }
