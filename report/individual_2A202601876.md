# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | **Đỗ Việt Tùng** |
| MSSV | **2A202601876** |
| Khóa/Lớp | K4 |
| Tên nhóm | ChickenFarmer |
| Vai trò chính | Thành viên 3 — Cleaning contract và controlled corruption |
| Repository | `K4_Day10_Nhom-ChickenFarmer` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Clean contract | cleaning pipeline | raw records | clean CSV/JSON | Hoàn thành |
| Controlled corruption | `corrupt_clean_dataframe()` | baseline DataFrame/config | corrupted data + log | Hoàn thành |
| Repaired clean | `build_clean_dataframe()` | raw snapshot | repaired CSV/JSON | Hoàn thành |
| Schema validation | `script/validate_clean.py` | repaired artifacts | PASS result | Hoàn thành |

Tôi sở hữu clean data và corruption/repair artifact, không tự thay đổi collection hoặc evaluation metric.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Derived-field contract | Retrieval | `text_for_embedding` hợp lệ |
| Corruption log | Observability | event metadata để liên kết signal |
| Demo clean states | Lead | clean–corrupted–repaired artifacts |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Tạo corruption | `corruption_log.json` | 12 deterministic events, seed 42 | log ID/type/parameters |
| Lưu state riêng | `papers_clean_corrupted.*` | baseline không bị overwrite | artifact paths khác nhau |
| Repair | `papers_clean_repaired.*` | 24 rows strict-clean | `validate_clean.py` PASS |

## 4. Giải thích phần kỹ thuật đã thực hiện

`corrupt_clean_dataframe()` nhận baseline clean DataFrame và config/seed 42; output là corrupted copy cùng event log. Sáu mutation gồm drop latest, blank summary, noise, truncate title, stale date, duplicate; derived fields như `summary_chars`, `age_days`, `text_for_embedding` được cập nhật phù hợp. Repair nhận raw snapshot, chạy lại cleaning thay vì sửa corrupted rows. Contract: baseline/repaired có ID unique và field clean hợp lệ; corrupted chỉ là state đo lường intentional dirty data.

## 5. Một quyết định kỹ thuật quan trọng

- **Quyết định:** dùng seed 42 và log before/after cho từng event.
- **Lý do:** corruption phải tái lập và truy nguyên được, không phải lỗi ngẫu nhiên.
- **Bằng chứng:** 12 event có ID/type/parameters; repaired strict validation PASS.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** duplicate và blank summary bị strict validation/index reject.
- **Nguyên nhân:** corrupted data cố ý vi phạm clean contract.
- **Xử lý:** tách state corrupted, chỉ nới index validation tại nhánh thí nghiệm; repaired vẫn strict.
- **Xác minh:** corrupted build được, repaired 24/24 rows và ID unique.

## 7. Hiểu biết về luồng end-to-end

Raw được cleaning thành baseline; bản sao clean bị corrupt và ghi log; RAG index/evaluate nhánh corrupted; repair quay về raw và chạy lại cùng cleaning contract; RAG/evaluate nhánh repaired. Vì artifact tách biệt, comparison đo data quality thay vì lỗi ghi đè file.

## 8. Phân tích kết quả

Có 12 events, hai cho mỗi loại. Hai drop và hai duplicate giữ corrupted row count ở 24 nên count không đủ phản ánh lỗi; quality đo uniqueness/summary riêng. Metrics `1.00 → 0.75 → 1.00` (hit rate), `1.00 → 0.7616 → 1.00` (F1), `1.00 → 0.75 → 1.00` (judge accuracy), `5 → 4 → 5` (score); quality/freshness `True/True → False/False → True/True`; stale `0 → 2 → 0`. CP6 xác nhận 12/12 event IDs được rebuild từ raw.

## 9. Điều học được và hướng cải thiện

Corruption cần state-specific contract, seed và log. Có thể thêm severity levels, corruption author/DOI/ngôn ngữ và property-based tests cho derived fields.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Đỗ Việt Tùng**  
**Ngày xác nhận:** **2026-08-06**
