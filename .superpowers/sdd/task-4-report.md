# Task 4 Report — Database Setup + dbt

**Status:** DONE_WITH_CONCERNS

## Commits Made

- `d15224f` — `feat: dbt setup and DB schema applied`
  - Files: `dbt/dbt_project.yml`, `dbt/models/sources.yml`, `dbt/models/schema.yml`
  - `dbt/profiles.yml` NOT committed (gitignored, as required)

## dbt test Output

```
18 data tests run. PASS=18 WARN=0 ERROR=0 SKIP=0 TOTAL=18
```

Tests passing:
- `not_null` on: users.id, users.email, users.display_name, users.created_at, todo_lists.id, todo_lists.owner_id, todo_lists.name, todos.id, todos.list_id, todos.created_by, todos.title, todos.status (12 tests)
- `unique` on: users.email (1 test)
- `accepted_values` on: todos.status, todos.priority (2 tests)
- `relationships` on: todo_lists.owner_id→users.id, todos.list_id→todo_lists.id, todos.created_by→users.id (3 tests)

## Concerns

### 1. Generator does not emit PRIMARY KEY constraints (medium severity)

`generate.py` emits UNIQUE and FK constraints but **no PRIMARY KEY** for any table's `id` column. This caused FK creation to fail when applying `schema.sql` to fresh databases (PostgreSQL requires a unique/PK constraint on the referenced column).

**Workaround applied:** Manually ran `ALTER TABLE users ADD CONSTRAINT pk_users PRIMARY KEY (id)` and `ALTER TABLE todo_lists ADD CONSTRAINT pk_todo_lists PRIMARY KEY (id)` before re-applying schema.sql.

**Proper fix:** Update `generate.py` to emit `PRIMARY KEY` for columns named `id` or those flagged as primary keys in the semantic model.

### 2. Custom dbt generic tests removed from schema.yml (low severity)

`generate.py` emits table-level custom tests (`no_new_todo_in_archived_list`, `completed_must_have_completed_at`, `non_completed_must_not_have_completed_at`) in the dbt `tests:` syntax that expects macros in `dbt/tests/`. These caused compilation errors.

**Workaround applied:** Removed the 3 table-level `tests:` blocks from `dbt/models/schema.yml` per the task brief's guidance. This is the one manual edit to a generated file.

**Proper fix:** Either (a) implement dbt generic test macros in `dbt/tests/`, or (b) update `generate.py` to emit these as singular tests (`.sql` files in `dbt/tests/`) rather than generic test blocks in schema.yml.

### 3. dbt-core version conflict

The `.venv` had `dbt-core==2.0.0a2` (Fusion) which does not support the postgres adapter. Required reinstalling to `dbt-core==1.8.2` + `dbt-postgres==1.8.2`.

**Fix applied:** `pip install "dbt-core==1.8.2" "dbt-postgres==1.8.2" --force-reinstall`

**Recommendation:** Pin `dbt-core==1.8.2` in `requirements.txt` to prevent accidental upgrade to 2.x.

### 4. sources.yml source name diverges from schema.yml

The plan specified `name: todo_app` in `sources.yml`, but `schema.yml` uses `name: todoapp` (generated from `domain: TodoApp`). Using `todoapp` caused a duplicate source conflict. Used `todo_app` in `sources.yml` per the plan. Both sources now coexist (6 sources total: 3 from each file), which is harmless but slightly redundant.

## Database State

Both `todo_app` and `todo_app_test` databases contain:
- `users` table (with manually added PK on id)
- `todo_lists` table (with manually added PK on id)
- `todos` table (FK constraints working)

---

## Bug Fix Follow-up — 2026-06-24

**Status:** DONE

### Fixes Applied

1. **Fix 1 — PRIMARY KEY in DDL generator**: Added `CONSTRAINT pk_{table} PRIMARY KEY ({pk_col})` logic in `generate_ddl`. Identifies first `uuid NOT NULL` attribute as PK. All 3 tables now emit proper PK constraints.

2. **Fix 2 — Domain name snake_case**: Changed `generate_dbt_schema` to use `re.sub(r"(?<!^)(?=[A-Z])", "_", _raw).lower()`. `TodoApp` → `todo_app`. Updated `test_dbt_schema_source_name` to expect `"test_app"` (from `TestApp`).

3. **Fix 3 — Remove custom dbt tests**: Deleted the `custom_tests` block from `generate_dbt_schema`. Custom SQL logic stays in application layer (services/), not in dbt schema.yml.

4. **Fix 4 — Pin dbt-core**: Added `dbt-core==1.8.2` to `requirements.txt`.

5. **Bonus — sources.yml conflict resolved**: `sources.yml` previously defined `name: todo_app` as a workaround. Now that `schema.yml` also emits `todo_app`, cleared `sources.yml` to `sources: []` to avoid duplicate source error.

### Verification

- **pytest**: 19/19 passed (`tests/test_generate.py`)
- **dbt test**: PASS=18 WARN=0 ERROR=0 SKIP=0 TOTAL=18
- **PRIMARY KEY in schema.sql**: `CONSTRAINT pk_users PRIMARY KEY (id)`, `CONSTRAINT pk_todo_lists PRIMARY KEY (id)`, `CONSTRAINT pk_todos PRIMARY KEY (id)` — confirmed via `pg_constraint` query
- **Source name in dbt/models/schema.yml**: `name: todo_app` — confirmed
- **No table-level `tests:` blocks in schema.yml**: confirmed

### Files Changed

- `generate.py` — all 4 fixes applied
- `requirements.txt` — `dbt-core==1.8.2` added
- `tests/test_generate.py` — `test_dbt_schema_source_name` updated to expect `test_app`
- `generated/ddl/schema.sql` — regenerated with PRIMARY KEY constraints
- `dbt/models/schema.yml` — regenerated: `todo_app` source, no custom tests
- `dbt/models/sources.yml` — cleared to `sources: []`
