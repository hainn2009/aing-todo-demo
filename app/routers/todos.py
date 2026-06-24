# app/routers/todos.py
# Routers contain NO business logic — only parse HTTP, call service, return response.
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.db import get_conn, put_conn
from app.services import todo_service

router = APIRouter(tags=["todos"])


class CreateTodoRequest(BaseModel):
    created_by: str
    title: str = Field(max_length=500)
    priority: str = "medium"
    due_date: date | None = None


class UpdateTodoRequest(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None


@router.post("/lists/{list_id}/todos", status_code=201)
def create_todo(list_id: str, body: CreateTodoRequest) -> dict:
    conn = get_conn()
    try:
        try:
            return todo_service.create_todo(
                conn, list_id, body.created_by, body.title, body.priority, body.due_date
            )
        except PermissionError as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            raise HTTPException(404, str(e))
    finally:
        put_conn(conn)


@router.get("/todos/{todo_id}")
def get_todo(todo_id: str) -> dict:
    conn = get_conn()
    try:
        result = todo_service.get_todo(conn, todo_id)
        if not result:
            raise HTTPException(404, "Todo not found")
        return result
    finally:
        put_conn(conn)


@router.patch("/todos/{todo_id}")
def update_todo(todo_id: str, body: UpdateTodoRequest) -> dict:
    conn = get_conn()
    try:
        try:
            return todo_service.update_todo(
                conn, todo_id, body.title, body.status, body.priority, body.due_date
            )
        except PermissionError as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            raise HTTPException(404, str(e))
    finally:
        put_conn(conn)


@router.delete("/todos/{todo_id}")
def delete_todo(todo_id: str) -> dict:
    conn = get_conn()
    try:
        result = todo_service.soft_delete_todo(conn, todo_id)
        if not result:
            raise HTTPException(404, "Todo not found")
        return result
    finally:
        put_conn(conn)


@router.get("/lists/{list_id}/todos")
def list_todos(list_id: str, active: bool = Query(default=False)) -> list:
    conn = get_conn()
    try:
        return todo_service.list_todos(conn, list_id, active_only=active)
    finally:
        put_conn(conn)
