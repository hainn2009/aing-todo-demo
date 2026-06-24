# AING Semantic-First Methodology Guide

> Dành cho developer nội bộ — biết Python + FastAPI cơ bản, chưa biết AING.  
> Đọc một lần, làm theo từng bước.

---

## Phần 1 — Pipeline & Ai Làm Gì

### Pipeline 4 bước

```
[Human]  spec/spec.md                    ← viết use cases, acceptance criteria
[Human]  semantic/semantic_model.yaml    ← viết domain model + business rules
         ↓
[Script] python generate.py
         ↓ generated/ddl/schema.sql
         ↓ generated/pydantic_models.py
         ↓ dbt/models/schema.yml
         ↓
[AI]     implement app/                  ← prompt AI sinh routes + services
[Human]  review BR-xxx trong services/   ← CHỈ review đây, không đọc toàn bộ app/
         ↓
[CI]     dbt test                        ← data quality gate tự động
```

### Ai chạm file nào

| File / Thư mục | Người làm | Được sửa tay? |
|----------------|-----------|--------------|
| `spec/spec.md` | Human | ✅ |
| `semantic/semantic_model.yaml` | Human | ✅ |
| `generated/` | Script (`generate.py`) | ❌ — chạy `python generate.py` |
| `app/` | AI | ✅ — chỉ review BR comment |
| `dbt/models/schema.yml` | Script (`generate.py`) | ❌ |
| `dbt/dbt_project.yml` | Human | ✅ |

### Quy tắc duy nhất cần nhớ

> **Human chỉ review `semantic/semantic_model.yaml` và `spec/spec.md` — không bao giờ review code chi tiết trong `app/`.**

Khi AI sinh code sai → vấn đề nằm ở semantic model hoặc prompt, không phải ở code. Fix ở nguồn, không fix triệu chứng.

---

## Phần 2 — Walkthrough `aing_todo_demo`

### 2.1 Viết `semantic/semantic_model.yaml`

#### ① Mục tiêu của file

`semantic_model.yaml` không phải schema database, cũng không phải API spec. Nó là **ngôn ngữ chung** giữa ba bên:

- **Business/Product** — viết business rules bằng ngôn ngữ domain
- **Human reviewer** — đọc để hiểu hệ thống hoạt động như thế nào
- **AI** — đọc để implement đúng, không tự bịa ra rule

Câu hỏi kiểm tra: *"Nếu một người mới đọc file này, họ có hiểu domain hoạt động thế nào không?"* — nếu có, file đúng hướng.

#### ② Cấu trúc: bắt buộc vs. tùy chọn

```yaml
version: "1.0"          # ✅ bắt buộc
domain: TodoApp          # ✅ bắt buộc — PascalCase, dùng để đặt tên dbt source
description: "..."       # ✅ bắt buộc

entities:                # ✅ bắt buộc
  User:
    description: "..."
    source_table: users  # ✅ bắt buộc — tên bảng trong DB
    attributes:          # ✅ bắt buộc
      id: { type: uuid, nullable: false }
    business_rules:      # ✅ bắt buộc — ít nhất phải có (dù entity không có rule thì để [])
      - id: BR-U01
        rule: "..."
        rationale: "..."
    tests:               # ✅ bắt buộc — dùng để sinh dbt test
      - not_null: [id]

relationships:           # 🔶 khuyến nghị — giúp AI hiểu FK khi prompt
computed_concepts:       # ⬜ tùy chọn — định nghĩa filter/metric tái sử dụng
glossary:                # ⬜ tùy chọn — ánh xạ ngôn ngữ domain → kỹ thuật
```

Xem file thực tế: [`semantic/semantic_model.yaml`](../semantic/semantic_model.yaml)

#### ③ Logic gì vào semantic — logic gì để ngoài

**Nên vào semantic:**

| Loại logic | Ví dụ |
|-----------|-------|
| Constraint cấp dữ liệu | Email phải unique, title không được null |
| Business rule phát biểu được thành câu độc lập với tech stack | "Không hard-delete user" |
| Invariant bất biến theo thời gian | "completed todo không được sửa title" |
| Khái niệm domain cần đồng bộ AI | "xóa" = `is_deleted=true`, không phải SQL DELETE |

