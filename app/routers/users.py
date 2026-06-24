# app/routers/users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import get_conn, put_conn
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: str = Field(max_length=255)
    display_name: str = Field(max_length=255)


@router.post("", status_code=201)
def create_user(body: CreateUserRequest) -> dict:
    conn = get_conn()
    try:
        try:
            return user_service.create_user(conn, body.email, body.display_name)
        except ValueError as e:
            raise HTTPException(409, str(e))
    finally:
        put_conn(conn)


@router.get("/{user_id}")
def get_user(user_id: str) -> dict:
    conn = get_conn()
    try:
        result = user_service.get_user(conn, user_id)
        if not result:
            raise HTTPException(404, "User not found")
        return result
    finally:
        put_conn(conn)
