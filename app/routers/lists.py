# app/routers/lists.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import get_conn, put_conn
from app.services.list_service import create_list, get_list, archive_list

router = APIRouter(prefix="/lists", tags=["lists"])


class CreateListRequest(BaseModel):
    owner_id: str
    name: str = Field(max_length=255)
    is_shared: bool = False


@router.post("", status_code=201)
def create_list_route(body: CreateListRequest) -> dict:
    conn = get_conn()
    try:
        return create_list(conn, body.owner_id, body.name, body.is_shared)
    finally:
        put_conn(conn)


@router.get("/{list_id}")
def get_list_route(list_id: str) -> dict:
    conn = get_conn()
    try:
        result = get_list(conn, list_id)
        if not result:
            raise HTTPException(404, "List not found")
        return result
    finally:
        put_conn(conn)


@router.patch("/{list_id}/archive")
def archive_list_route(list_id: str) -> dict:
    conn = get_conn()
    try:
        result = archive_list(conn, list_id)
        if not result:
            raise HTTPException(404, "List not found or already archived")
        return result
    finally:
        put_conn(conn)