**Để ngoài (vào `services/` hoặc `spec/`):**

| Loại logic | Đặt ở đâu | Lý do |
|-----------|-----------|-------|
| "Trả 404 nếu không tìm thấy" | `routers/` | Phụ thuộc HTTP protocol |
| "completed_at = NOW() khi status → completed" | `services/` | BR có trong semantic (BR-T02), nhưng *cách set* là runtime logic |
| "Chỉ owner mới archive được list" | `services/` | Phụ thuộc auth system chưa có |
| Pagination, sorting | `routers/` | UI concern |

**Ranh giới kiểm tra:** Nếu rule có thể phát biểu mà không nhắc đến HTTP method, endpoint, hay framework → thuộc về semantic.

Ví dụ:
- ✅ "Email unique kể cả tài khoản đã deactivate" → vào semantic
- ❌ "POST /users trả 409 nếu email trùng" → vào spec hoặc router comment

#### ④ Tại sao có từng trường

Mỗi trường tồn tại có lý do. Nếu bỏ đi, mất gì?

**`id: BR-xxx` trong business_rules**

```yaml
business_rules:
  - id: BR-U01          # ← nếu bỏ id này
    rule: "Email unique kể cả tài khoản đã deactivate"
```

Mất: Code trong `services/` không thể trích dẫn. Khi đọc code sau 6 tháng, không biết rule này đến từ đâu, có còn hiệu lực không.

Với `id`:
```python
# services/user_service.py
# BR-U01: Email unique kể cả tài khoản đã deactivate
existing = db.query("SELECT id FROM users WHERE email = %s", [email])
if existing:
    raise HTTPException(409, "Email already exists")
```

**`rationale`**

```yaml
- id: BR-U02
  rule: "Không hard-delete user — chỉ set is_active = false"
  rationale: "Foreign key integrity và audit trail"  # ← nếu bỏ
```

Mất: AI (hoặc developer mới) không biết *tại sao* có rule này. Dễ "optimize" bằng cách thêm `ON DELETE CASCADE` vào FK, phá vỡ audit trail.

**`depends_on`**

```yaml
- id: BR-T03
  rule: "Todo trong list đã archive không được đổi status"
  depends_on: BR-L01    # ← BR-L01: list archive không thêm todo mới
```

Mất: AI implement BR-T03 mà không kiểm tra xem list có archive không — vì không biết BR-T03 phụ thuộc vào trạng thái của list.

**`glossary`**

```yaml
glossary:
  "xóa":
    maps_to: "is_deleted = true"
    NOT: "SQL DELETE statement"
```

Mất: Khi prompt "xóa todo", AI có thể sinh `DELETE FROM todos WHERE id = ...` thay vì `UPDATE todos SET is_deleted = true`. Glossary là hướng dẫn ngôn ngữ bắt buộc cho AI.

**`computed_concepts`**

```yaml
computed_concepts:
  ActiveTodo:
    formula: "is_deleted = false AND status NOT IN ('completed', 'cancelled')"
```

Mất: AI tự định nghĩa "todo đang active" theo cách của nó — có thể quên check `is_deleted`, hoặc include `cancelled`. Computed concepts đảm bảo mọi nơi trong code dùng cùng một định nghĩa.

#### ⑤ Verification — kiểm tra syntax

Hiện tại không có schema validator riêng. Workflow kiểm tra:

```bash
# Sau mỗi lần sửa semantic_model.yaml:
python generate.py
git diff generated/
```

**Ba loại lỗi phổ biến:**

| Lỗi | Triệu chứng | Cách phát hiện |
|-----|------------|----------------|
| Thiếu field bắt buộc (`source_table`) | Generator crash: `KeyError: 'source_table'` | Thấy ngay khi chạy |
| Gõ sai tên field (`buisness_rules`) | Generator chạy thành công nhưng thiếu BR comment trong Pydantic | `git diff generated/` — class thiếu docstring |
| `depends_on` trỏ ID không tồn tại | Generator không validate cross-reference → silent | Code review: services/ thiếu guard condition |

> **Known limitation:** Generator không có built-in schema validation. `git diff generated/` là vòng feedback chính.

#### ⑥ Mở rộng và tùy biến

