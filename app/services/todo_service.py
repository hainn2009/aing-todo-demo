# app/services/todo_service.py
from datetime import datetime, date, timezone
import psycopg2.extensions


def _get_todo(cur, todo_id: str) -> tuple | None:
    """Fetch todo joined with list to get archived_at (10-tuple)."""
    cur.execute(
        """
        SELECT t.id, t.list_id, t.created_by, t.title, t.status,
               t.priority, t.due_date, t.completed_at, t.is_deleted,
               l.archived_at
        FROM todos t
        JOIN todo_lists l ON t.list_id = l.id
        WHERE t.id = %s
        """,
        (todo_id,),
    )
    return cur.fetchone()


def _row_to_todo(row: tuple) -> dict:
    """
    Convert a 10-tuple to a todo dict.
    row[0..8] = todo columns; row[9] = l.archived_at (ignored in output,
    used only internally for business rule checks).
    """
    return {
        "id": str(row[0]),
        "list_id": str(row[1]),
        "created_by": str(row[2]),
        "title": row[3],
        "status": row[4],
        "priority": row[5],
        "due_date": row[6].isoformat() if row[6] else None,
        "completed_at": row[7].isoformat() if row[7] else None,
        "is_deleted": row[8],
    }


def create_todo(
    conn: psycopg2.extensions.connection,
    list_id: str,
    created_by: str,
    title: str,
    priority: str = "medium",
    due_date: date | None = None,
    is_imported: bool = False,
) -> dict:
    with conn.cursor() as cur:
        # BR-L01: cannot add todo to archived list
        cur.execute("SELECT archived_at FROM todo_lists WHERE id = %s", (list_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("List not found")
        if row[0] is not None:
            raise PermissionError("Cannot add todo to archived list (BR-L01)")

        # BR-T04: due_date must not be in the past
        if due_date and due_date < date.today() and not is_imported:
            raise ValueError("due_date cannot be in the past (BR-T04)")

        cur.execute(
            """
            INSERT INTO todos (id, list_id, created_by, title, status, priority, due_date, is_deleted)
            VALUES (gen_random_uuid(), %s, %s, %s, 'pending', %s, %s, false)
            RETURNING id, list_id, created_by, title, status, priority, due_date, completed_at, is_deleted
            """,
            (list_id, created_by, title, priority, due_date),
        )
        row = cur.fetchone()
        conn.commit()
        # Append None for archived_at to make a consistent 10-tuple for _row_to_todo
        return _row_to_todo(row + (None,))


def get_todo(conn: psycopg2.extensions.connection, todo_id: str) -> dict | None:
    with conn.cursor() as cur:
        row = _get_todo(cur, todo_id)
        return _row_to_todo(row) if row else None


def update_todo(
    conn: psycopg2.extensions.connection,
    todo_id: str,
    title: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_date: date | None = None,
) -> dict:
    with conn.cursor() as cur:
        row = _get_todo(cur, todo_id)
        if not row:
            raise ValueError("Todo not found")

        current_status = row[4]
        list_archived_at = row[9]

        # BR-T01: completed todo cannot change title or status
        if current_status == "completed" and (title is not None or status is not None):
            raise PermissionError(
                "Cannot modify completed todo title or status (BR-T01)"
            )

        # BR-T03: todo in archived list cannot change status
        if list_archived_at is not None and status is not None:
            raise PermissionError(
                "Cannot change status of todo in archived list (BR-T03)"
            )

        updates = {}
        if title is not None:
            updates["title"] = title
        if status is not None:
            updates["status"] = status
        if priority is not None:
            updates["priority"] = priority
        if due_date is not None:
            updates["due_date"] = due_date

        # BR-T02: system sets completed_at when status → completed
        if status == "completed":
            updates["completed_at"] = datetime.now(timezone.utc)

        if not updates:
            return _row_to_todo(row)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [todo_id]
        cur.execute(
            f"""
            UPDATE todos SET {set_clause}
            WHERE id = %s
            RETURNING id, list_id, created_by, title, status, priority,
                      due_date, completed_at, is_deleted
            """,
            values,
        )
        updated = cur.fetchone()
        conn.commit()
        # Append None for archived_at to make a consistent 10-tuple for _row_to_todo
        return _row_to_todo(updated + (None,))


def soft_delete_todo(conn: psycopg2.extensions.connection, todo_id: str) -> dict | None:
    # Soft delete only — NEVER SQL DELETE on todos (semantic model: is_deleted = soft delete)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE todos SET is_deleted = true
            WHERE id = %s
            RETURNING id, list_id, created_by, title, status, priority,
                      due_date, completed_at, is_deleted
            """,
            (todo_id,),
        )
        row = cur.fetchone()
        conn.commit()
        # Append None for archived_at to make a consistent 10-tuple for _row_to_todo
        return _row_to_todo(row + (None,)) if row else None


def list_todos(
    conn: psycopg2.extensions.connection, list_id: str, active_only: bool = False
) -> list[dict]:
    with conn.cursor() as cur:
        if active_only:
            # ActiveTodo computed concept: is_deleted=false AND status NOT IN ('completed','cancelled')
            cur.execute(
                """
                SELECT id, list_id, created_by, title, status, priority,
                       due_date, completed_at, is_deleted
                FROM todos
                WHERE list_id = %s
                  AND is_deleted = false
                  AND status NOT IN ('completed', 'cancelled')
                """,
                (list_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, list_id, created_by, title, status, priority,
                       due_date, completed_at, is_deleted
                FROM todos WHERE list_id = %s
                """,
                (list_id,),
            )
        # Append None for archived_at to make a consistent 10-tuple for _row_to_todo
        return [_row_to_todo(r + (None,)) for r in cur.fetchall()]
