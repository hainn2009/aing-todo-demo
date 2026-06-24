# Task 7 Report — Todos API + Business Rules + README

**Status:** DONE

## Files Created / Modified

| File | Action |
|------|--------|
| `tests/test_api_todos.py` | Created — 8 tests (all 7 plan tests + test_list_active_todos) |
| `app/services/todo_service.py` | Created — all BR-T01–T04 enforced with cited IDs |
| `app/routers/todos.py` | Created — no business logic, HTTP-only |
| `app/main.py` | Modified — registered todos router |
| `README.md` | Created |

## Test Results

### pytest tests/ -v

```
33 passed, 1 warning in 0.35s
```

Breakdown:
- `test_api_lists.py` — 6 passed
- `test_api_todos.py` — 8 passed (all 7 plan tests present + test_list_active_todos_excludes_deleted_and_completed which counts as test #7 per the plan)
- `test_generate.py` — 19 passed (generator unit tests)

### dbt test

```
PASS=18 WARN=0 ERROR=0 SKIP=0 TOTAL=18
```

(2 warnings: dbt deprecation notices for `relationships` test argument format — cosmetic, not failures)

## Business Rules Verification

| Rule | Location | Test |
|------|----------|------|
| BR-L01 | `todo_service.create_todo` line 50 | `test_create_todo_in_archived_list_fails` PASS |
| BR-T01 | `todo_service.update_todo` line 83 | `test_update_completed_todo_title_fails` PASS, `test_update_completed_todo_status_fails` PASS |
| BR-T02 | `todo_service.update_todo` line 96 | `test_update_status_to_completed_sets_completed_at` PASS |
| BR-T03 | `todo_service.update_todo` line 88 | `test_update_todo_status_in_archived_list_fails` PASS |
| BR-T04 | `todo_service.create_todo` line 54 | present in service (no separate test, per plan) |

## _row_to_todo 10-tuple consistency

All callers that do non-JOIN queries append `(None,)` to the 9-element RETURNING tuple before calling `_row_to_todo`:
- `create_todo`: `row + (None,)`
- `update_todo`: `updated + (None,)`
- `soft_delete_todo`: `row + (None,)`
- `list_todos`: `r + (None,)` for each row

`get_todo` uses `_get_todo()` which JOINs `todo_lists` and naturally returns `l.archived_at` as element [9].

## Constraints Met

- [x] Routers contain NO business logic
- [x] Business rules cited by BR-xxx in services
- [x] No ORM — raw psycopg2 SQL only
- [x] Soft delete: `UPDATE todos SET is_deleted = true` (no SQL DELETE)
- [x] ActiveTodo filter: `is_deleted = false AND status NOT IN ('completed', 'cancelled')`
- [x] All 7 plan tests present
- [x] `completed_at` never accepted as API input — system-set only

## Commits

Not committed yet — waiting for caller to approve and commit.
