# tests/test_api_todos.py
import uuid
import pytest


def make_user(client) -> dict:
    r = client.post("/users", json={
        "email": f"{uuid.uuid4()}@test.com",
        "display_name": "User",
    })
    return r.json()


def make_list(client, owner_id: str) -> dict:
    r = client.post("/lists", json={"owner_id": owner_id, "name": "List"})
    return r.json()


def make_todo(client, list_id: str, created_by: str, **kwargs) -> dict:
    payload = {"created_by": created_by, "title": "Do something", **kwargs}
    r = client.post(f"/lists/{list_id}/todos", json=payload)
    assert r.status_code == 201
    return r.json()


def test_create_todo(client):
    user = make_user(client)
    lst = make_list(client, user["id"])
    r = client.post(f"/lists/{lst['id']}/todos", json={
        "created_by": user["id"],
        "title": "Buy milk",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Buy milk"
    assert data["status"] == "pending"
    assert data["completed_at"] is None


def test_create_todo_in_archived_list_fails(client):
    # BR-L01
    user = make_user(client)
    lst = make_list(client, user["id"])
    client.patch(f"/lists/{lst['id']}/archive")
    r = client.post(f"/lists/{lst['id']}/todos", json={
        "created_by": user["id"],
        "title": "Late task",
    })
    assert r.status_code == 409


def test_update_status_to_completed_sets_completed_at(client):
    # BR-T02
    user = make_user(client)
    lst = make_list(client, user["id"])
    todo = make_todo(client, lst["id"], user["id"])
    r = client.patch(f"/todos/{todo['id']}", json={"status": "completed"})
    assert r.status_code == 200
    assert r.json()["completed_at"] is not None


def test_update_completed_todo_title_fails(client):
    # BR-T01
    user = make_user(client)
    lst = make_list(client, user["id"])
    todo = make_todo(client, lst["id"], user["id"])
    client.patch(f"/todos/{todo['id']}", json={"status": "completed"})
    r = client.patch(f"/todos/{todo['id']}", json={"title": "New title"})
    assert r.status_code == 409


def test_update_completed_todo_status_fails(client):
    # BR-T01
    user = make_user(client)
    lst = make_list(client, user["id"])
    todo = make_todo(client, lst["id"], user["id"])
    client.patch(f"/todos/{todo['id']}", json={"status": "completed"})
    r = client.patch(f"/todos/{todo['id']}", json={"status": "pending"})
    assert r.status_code == 409


def test_update_todo_status_in_archived_list_fails(client):
    # BR-T03
    user = make_user(client)
    lst = make_list(client, user["id"])
    todo = make_todo(client, lst["id"], user["id"])
    client.patch(f"/lists/{lst['id']}/archive")
    r = client.patch(f"/todos/{todo['id']}", json={"status": "in_progress"})
    assert r.status_code == 409


def test_soft_delete_todo(client):
    user = make_user(client)
    lst = make_list(client, user["id"])
    todo = make_todo(client, lst["id"], user["id"])
    r = client.delete(f"/todos/{todo['id']}")
    assert r.status_code == 200
    fetched = client.get(f"/todos/{todo['id']}").json()
    assert fetched["is_deleted"] is True


def test_list_active_todos_excludes_deleted_and_completed(client):
    user = make_user(client)
    lst = make_list(client, user["id"])
    t1 = make_todo(client, lst["id"], user["id"], title="Active")
    t2 = make_todo(client, lst["id"], user["id"], title="Done")
    t3 = make_todo(client, lst["id"], user["id"], title="Deleted")
    client.patch(f"/todos/{t2['id']}", json={"status": "completed"})
    client.delete(f"/todos/{t3['id']}")
    r = client.get(f"/lists/{lst['id']}/todos?active=true")
    ids = [t["id"] for t in r.json()]
    assert t1["id"] in ids
    assert t2["id"] not in ids
    assert t3["id"] not in ids