**Thêm entity mới:**
```yaml
entities:
  Tag:              # ← thêm block mới
    source_table: tags
    ...
```
Chạy `python generate.py` → sinh column mới, class Pydantic, dbt test.

**Thêm attribute vào entity có sẵn:**
```yaml
entities:
  Todo:
    attributes:
      priority: ...     # đã có
      estimated_hours:  # ← thêm mới
        type: integer
        nullable: true
```
Chạy `python generate.py` → generated/ cập nhật. Vì DB đang có data, cần thêm migration thủ công:
```sql
ALTER TABLE todos ADD COLUMN estimated_hours INTEGER;
```

**Thêm business rule:**
```yaml
business_rules:
  - id: BR-T05      # ← ID tiếp theo theo thứ tự
    rule: "estimated_hours nếu có phải > 0"
    rationale: "0 giờ không có nghĩa gì"
```
Generator không đọc BR trực tiếp vào code. BR được enforce khi AI prompt lần sau nhận semantic model updated.

**Custom field không có trong AING spec:**
```yaml
attributes:
  color:
    type: string
    max_length: 7
    ui_hint: "#hex"     # ← field tùy biến, generator sẽ ignore
```
Generator ignore mọi field không trong mapping của nó — đây là tính năng, không phải bug. Dùng để note nội bộ mà không ảnh hưởng generated output.

---

### 2.2 Chạy `generate.py`

```bash
python generate.py
```

Output:
```
[OK] generated/ddl/schema.sql
[OK] generated/pydantic_models.py
[OK] dbt/models/schema.yml
```

**Quy tắc mapping quan trọng nhất:**

| YAML | SQL | Pydantic |
|------|-----|---------|
| `type: uuid` | `UUID NOT NULL` | `UUID` |
| `type: string, max_length: 255` | `VARCHAR(255) NOT NULL` | `str = Field(max_length=255)` |
| `type: enum, values: [a, b]` | `VARCHAR(50) CHECK (col IN ('a','b'))` | `Literal['a', 'b']` |
| `nullable: true` | *(bỏ NOT NULL)* | `Optional[...]` |
| `default: true` | `DEFAULT true` | `Field(default=True)` |
| `references: User.id` | `FOREIGN KEY REFERENCES users(id)` | *(không sinh trong Pydantic)* |

**Nguyên tắc quan trọng:** Nếu thấy cần sửa schema SQL hoặc Pydantic model — **quay lại sửa `semantic_model.yaml`, không sửa `generated/`**. File generated sẽ bị overwrite lần chạy sau.

---

### 2.3 AI Prompt → `app/`

**Template prompt (copy và điền):**

```
Implement [tên feature] theo spec tại spec/spec.md.

Đọc semantic/semantic_model.yaml trước — business rules có ID (BR-xxx),
enforce chúng trong services/ với comment trích dẫn ID.

Pydantic models import từ generated/pydantic_models.py, không viết lại.
Stack: FastAPI + psycopg2 + PostgreSQL. Không dùng ORM.
generated/ và dbt/models/schema.yml — KHÔNG sửa tay, chạy generate.py.
```

**3 nguyên tắc AI phải tuân theo (kiểm tra sau khi nhận code):**

1. `routers/` chỉ parse HTTP → gọi service → trả response. Không chứa business logic.
2. `services/` enforce business rules với comment trích dẫn ID: `# BR-T01: completed todo không được sửa title`
3. Raw SQL với psycopg2 — không dùng ORM.

**Cách review kết quả:**

Chỉ cần kiểm tra `services/` có đủ BR-xxx comment không:

```python
# services/todo_service.py

def update_todo(todo_id, data):
    todo = get_todo(todo_id)

    # BR-T01: completed todo không được sửa title
    if todo["status"] == "completed" and data.get("title"):
        raise HTTPException(400, "Cannot update completed todo")

    # BR-T03: todo trong archived list không đổi status
    if data.get("status"):
        lst = get_list(todo["list_id"])
        if lst["archived_at"] is not None:
            raise HTTPException(400, "List is archived")
    ...
```

Nếu thiếu comment BR-xxx → yêu cầu AI bổ sung trước khi merge.

---

### 2.4 `dbt test` — CI gate

```bash
cd dbt && dbt test
```

