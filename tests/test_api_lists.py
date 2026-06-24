# tests/test_api_lists.py
import uuid
import pytest


def make_user(client) -> dict:
    r = client.post("/users", json={
        "email": f"{uuid.uuid4()}@test.com",
        "display_name": "Test User",
    })
    assert r.status_code == 201
    return r.json()


def test_create_user(client):
    r = client.post("/users", json={
        "email": "alice@test.com",
        "display_name": "Alice",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "alice@test.com"
    assert "id" in data


def test_create_user_duplicate_email_fails(client):
    payload = {"email": "dup@test.com", "display_name": "D"}
    client.post("/users", json=payload)
    r = client.post("/users", json=payload)
    assert r.status_code == 409


def test_create_list(client):
    user = make_user(client)
    r = client.post("/lists", json={"owner_id": user["id"], "name": "My List"})
    assert r.status_code == 201
    assert r.json()["name"] == "My List"
    assert r.json()["archived_at"] is None


def test_get_list(client):
    user = make_user(client)
    created = client.post("/lists", json={"owner_id": user["id"], "name": "Proj"}).json()
    r = client.get(f"/lists/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_archive_list(client):
    user = make_user(client)
    lst = client.post("/lists", json={"owner_id": user["id"], "name": "Old"}).json()
    r = client.patch(f"/lists/{lst['id']}/archive")
    assert r.status_code == 200
    assert r.json()["archived_at"] is not None


def test_archive_list_not_found(client):
    r = client.patch(f"/lists/{uuid.uuid4()}/archive")
    assert r.status_code == 404
