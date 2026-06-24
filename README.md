# AING Todo Demo

Reference implementation của AING semantic-first methodology.

## Nguyên tắc

`semantic/semantic_model.yaml` là **single source of truth** — mọi thứ khác được sinh ra từ nó:
- Con người chỉ review spec và semantic model, không review code
- `generate.py` sinh boilerplate deterministically
- AI sinh `app/` từ spec + semantic

## Quick Start

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env  # chỉnh DB credentials
psql -U postgres -d todo_app -f generated/ddl/schema.sql
uvicorn app.main:app --reload
```

Docs: http://localhost:8000/docs

## Workflow

```
1. Sửa semantic/semantic_model.yaml
2. python generate.py
3. Review generated/ddl/schema.sql → viết migration nếu cần
4. Prompt AI để update app/:
```

## AI Prompt Template

```
Implement [feature] theo spec tại spec/spec.md.
Đọc semantic/semantic_model.yaml trước — business rules có ID (BR-xxx),
enforce chúng trong services/ với comment trích dẫn ID.
Pydantic models import từ generated/pydantic_models.py, không viết lại.
Stack: FastAPI + psycopg2 + PostgreSQL. Không dùng ORM.
generated/ và dbt/models/schema.yml — KHÔNG sửa tay, chạy generate.py.
```

## Chạy Tests

```bash
pytest tests/ -v          # unit + API tests (33 tests)
cd dbt && dbt test        # data quality gate (18 tests)
```

## Business Rules

| ID | Rule | Enforced in |
|----|------|-------------|
| BR-U01 | Email unique kể cả tài khoản deactivate | `routers/users.py` |
| BR-U02 | Không hard-delete user | `routers/users.py` (soft-delete pattern) |
| BR-L01 | List đã archive không thêm todo mới | `services/todo_service.create_todo` |
| BR-T01 | completed todo không đổi title hoặc status | `services/todo_service.update_todo` |
| BR-T02 | `completed_at` system-set khi status → completed | `services/todo_service.update_todo` |
| BR-T03 | Todo trong archived list không đổi status | `services/todo_service.update_todo` |
| BR-T04 | `due_date` không được là ngày trong quá khứ | `services/todo_service.create_todo` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /users | Create user |
| GET | /users/{id} | Get user |
| POST | /lists | Create list |
| GET | /lists/{id} | Get list |
| PATCH | /lists/{id}/archive | Archive list |
| POST | /lists/{list_id}/todos | Create todo |
| GET | /todos/{id} | Get todo |
| PATCH | /todos/{id} | Update todo |
| DELETE | /todos/{id} | Soft-delete todo |
| GET | /lists/{list_id}/todos | List todos (supports ?active=true) |
