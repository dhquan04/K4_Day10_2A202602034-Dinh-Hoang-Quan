# CP2 — Khóa contract và điều phối handoff

**Điều phối:** Thành viên 1  
**Checkpoint:** CP2 — Test set, RAG index & agent smoke test  
**Ngày kiểm tra:** 2026-08-06

## Contract đã khóa

- Nguồn clean chuẩn: `data/clean/papers_clean.json` và `data/clean/papers_clean.csv`.
- Schema: 16 trường theo `src/ingestion/clean_schema.py`; các trường bắt buộc cho index gồm `paper_id`, `title`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`.
- `paper_id` là DOI đã chuẩn hóa; phải duy nhất xuyên suốt raw → clean → metadata index → `ground_truth_doc_ids`.
- Không refresh Crossref/source trong CP2 để baseline không thay đổi.

## Kết quả kiểm tra handoff

| Hạng mục | Kết quả | Bằng chứng |
| --- | --- | --- |
| Clean contract | PASS — 24 rows, không thiếu `text_for_embedding`, không trùng `paper_id` | `script/validate_clean.py` |
| Reconciliation raw → clean | PASS — raw 24, clean 24, dropped 0 | `data/raw/crossref_records.json`, `data/quality/clean_drop_log.json` |
| Test set | PASS — 8 câu hỏi; mọi `ground_truth_doc_ids` đều tồn tại trong clean data | `data/eval/test_set.json` |
| Baseline embedding manifest | PASS — collection `papers-baseline`, 24 documents | `data/embeddings/papers_embeddings.json` |

## Handoff

1. Evaluation/observability dùng nguyên `data/eval/test_set.json`; không thay câu hỏi, ground truth hay document ID trong các phase so sánh.
2. RAG dùng collection `papers-baseline`; corrupted và repaired phải dùng các tên/manifest riêng theo `src/core/config.py`.
3. Nếu index hoặc test set thiếu trường, trả lại clean owner để sửa contract/data rồi tạo lại artifact — không vá kết quả evaluation thủ công.

## Blocker trước end-to-end

`script/run_role4_cp2.py` đã khởi tạo được embedding model nhưng chưa hoàn tất smoke-test trong cửa sổ kiểm tra 60 giây. Cần chạy lại entrypoint này đến khi xác nhận đủ: exact lookup theo ID/title, semantic search và agent có trace tool output. Không chuyển sang CP3 khi thiếu evidence đó.

