# app/services/user_service.py
import psycopg2.extensions


def create_user(conn: psycopg2.extensions.connection, email: str, display_name: str) -> dict:
    with conn.cursor() as cur:
        # BR-U01: email unique across all accounts including deactivated
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            raise ValueError("Email already registered (BR-U01)")
        cur.execute(
            """
            INSERT INTO users (id, email, display_name, created_at, is_active)
            VALUES (gen_random_uuid(), %s, %s, NOW(), true)
            RETURNING id, email, display_name, created_at, is_active
            """,
            (email, display_name),
        )
        row = cur.fetchone()
        conn.commit()
        return {
            "id": str(row[0]),
            "email": row[1],
            "display_name": row[2],
            "created_at": row[3].isoformat(),
            "is_active": row[4],
        }


def get_user(conn: psycopg2.extensions.connection, user_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, display_name, created_at, is_active FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "email": row[1],
            "display_name": row[2],
            "created_at": row[3].isoformat(),
            "is_active": row[4],
        }
