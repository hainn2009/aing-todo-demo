# tests/test_generate.py
import yaml
import pytest
from generate import generate_ddl, generate_pydantic, generate_dbt_schema

MINIMAL_MODEL = yaml.safe_load("""
version: "1.0"
domain: TestApp
entities:
  Task:
    source_table: tasks
    attributes:
      id:
        type: uuid
        nullable: false
      title:
        type: string
        nullable: false
        max_length: 200
      status:
        type: enum
        values: [pending, done]
        default: pending
      owner_id:
        type: uuid
        nullable: false
        references: User.id
      notes:
        type: string
        nullable: true
  User:
    source_table: users
    attributes:
      id:
        type: uuid
        nullable: false
      email:
        type: string
        nullable: false
        unique: true
    business_rules:
      - id: BR-U01
        rule: "Email unique"
    tests:
      - not_null: [id, email]
      - unique: [email]
""")


# --- DDL tests ---

def test_ddl_creates_table():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "CREATE TABLE IF NOT EXISTS tasks" in ddl

def test_ddl_uuid_not_null():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "id UUID NOT NULL" in ddl

def test_ddl_varchar_max_length():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "title VARCHAR(200) NOT NULL" in ddl

def test_ddl_enum_check_constraint():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "CHECK (status IN ('pending', 'done'))" in ddl

def test_ddl_enum_default():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "DEFAULT 'pending'" in ddl

def test_ddl_nullable_no_not_null():
    ddl = generate_ddl(MINIMAL_MODEL)
    notes_lines = [l for l in ddl.splitlines() if "notes" in l and "CONSTRAINT" not in l]
    assert len(notes_lines) == 1
    assert "NOT NULL" not in notes_lines[0]

def test_ddl_foreign_key():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "REFERENCES users(id)" in ddl

def test_ddl_unique_constraint_from_attribute():
    ddl = generate_ddl(MINIMAL_MODEL)
    assert "UNIQUE (email)" in ddl


# --- Pydantic tests ---

def test_pydantic_class_name():
    code = generate_pydantic(MINIMAL_MODEL)
    assert "class Task(BaseModel):" in code

def test_pydantic_literal_enum():
    code = generate_pydantic(MINIMAL_MODEL)
    assert "Literal['pending', 'done']" in code

def test_pydantic_optional_nullable():
    code = generate_pydantic(MINIMAL_MODEL)
    # notes is nullable
    assert "Optional[str]" in code

def test_pydantic_business_rule_id_in_comment():
    code = generate_pydantic(MINIMAL_MODEL)
    assert "BR-U01" in code

def test_pydantic_required_imports():
    code = generate_pydantic(MINIMAL_MODEL)
    assert "from uuid import UUID" in code
    assert "from pydantic import BaseModel" in code


# --- dbt schema tests ---

def test_dbt_schema_version():
    raw = generate_dbt_schema(MINIMAL_MODEL)
    data = yaml.safe_load(raw)
    assert data["version"] == 2

def test_dbt_schema_source_name():
    raw = generate_dbt_schema(MINIMAL_MODEL)
    data = yaml.safe_load(raw)
    assert data["sources"][0]["name"] == "testapp"

def test_dbt_not_null_test_on_non_nullable_col():
    raw = generate_dbt_schema(MINIMAL_MODEL)
    data = yaml.safe_load(raw)
    tasks_table = next(t for t in data["sources"][0]["tables"] if t["name"] == "tasks")
    id_col = next(c for c in tasks_table["columns"] if c["name"] == "id")
    assert "not_null" in id_col["tests"]

def test_dbt_accepted_values_test():
    raw = generate_dbt_schema(MINIMAL_MODEL)
    data = yaml.safe_load(raw)
    tasks_table = next(t for t in data["sources"][0]["tables"] if t["name"] == "tasks")
    status_col = next(c for c in tasks_table["columns"] if c["name"] == "status")
    av = next(t for t in status_col["tests"] if isinstance(t, dict) and "accepted_values" in t)
    assert av["accepted_values"]["values"] == ["pending", "done"]

def test_dbt_relationships_test():
    raw = generate_dbt_schema(MINIMAL_MODEL)
    data = yaml.safe_load(raw)
    tasks_table = next(t for t in data["sources"][0]["tables"] if t["name"] == "tasks")
    owner_col = next(c for c in tasks_table["columns"] if c["name"] == "owner_id")
    rel = next(t for t in owner_col["tests"] if isinstance(t, dict) and "relationships" in t)
    assert rel["relationships"]["field"] == "id"

def test_dbt_unique_test_from_tests_block():
    raw = generate_dbt_schema(MINIMAL_MODEL)
    data = yaml.safe_load(raw)
    users_table = next(t for t in data["sources"][0]["tables"] if t["name"] == "users")
    email_col = next(c for c in users_table["columns"] if c["name"] == "email")
    assert "unique" in email_col["tests"]
