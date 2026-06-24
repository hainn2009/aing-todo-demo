# Todo App — Specification

## Domain

Application quản lý công việc cá nhân với lists, todos, và collaborators.

## Use Cases

### UC-01: User creates a todo list
- POST /lists với body {owner_id, name, is_shared?}
- name required, max 255 chars
- is_shared mặc định false

### UC-02: User adds a todo to a list
- POST /lists/{list_id}/todos với body {created_by, title, priority?, due_date?}
- title required, max 500 chars
- due_date nếu cung cấp: phải >= hôm nay (BR-T04)
- List phải chưa archive (BR-L01)

### UC-03: User updates a todo
- PATCH /todos/{id} với body {title?, status?, priority?, due_date?}
- Không thể thay đổi status hoặc title nếu todo đang completed (BR-T01)
- Khi status → completed: system tự set completed_at (BR-T02)
- Không thể đổi status nếu list đã archive (BR-T03)

### UC-04: User archives a list
- PATCH /lists/{id}/archive
- Sau archive: không thêm todo mới (BR-L01), không đổi status (BR-T03)

### UC-05: User soft-deletes a todo
- DELETE /todos/{id} → set is_deleted = true
- Không bao giờ dùng SQL DELETE

### UC-06: User views active todos của một list
- GET /lists/{list_id}/todos?active=true
- active=true filter: is_deleted=false AND status NOT IN ('completed','cancelled')

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

## Acceptance Criteria

- BR-U01, BR-U02, BR-L01, BR-L02, BR-T01, BR-T02, BR-T03, BR-T04 enforced at service layer
- completed_at never accepted as API input — system-set only (BR-T02)
- No SQL DELETE on todos or users table
- `dbt test` passes on fresh DB after schema.sql applied
- `python generate.py` runs idempotently — output identical on second run

## Out of Scope

- Authentication / JWT
- Frontend UI
- Docker Compose
- dbt CI/CD pipeline config