Output khi pass:
```
14:32:01  Finished running 18 tests in 0 hours 0 minutes and 2.34s.
14:32:01  Completed successfully
14:32:01  Done. PASS=18 WARN=0 ERROR=0 SKIP=0 TOTAL=18
```

`dbt test` kiểm tra data quality trực tiếp trên DB — độc lập với unit test. Chạy sau mỗi deploy và hàng đêm trong CI. Fail = alert, không deploy tiếp.

Chạy test cho một bảng cụ thể:
```bash
dbt test --select todos
dbt test --store-failures  # lưu failing rows vào DB để debug
```

---

## Phần 3 — Exercise: Thêm Entity `Tag`

**Scenario:** User muốn gắn tag cho todo (ví dụ: "urgent", "work", "personal"). Một todo có thể có nhiều tag. Thêm entity `Tag` vào hệ thống.

---

### Bước 1 — Viết semantic

Mở `semantic/semantic_model.yaml`, thêm entity `Tag` và bảng junction `TodoTag`:

```yaml
entities:
  # ... User, TodoList, Todo giữ nguyên ...

  Tag:
    description: "Nhãn phân loại có thể gắn vào todo"
    source_table: tags
    attributes:
      id:         { type: uuid,   nullable: false }
      created_by: { type: uuid,   nullable: false, references: User.id }
      name:       { type: string, nullable: false, max_length: 50, unique: true }
      color:
        type: string
        max_length: 7
        nullable: true
        description: "Hex color code, ví dụ: #FF5733"
    business_rules:
      - id: BR-TG01
        rule: "Tên tag unique toàn hệ thống, không phân biệt hoa thường"
        rationale: "Tránh duplicate tag 'urgent' và 'Urgent'"
      - id: BR-TG02
        rule: "Không hard-delete tag — chỉ set is_active = false nếu cần ẩn"
        rationale: "Audit trail và tránh mất FK reference từ todo_tags"
    tests:
      - not_null: [id, created_by, name]
      - unique: [name]

  TodoTag:
    description: "Bảng junction: mối quan hệ nhiều-nhiều giữa Todo và Tag"
    source_table: todo_tags
    attributes:
      todo_id: { type: uuid, nullable: false, references: Todo.id }
      tag_id:  { type: uuid, nullable: false, references: Tag.id }
    business_rules:
      - id: BR-TG03
        rule: "Không thể gắn tag vào todo đã completed"
        rationale: "completed todo là bằng chứng — không thay đổi classification sau khi xong"
        depends_on: BR-T01
    tests:
      - not_null: [todo_id, tag_id]
```

Thêm vào `relationships`:
```yaml
relationships:
  # ... relationships cũ ...
  TodoHasTags:
    from: Todo
    to: Tag
    type: many_to_many
    via: TodoTag
```

**Checklist trước khi qua bước 2:**
- [ ] Mỗi BR có `id`, `rule`, `rationale`
- [ ] ID tiếp theo theo thứ tự (`BR-G01`, không dùng lại ID cũ)
- [ ] `source_table` đặt tên snake_case, số nhiều
- [ ] `references` dùng format `EntityName.field`

---

### Bước 2 — Chạy generator và đọc diff

```bash
python generate.py
git diff generated/
```

