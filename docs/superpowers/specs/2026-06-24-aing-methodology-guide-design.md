# Design: AING Methodology Guide

**Date:** 2026-06-24  
**Status:** Approved  
**Deliverable:** `docs/aing_methodology_guide.md`

---

## Mục Đích

Tài liệu hướng dẫn dành cho **developer nội bộ onboarding** — biết Python + FastAPI cơ bản, chưa biết AING. Đọc một lần, làm theo từng bước, kết thúc biết cách build app mới với AING semantic-first methodology.

**Ngôn ngữ:** Tiếng Việt.  
**Format:** Tutorial (không phải reference).

---

## Cấu Trúc 3 Phần

### Phần 1 — Pipeline & Ai Làm Gì (~5 phút đọc)

- Sơ đồ ASCII pipeline 4 bước: Human → Script → AI → CI
- Bảng "ai làm gì — file nào chạm được" (Human/Script/AI, ✅/❌)
- **Một quy tắc duy nhất cần nhớ:** Human chỉ review semantic model và spec — không bao giờ review code chi tiết trong `app/`

---

### Phần 2 — Walkthrough aing_todo_demo (~20 phút đọc)

#### 2.1 Viết `semantic_model.yaml`

6 sub-section:

**① Mục tiêu của file**  
Ngôn ngữ chung giữa business, human reviewer và AI. Test: "Người mới đọc file này có hiểu domain không?"

**② Cấu trúc: bắt buộc vs. tùy chọn**

| Block | Bắt buộc? | Mục đích |
|-------|-----------|---------|
| `version`, `domain`, `description` | ✅ | Header định danh |
| `entities` + `attributes` | ✅ | Data model |
| `business_rules` (có `id`) | ✅ | Trái tim của file |
| `tests` | ✅ | Sinh dbt test |
| `relationships` | Khuyến nghị | Giúp AI hiểu FK |
| `computed_concepts` | Tùy chọn | Định nghĩa filter/metric phức tạp |
| `glossary` | Tùy chọn | Ngăn AI dùng sai ngôn ngữ domain |

**③ Logic gì vào semantic — logic gì để ngoài**

Vào semantic:
- Constraint cấp dữ liệu: uniqueness, nullability, enum values
- Business rule phát biểu được thành câu văn độc lập với tech stack
- Invariant bất biến theo thời gian

Để ngoài (services/ hoặc spec):
- Logic phụ thuộc HTTP flow cụ thể
- Logic phụ thuộc runtime (completed_at = NOW())
- Authorization / pagination / sorting

Ranh giới kiểm tra: nếu rule có thể phát biểu mà không nhắc đến HTTP method, endpoint, hay framework → thuộc về semantic.

**④ Tại sao có từng trường**  
Giải thích lý do tồn tại bằng câu hỏi ngược: nếu bỏ đi thì mất gì?
- `id: BR-xxx` → traceability từ code về spec
- `rationale` → AI không "optimize" sai rule
- `depends_on` → AI biết dependency giữa các BR
- `glossary` → "xóa" ≠ DELETE, "hoàn thành" ≠ is_deleted=true
- `computed_concepts` → AI dùng cùng định nghĩa OverdueTodo/ActiveTodo

**⑤ Verification — kiểm tra syntax**  
- Chạy `python generate.py` ngay sau khi sửa
- `git diff generated/` để verify output đúng như expect
- Known limitation: không có schema validator riêng — silent bug khi gõ sai tên field

**⑥ Mở rộng và tùy biến**  
- Thêm entity: thêm block, chạy generator
- Thêm attribute: thêm vào attributes, viết migration thủ công
- Thêm BR: đặt ID tiếp theo, generator không đọc BR — AI prompt mới enforce
- Custom field không có trong AING spec: generator ignore (dùng để note nội bộ)

#### 2.2 Chạy `generate.py`
- Output 3 files, quy tắc mapping quan trọng nhất
- Nếu cần sửa schema → quay lại YAML, không sửa generated/

#### 2.3 AI Prompt → `app/`
- Template prompt
- 3 nguyên tắc AI phải tuân theo
- Cách review: check BR-xxx comment trong services/

#### 2.4 `dbt test`
- Lệnh chạy, output mong đợi, ý nghĩa CI gate

---

### Phần 3 — Exercise: Thêm entity `Tag` (~15 phút)

Scenario: Thêm Tag (gắn label cho todo).

**Bước 1-5:** Viết semantic → generate → migration → AI prompt → verify

**3A — Lỗi syntax và missing field**

3 tình huống thực tế:
1. Gõ sai tên field cấp cao → generator chạy, output thiếu BR comment → phát hiện qua `git diff`
2. Thiếu `source_table` → crash `KeyError` → rõ ràng, dễ fix
3. `depends_on` trỏ ID không tồn tại → silent bug, AI implement thiếu guard → phát hiện lúc review services/

**3B — Thêm trường tùy biến**

2 cách:
1. Thêm vào `attributes` → generator sinh column + Pydantic (đúng khi cần persist)
2. Thêm field metadata không trong AING spec → generator ignore (dùng để note nội bộ)

**3C — Re-enforce và trường thừa**

- Enforce not_null: thêm vào `tests.not_null` → dbt test fail nếu vi phạm
- Trường thừa: generator bỏ qua silent → workaround: `python generate.py && git diff generated/` trước mỗi commit

---

## Out of Scope

- Hướng dẫn setup PostgreSQL / dbt profiles
- CI/CD pipeline config
- Authentication / JWT
