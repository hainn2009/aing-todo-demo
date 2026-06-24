# app/routers/users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import get_conn, put_conn

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: str = Field(max_length=255)
    display_name: str = Field(max_length=255)


@router.post("", status_code=201)
def create_user(body: CreateUserRequest) -> dict:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # BR-U01: email unique across all accounts including deactivated
            cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
            if cur.fetchone():
                raise HTTPException(409, "Email already registered (BR-U01)")
            cur.execute(
                """
                INSERT INTO users (id, email, display_name, created_at, is_active)
                VALUES (gen_random_uuid(), %s, %s, NOW(), true)
                RETURNING id, email, display_name, created_at, is_active
                """,
                (body.email, body.display_name),
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
    finally:
        put_conn(conn)


@router.get("/{user_id}")
def get_user(user_id: str) -> dict:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, created_at, is_active FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "User not found")
            return {
                "id": str(row[0]),
                "email": row[1],
                "display_name": row[2],
                "created_at": row[3].isoformat(),
                "is_active": row[4],
            }
    finally:
        put_conn(conn)