Output mong đợi trong `generated/ddl/schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS tags (
    id UUID NOT NULL,
    created_by UUID NOT NULL,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7),
    CONSTRAINT pk_tags PRIMARY KEY (id),
    CONSTRAINT uq_tags_name UNIQUE (name),
    CONSTRAINT fk_tags_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS todo_tags (
    todo_id UUID NOT NULL,
    tag_id UUID NOT NULL,
    CONSTRAINT pk_todo_tags PRIMARY KEY (todo_id),   -- ⚠ xem lưu ý bên dưới
    CONSTRAINT fk_todo_tags_todo_id FOREIGN KEY (todo_id) REFERENCES todos(id),
    CONSTRAINT fk_todo_tags_tag_id FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

> ⚠ **Lưu ý:** Generator tự detect PK từ UUID column đầu tiên (`todo_id`). Với junction table, PK đúng là composite `(todo_id, tag_id)`. Đây là case generator chưa handle — cần sửa thủ công trong `schema.sql` SAU khi generate, hoặc fix `generate.py`. Đây là ví dụ về **ranh giới của generator**: khi logic quá đặc thù, human/developer cần can thiệp.

---

### Bước 3 — Viết migration

Vì DB đang có data từ bước trước, không re-run `schema.sql` từ đầu mà viết migration:

```sql
-- migrations/002_add_tags.sql
CREATE TABLE IF NOT EXISTS tags (
    id UUID NOT NULL,
    created_by UUID NOT NULL,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7),
    CONSTRAINT pk_tags PRIMARY KEY (id),
    CONSTRAINT uq_tags_name UNIQUE (name),
    CONSTRAINT fk_tags_created_by FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS todo_tags (
    todo_id UUID NOT NULL,
    tag_id  UUID NOT NULL,
    CONSTRAINT pk_todo_tags PRIMARY KEY (todo_id, tag_id),
    CONSTRAINT fk_todo_tags_todo FOREIGN KEY (todo_id) REFERENCES todos(id),
    CONSTRAINT fk_todo_tags_tag  FOREIGN KEY (tag_id)  REFERENCES tags(id)
);
```

Chạy:
```bash
psql -U postgres -d todo_app -f migrations/002_add_tags.sql
```

---

### Bước 4 — AI Prompt

Trước tiên, cập nhật `spec/spec.md` — thêm use cases cho Tag management (POST /tags, gắn tag vào todo, bỏ tag). Sau đó điền template prompt:

```
Implement Tag management theo spec tại spec/spec.md.

Đọc semantic/semantic_model.yaml trước — có 3 business rules mới:
BR-TG01, BR-TG02, BR-TG03. Enforce chúng trong services/tag_service.py
với comment trích dẫn ID.

Cần implement:
- POST /tags — tạo tag mới (BR-G01: unique không phân biệt hoa thường)
- POST /todos/{id}/tags/{tag_id} — gắn tag vào todo (BR-G03: không gắn vào completed todo)
- DELETE /todos/{id}/tags/{tag_id} — bỏ tag khỏi todo
- GET /todos/{id}/tags — list tags của todo

Pydantic models import từ generated/pydantic_models.py, không viết lại.
Stack: FastAPI + psycopg2 + PostgreSQL. Không dùng ORM.
```

**Sau khi nhận code, check:**

```python
# services/tag_service.py — phải có:

# BR-TG01: Tên tag unique toàn hệ thống, không phân biệt hoa thường
name_lower = name.lower()
existing = db.query("SELECT id FROM tags WHERE LOWER(name) = %s", [name_lower])
if existing:
    raise HTTPException(409, "Tag name already exists")

# BR-TG03: Không thể gắn tag vào todo đã completed
todo = get_todo(todo_id)
if todo["status"] == "completed":
    raise HTTPException(400, "Cannot tag a completed todo")
```

Nếu thiếu một trong hai comment → yêu cầu AI bổ sung.

---

### Bước 5 — Verify

```bash
# Unit + API tests
python -m pytest tests/ -v

# Data quality gate
cd dbt && dbt test
```

Cả hai pass → done.

---

### 3A — Lỗi syntax và missing field: hệ thống báo thế nào?

#### Tình huống 1: Gõ sai tên field cấp cao

```yaml
entities:
  Tag:
    buisness_rules:    # ← sai: business_rules
      - id: BR-G01
        rule: "..."
```

**Triệu chứng:** Generator chạy thành công, không crash. Nhưng `git diff generated/` cho thấy class `Tag` trong `pydantic_models.py` không có BR comment:

```python
# Trước (đúng):
class Tag(BaseModel):
    # BR-G01: Tên tag unique toàn hệ thống

# Sau (sai):
class Tag(BaseModel):   # ← không có comment
```

**Cách fix:** `git diff generated/` sau mỗi lần sửa YAML — nếu thấy mất đi thứ gì mình vừa thêm thì đọc lại YAML.

---

#### Tình huống 2: Thiếu `source_table`

```yaml
entities:
  Tag:
    description: "Nhãn phân loại"
    # source_table: tags   ← bị xóa mất
    attributes:
      ...
```

**Triệu chứng:** Generator crash ngay lập tức:

```
Traceback (most recent call last):
  File "generate.py", line 82, in generate_ddl
    table = entity["source_table"]
