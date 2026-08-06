# Báo cáo Role 5 — Evaluation & Observability

**Nhóm:** ChickenFarmer  
**Vai trò:** Evaluation & observability owner (`eval|observe`)  
**Phạm vi:** `src/evaluation/testset.py`, `src/observability/quality.py`, `data/eval/`, `data/quality/`  
**Checkpoint:** CP0, CP1 và CP2

## Checkpoint 0 — Contract evaluation & observability

### Mục tiêu phần việc

Đọc format test set / answer / metric, thiết kế câu hỏi từ dữ liệu thật, và chốt khung evidence cho quality/freshness trước khi chạy baseline end-to-end.

### Input đã đọc

| Module | Contract quan trọng |
| --- | --- |
| `src/evaluation/testset.py` | Mỗi sample: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| `src/evaluation/metrics.py` | Metrics: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`; answers lưu từng câu với `retrieval_hit`, `token_f1`, `judge` |
| `src/retrieval/qa.py` | Câu hỏi factual dùng pattern: summary → first sentence; authors → `authors_joined`; date → `published`; categories → `categories_joined` |
| `src/core/config.py` | Artifact paths: `data/eval/test_set.json`, `data/quality/`, `data/quality/freshness_report.json`, `freshness_threshold_days=180` |

### Thiết kế evaluation set

| `question_type` | Mẫu câu hỏi | `ground_truth` | `ground_truth_doc_ids` |
| --- | --- | --- | --- |
| `summary` | What is the main contribution of the paper titled '{title}'? | Câu đầu của `summary` | `[paper_id]` |
| `authors` | Who authored the paper titled '{title}'? | `authors_joined` (fallback `unknown`) | `[paper_id]` |
| `date` | When was the paper titled '{title}' published? | `published` (ISO `YYYY-MM-DD`) | `[paper_id]` |
| `categories` | What categories apply to the paper titled '{title}'? | `categories_joined` hoặc `primary_category` | `[paper_id]` |

Quy tắc:

- Chỉ chọn paper từ cleaned dataframe (`title`, `summary`, `published`, `paper_id` đều hợp lệ).
- `ground_truth_doc_ids` luôn lấy từ `paper_id` clean — không tự bịa ID.
- Title trong câu hỏi giữ nguyên để `qa.py` có thể exact lookup theo title.
- Test set cố định tại `data/eval/test_set.json`, dùng lại cho baseline / corrupted / repaired.

### Quality & freshness signals

| Signal | Dimension | Ngưỡng/kỳ vọng | Artifact evidence |
| --- | --- | --- | --- |
| `row_count` | Completeness | > 0 | `{report_name}.json` |
| `paper_id_not_null` | Validity | 0 null/blank | `{report_name}.json` |
| `paper_id_unique` | Uniqueness | 0 duplicate | `{report_name}.json` |
| `title_not_null` | Completeness | 0 missing | `{report_name}.json` |
| `summary_not_null` | Completeness | 0 missing | `{report_name}.json` |
| `summary_min_length` | Validity | 0 summary < 40 chars | `{report_name}.json` |
| `text_for_embedding_present` | Completeness | 0 missing | `{report_name}.json` |
| `age_days_present` | Freshness | 0 missing | `{report_name}.json` |
| `stale_rows` | Freshness | `age_days <= freshness_threshold_days` | `freshness_report.json` |
| `is_fresh` | Freshness | `stale_rows == 0` | `freshness_report.json` |

Freshness được tính từ `published` / `age_days` trong clean data — không giả định ngày hiện tại nếu thiếu `published`.

### Artifact bàn giao (Role 5)

| Artifact | Path | CP |
| --- | --- | --- |
| Evaluation set | `data/eval/test_set.json` | CP1 |
| Quality report baseline | `data/quality/baseline_quality.json` | CP1 |
| Freshness report | `data/quality/freshness_report.json` | CP1 |
| Contract doc | `report/role5_checkpoint_0_1.md` | CP0 |

### Phụ thuộc upstream (đã xác minh)

- Raw artifacts tồn tại: `data/raw/crossref_response.json`, `data/raw/crossref_records.json`
- `paper_id` ổn định theo contract trong `report/cp0_clean_contract.md`
- Clean artifacts từ role Cleaning: `data/clean/papers_clean.{csv,json}`, `data/quality/clean_drop_log.json`

### Kết luận CP0

Đã chốt schema test set, mapping câu hỏi → ground truth, danh sách quality/freshness signals và đường dẫn artifact để team dùng chung.

## Checkpoint 1 — Quality gates & draft test set

### Mục tiêu phần việc

Implement quality checks và freshness report; chọn paper sạch và ghi evaluation set draft từ cleaned dataframe.

### Implementation

| File | Chức năng |
| --- | --- |
| `src/observability/quality.py` | `run_data_quality_checks()`, `build_freshness_report()` |
| `src/evaluation/testset.py` | `build_test_set()` — 8 câu (2/paper type × 4 types) |

### Tiêu chí hoàn thành CP1

- [x] Clean CSV/JSON đọc được và có đủ cột contract
- [x] Quality checks: row count, unique ID, thiếu title/summary, duplicate
- [x] Freshness từ `published` / `age_days`
- [x] Test set draft với 4 `question_type`
- [x] Quality/freshness JSON ghi ra `data/quality/`
- [x] Không sửa module ngoài phạm vi Role 5

### Lệnh tái hiện phần Role 5

```bash
uv run python script/run_role5_cp1.py
```

Hoặc:

```bash
python script/run_role5_cp1.py
```

### Kết luận CP1

Role 5 đã implement observability checks và evaluation set builder. Các artifact baseline quality/freshness/test set sẵn sàng cho handoff sang index (CP2) và baseline evaluation (CP3).

## Checkpoint 2 — Test set cố định, audit index & khung report

### Mục tiêu phần việc

Khóa evaluation set trên clean + index, audit embedding manifest, đóng băng baseline quality/freshness signals, và chuẩn bị khuôn `phase1_report` (metrics để trống cho CP3).

### Việc đã làm (Role 5)

| # | Việc CP2 | Trạng thái | Evidence |
| --- | --- | --- | --- |
| 1 | `build_test_set` đủ `id` / `question_type` / `question` / `ground_truth` / `ground_truth_doc_ids` | Done | `src/evaluation/testset.py` |
| 2 | Question từ cleaned data; ID phải có trong index | Done | `build_test_set(..., indexed_paper_ids=...)` + `validate_test_set_against_index` |
| 3 | Lưu test set cố định và preview vài row | Done | `data/eval/test_set.json` (8 câu); `preview_test_set()` |
| 4 | Audit embedding manifest / collection / document count | Done | `audit_embedding_manifest()` → `data/quality/embedding_audit_baseline.json` |
| 5 | Freeze baseline quality/freshness signals | Done | `freeze_baseline_signals()` → `data/quality/baseline_signals.json` |
| 6 | Khuôn phase1 report (metrics fill ở CP3) | Done | `generate_phase1_report()` → `data/reports/phase1_report.md` |

### Kết quả audit hiện tại

- Embedding manifest: `papers-baseline`, 24 documents, khớp clean 24 rows, **passed**
- Quality: **passed**, Freshness: **is_fresh=true** (0 stale / threshold 180)
- Test set: 8 samples; mọi `ground_truth_doc_ids` có trong embedding manifest

### Phụ thuộc / blocker từ role khác

| Role | Cần gì | Trạng thái |
| --- | --- | --- |
| Cleaning | `data/clean/papers_clean.{csv,json}` | Có |
| RAG | `data/embeddings/papers_embeddings.json` | Có (manifest audit OK) |
| RAG | Chroma persist `data/chroma/` cho smoke search/lookup thật | **Thiếu / trống** — Role 5 chỉ audit được manifest JSON; cần Role RAG xác nhận collection `papers-baseline` load được |
| Lead | `phase1.py` gọi test set → evaluate → quality → report | **Chưa** (đúng lịch CP3) |

### Ngoài phạm vi Role 5 ở CP2

Không sửa: `phase1.py`, `corruption_flow.py`, `retrieval/*`, `cleaning.py`, `crossref.py`, `generate_corruption_report` (CP5/CP6).
