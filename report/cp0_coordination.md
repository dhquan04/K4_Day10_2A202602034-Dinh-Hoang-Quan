# CP0 — Điều phối, ownership và Definition of Done

**Điều phối:** Thành viên 1  
**Thời điểm chốt:** 2026-08-06  
**Nhánh tích hợp hiện tại:** `main` (không tạo nhánh mới trong CP0). Mọi thay đổi phải được rà soát trước khi tích hợp vào nhánh này.

## Môi trường chạy thống nhất

- Python runner đã kiểm chứng: `.\\.venv\\Scripts\\python.exe`.
- `uv` hiện không có trong `PATH`; không dùng `uv run ...` làm điều kiện nghiệm thu cho đến khi nhóm cài và thống nhất lại công cụ này.
- `.env` được git-ignore. Không đưa API key hoặc giá trị `.env` vào source, artifact hay báo cáo.

## Ownership và artifact bàn giao

| Thành viên | Ownership CP0 | Input | Artifact/path bàn giao | Lệnh hoặc bằng chứng nghiệm thu | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| 1 | Điều phối, contract, DoD và handoff | Cập nhật từ tất cả owner | `report/checkpoint_0_handoff.md`, `report/cp0_coordination.md` | Đối chiếu artifact với bảng này và chạy acceptance checks | Đang điều phối |
| 2 | Raw ingestion Crossref | Settings + Crossref payload | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `src/ingestion/crossref.py` | `& .\\.venv\\Scripts\\python.exe -m ingestion.crossref` | Đạt: 24 records, 24 ID unique |
| 3 | Clean schema/rules/validation | Raw records | `report/cp0_clean_contract.md`, `src/ingestion/clean_schema.py`, `script/validate_clean.py` | `& .\\.venv\\Scripts\\python.exe script\\validate_clean.py` | Chưa đạt: `text_for_embedding_matches_template` fail |
| 4 | Index, embedding và agent contract | Clean schema | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/retrieval/agent.py`, `report/role4_checkpoint_0_1.md` | Review input/output, model, collection, metadata và smoke-test plan | Đạt ở phạm vi thiết kế CP0 |
| 5 | Evaluation/report evidence design | Clean schema + index contract | `src/evaluation/testset.py` và thiết kế artifact tại `data/eval/`, `data/quality/` | Kiểm tra đủ question type/ground truth/evidence signals | Chưa đạt: test-set builder vẫn TODO |

## Acceptance checks của Thành viên 1

Chạy tại thư mục gốc repository:

```powershell
& .\.venv\Scripts\python.exe -m ingestion.crossref
& .\.venv\Scripts\python.exe script\validate_clean.py
```

Kết quả chốt ngày 2026-08-06:

- Raw lineage: **PASS** — 24 records, 24 `paper_id` unique; tập `paper_id` raw và clean trùng nhau.
- Clean validation: **FAIL** — 24/24 dòng không khớp template `text_for_embedding`; không được chuyển trạng thái CP0 sang hoàn tất cho đến khi lỗi này được sửa và lệnh trả về PASS.
- Evaluation contract: **BLOCKED** — chưa có implementation/artifact test set để nghiệm thu 4 loại câu hỏi (`summary`, `authors`, `date`, `categories`) và ground truth document IDs.

## Definition of Done CP0

- [x] Luồng raw → clean → index → evaluate → report, artifact path và điều kiện handoff được công bố.
- [x] Raw response và raw records tồn tại; có `paper_id` ổn định để bàn giao.
- [x] Raw ingestion có parse, lưu snapshot và retry/backoff cho 429/503.
- [x] Clean contract, metadata index, embedding model và collection names đã chốt.
- [ ] Clean validation PASS, gồm `text_for_embedding` tái tạo đúng template.
- [ ] Test-set/evidence contract có artifact hoặc implementation có thể nghiệm thu; bao phủ summary/authors/date/categories.
- [ ] Thành viên 1 chạy lại hai acceptance checks sau bàn giao và cập nhật trạng thái cuối cùng.

**Trạng thái CP0 hiện tại: CHƯA HOÀN TẤT.** Chỉ Thành viên 1 được đánh dấu hoàn tất CP0 sau khi mọi ô DoD còn lại được nghiệm thu PASS.