KeyError: 'source_table'
```

**Cách fix:** Đọc traceback, thêm lại `source_table` vào entity bị thiếu.

---

#### Tình huống 3: `depends_on` trỏ ID không tồn tại

```yaml
- id: BR-TG03
  rule: "Không thể gắn tag vào todo đã completed"
  depends_on: BR-T99   # ← ID không tồn tại
```

**Triệu chứng:** Generator chạy thành công, không có lỗi nào. AI nhận semantic model và có thể implement BR-G03 mà không biết về BR-T01 (completed todo không được sửa). Code sinh ra có thể thiếu guard condition.

**Cách phát hiện:** Chỉ phát hiện khi review `services/tag_service.py` — thấy thiếu check `todo["status"] == "completed"`.

**Đây là known limitation.** Generator không validate cross-reference giữa các BR ID.

---

### 3B — Thêm trường tùy biến vào Tag entity

**Scenario:** Muốn thêm field `icon` phục vụ UI (emoji hoặc icon name), nhưng chưa chắc có đưa vào DB hay không.

**Cách 1 — Thêm vào `attributes` như bình thường:**

```yaml
Tag:
  attributes:
    icon:
      type: string
      max_length: 50
      nullable: true
      description: "Emoji hoặc icon name, ví dụ: 🔥 hoặc 'fire'"
```

Generator sinh:
- Column `icon VARCHAR(50)` trong `schema.sql`
- Field `icon: Optional[str] = Field(default=None, max_length=50)` trong Pydantic

Dùng khi `icon` là data thực sự cần persist trong DB.

**Cách 2 — Field metadata nội bộ, không sinh code:**

```yaml
Tag:
  attributes:
    name:
      type: string
      max_length: 50
      nullable: false
      ui_hint: "Hiển thị dưới dạng badge màu"   # ← field tùy biến
      placeholder_example: "urgent"               # ← field tùy biến
```

Generator ignore hoàn toàn `ui_hint` và `placeholder_example` vì chúng không có trong mapping của generator. Không lỗi, không warning. Dùng để note cho AI hoặc developer đọc mà không ảnh hưởng DB schema.

**Quy tắc chọn:**
- Cần lưu vào DB → cách 1
- Chỉ cần note/context cho AI hoặc team → cách 2

---

### 3C — Re-enforce: đảm bảo trường phải tồn tại

**Kịch bản:** Muốn đảm bảo mọi `Tag` phải có `created_by` — không được phép null trong DB.

Thêm vào `tests`:

```yaml
Tag:
  tests:
    - not_null: [id, created_by, name]   # ← đảm bảo created_by trong danh sách
```

Generator sinh dbt test:
```yaml
# dbt/models/schema.yml (generated)
- name: created_by
  tests:
    - not_null
    - relationships:
        to: source('todo_app', 'users')
        field: id
```

Chạy `dbt test` — nếu có row nào trong `tags` mà `created_by IS NULL` thì fail. Đây là cơ chế enforce duy nhất hiện tại.

---

**Kịch bản: Trường thừa trong YAML**

```yaml
Tag:
  attributes:
    name: { type: string, max_length: 50, nullable: false }
    DEPRECATED_slug: { type: string, nullable: true }   # ← field cũ, quên xóa
```

Generator sinh column `DEPRECATED_slug` trong `schema.sql` — không có lỗi, không warning.

**Workaround:** Chạy `python generate.py && git diff generated/` trước mỗi commit. Nếu thấy column không mong muốn xuất hiện trong diff → xóa khỏi YAML.

---

## Checklist Quick Reference

Mỗi lần thêm domain mới hoặc sửa semantic:

```
[ ] semantic_model.yaml có đủ: version, domain, entities, business_rules, tests
[ ] Mỗi BR có: id (BR-Xxx), rule, rationale
[ ] Mỗi entity có: source_table, ít nhất 1 test not_null cho id
[ ] python generate.py → không crash
[ ] git diff generated/ → output đúng như expect
[ ] Viết migration nếu DB đang có data
[ ] AI prompt có nhắc đến BR cần enforce
[ ] Review services/: đủ # BR-xxx comment
[ ] pytest tests/ -v → PASSED
[ ] dbt test → PASS
```
