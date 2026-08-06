# CP0 — Clean schema & rule contract (owner: cleaning/data-model)

Chốt tại checkpoint 0. Đây là contract dùng chung cho cleaning, index, test set,
quality — không đổi field/tên cột sau khi các phần khác đã bắt đầu code theo.

Nguồn: `src/ingestion/clean_schema.py` (code là nguồn sự thật, file này là tóm tắt
để bàn giao). Validation runner: `script/validate_clean.py` (chạy được từ CP1).

## 1. Clean schema (`CLEAN_COLUMNS`)

| Cột | Kiểu | Ghi chú |
| --- | --- | --- |
| `paper_id` | str | DOI, đã bỏ prefix `https://doi.org/` / `doi:`, lowercase. Stable ID xuyên suốt raw → clean → index → test set. |
| `title` | str | Đã strip tag/entity, whitespace chuẩn hóa. |
| `summary` | str | Abstract đã bỏ nhãn "Abstract:", strip tag, cap 2000 ký tự. |
| `authors` | list[str] | Trim, bỏ rỗng, de-dupe không phân biệt hoa/thường, tối đa 25. |
| `categories` | list[str] | Cùng rule như authors, không giới hạn số lượng. |
| `primary_category` | str | `categories[0]` nếu có, else `"uncategorized"`. |
| `published` | str | ISO `YYYY-MM-DD`. |
| `updated` | str | ISO `YYYY-MM-DD`. |
| `abs_url`, `pdf_url`, `comment` | str | Có thể rỗng (`""`), không được NaN. |
| `authors_joined` | str | `", ".join(authors)`. |
| `categories_joined` | str | `", ".join(categories)`. |
| `summary_chars` | int | `len(summary)`. |
| `age_days` | int | Xem mục 3. |
| `text_for_embedding` | str | Xem mục 2. |

`REQUIRED_NON_EMPTY`: `paper_id`, `title`, `summary`, `published`,
`text_for_embedding` — không được rỗng/NaN trong output. Không có cột nào khác
được phép NaN (xem check `no_nulls`).

## 2. Rule null / date / duplicate / authors / categories

Một raw record bị loại (không được ghi vào clean) nếu rơi vào 1 trong các lý do
sau (`DROP_REASONS`, mỗi lý do đếm riêng để `raw_count == clean_count +
sum(drop_counts)`):

- `missing_paper_id` — không có DOI sau normalize.
- `missing_title` / `short_title` (< 10 ký tự).
- `missing_summary` / `short_summary` (< 40 ký tự abstract sau khi strip tag).
- `missing_published` / `unparsable_published` — không parse được ngày (hỗ trợ
  `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY-MM`, `YYYY`, ISO datetime).
- `duplicate_paper_id` — trùng `paper_id` sau normalize; giữ bản `updated` mới
  nhất, hoà thì giữ bản `summary` dài hơn (không giữ bản đầu tiên gặp).

Authors/categories: normalize từng phần tử (strip tag, whitespace), bỏ chuỗi
rỗng, de-dupe theo lowercase, KHÔNG drop cả record nếu authors/categories rỗng
— chỉ cảnh báo (`authors_present` check là `warn`, không phải `fail`), vì
Crossref nhiều record thiếu author field nhưng vẫn dùng được cho retrieval.

## 3. `age_days` và `text_for_embedding`

`age_days = max(0, run_date.date() - published_date).days`, tính từ `published`
đã parse — không fallback về ngày hiện tại nếu thiếu (record đó bị drop ở bước
`missing_published`/`unparsable_published` trước khi tới bước này).

`text_for_embedding` build từ template cố định:

```text
Title: {title}
Authors: {authors_joined or "unknown"}
Categories: {categories_joined or "uncategorized"}
Published: {published}
Summary: {summary}
```

Nhúng metadata vào text có chủ đích: test set có câu hỏi về author/date/category,
nên các token đó phải nằm trong nội dung được embed thì retrieval mới match
được. Field label giữ cố định để so sánh baseline vs corrupted text theo dòng.

## 4. Validation raw → clean

Chạy sau khi `cleaning.py` ghi xong `data/clean/`:

```bash
uv run python script/validate_clean.py
```

Trước CP1 (chưa có clean artifact) script tự `SKIP` với exit code 0, không
block CP0. Từ CP1 trở đi, script check: đủ cột đúng thứ tự, không NaN,
`paper_id` unique, kiểu list/int đúng, ngày ISO, `summary_chars`/`authors_joined`/
`categories_joined`/`age_days`/`text_for_embedding` đều tái tạo được từ chính
dữ liệu trong dòng (không lệch), `primary_category` nằm trong `categories`,
freshness so với `freshness_threshold_days`, và đối chiếu
`raw_count == clean_count + drop_log` nếu có raw snapshot + drop log.

Options: `--clean-csv/--clean-json` để check bản corrupted/repaired,
`--drop-log` nếu cleaning.py ghi log ở path khác quy ước
`data/quality/clean_drop_log.json`.

## 5. Việc cần làm ở CP1 (người implement `cleaning.py`)

- Dùng thẳng helper trong `clean_schema.py` (đừng viết lại rule):
  `normalize_paper_id/title/summary/authors/categories`, `parse_date`,
  `format_date`, `compute_age_days`, `build_text_for_embedding`, `drop_reason`,
  `dedupe_records`, `empty_drop_log`.
- Ghi `drop_log` (dict đếm theo `DROP_REASONS`) ra
  `data/quality/clean_drop_log.json` để `validate_clean.py` đối chiếu count.
- Output đúng thứ tự cột `CLEAN_COLUMNS`, không thêm/bớt cột khi chưa cập nhật
  contract này.
