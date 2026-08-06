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
| Clean contract | `src/ingestion/cleaning.py:build_clean_dataframe()` | raw records | `data/clean/papers_clean.{csv,json}` | Hoàn thành |
| Controlled corruption | `src/ingestion/corruption.py:corrupt_clean_dataframe()` | baseline DataFrame/config | corrupted data + `data/results/corruption_log.json` | Hoàn thành |
| Repaired clean | `cleaning.py:build_clean_dataframe()` | raw snapshot | `data/clean/papers_clean_repaired.{csv,json}` | Hoàn thành |
| Schema validation | `script/validate_clean.py` | repaired CSV/JSON | strict validation PASS | Hoàn thành |

Tôi sở hữu clean data và corruption/repair artifact, không tự thay đổi collection hoặc evaluation metric.

### Nhiệm vụ theo checkpoint CP1–CP6

| Checkpoint | Nhiệm vụ thực hiện | Kết quả/bằng chứng |
|---|---|---|
| CP1 | Chốt clean-data contract và derived fields dùng downstream. | Schema clean, `text_for_embedding`. |
| CP2 | Kiểm tra clean artifact đáp ứng input index/evaluate. | `data/clean/papers_clean.{csv,json}` hợp lệ. |
| CP3 | Hỗ trợ baseline run; giữ clean contract không đổi. | Baseline clean 24 rows. |
| CP4 | Chọn corruption có chủ đích, record và tham số theo seed. | Scenario plan/seed 42. |
| CP5 | Tạo `corrupt_clean_dataframe`, log ID/type/params/count và xác minh corrupted dataset. | `corruption_log.json`, corrupted artifacts. |
| CP6 | Chạy cleaning lại từ raw, không sửa tay; kiểm tra schema/count/quality và demo ba state. | Repaired artifacts, `validate_clean.py` PASS. |

Chi tiết thực hiện: CP1 xác định cột bắt buộc, normalisation và derived fields (`summary_chars`, `age_days`, `text_for_embedding`); CP2 tạo/kiểm tra clean CSV/JSON cho downstream; CP3 xác nhận baseline clean 24 rows trước khi freeze. CP4 chọn sáu loại corruption, record và severity có chủ đích. CP5 triển khai từng mutation bằng seed 42, log ID/type/parameters/before-after count và kiểm tra artifact phản ánh đúng log. CP6 không vá dữ liệu lỗi: build lại từ raw, chạy strict schema/uniqueness/content validation, bàn giao repaired artifacts để index/evaluation và demo clean–corrupted–repaired.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Derived-field contract | Retrieval | `text_for_embedding` hợp lệ |
| Corruption log | Observability | event metadata để liên kết signal |
| Demo clean states | Lead | clean–corrupted–repaired artifacts |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Tạo corruption | `data/results/corruption_log.json` | 12 deterministic events, seed 42 | log ID/type/parameters |
| Lưu state riêng | `data/clean/papers_clean_corrupted.{csv,json}` | baseline không bị overwrite | artifact paths khác nhau |
| Repair | `data/clean/papers_clean_repaired.{csv,json}` | 24 rows strict-clean | `script/validate_clean.py` PASS |

## 4. Giải thích phần kỹ thuật đã thực hiện

`corrupt_clean_dataframe()` nhận baseline clean DataFrame và config/seed 42; output là corrupted copy cùng event log. Sáu mutation gồm drop latest, blank summary, noise, truncate title, stale date, duplicate; derived fields như `summary_chars`, `age_days`, `text_for_embedding` được cập nhật phù hợp. Repair nhận raw snapshot, chạy lại cleaning thay vì sửa corrupted rows. Contract: baseline/repaired có ID unique và field clean hợp lệ; corrupted chỉ là state đo lường intentional dirty data.

## 5. Một quyết định kỹ thuật quan trọng

- **Quyết định:** dùng seed 42 và log before/after cho từng event.
- **Lý do:** corruption phải tái lập và truy nguyên được, không phải lỗi ngẫu nhiên.
- **Bằng chứng:** 12 event có ID/type/parameters; repaired strict validation PASS.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `papers-corrupted` build fail vì `validate_index_input()` (`src/retrieval/index.py`, thuộc phạm vi Role 4) reject duplicate `paper_id` và blank summary.
- **Nguyên nhân:** corrupted data do tôi tạo ra cố ý vi phạm clean contract (đúng mục đích CP5), nên strict validation cho baseline không phù hợp để build state này.
- **Xử lý:** tôi báo lỗi kèm evidence (`corruption_log.json`) cho Role 4; Role 4 thêm cờ `allow_intentional_corruption` trong `index.py` để cho phép build `papers-corrupted` mà không nới lỏng validation cho baseline/repaired. Phần của tôi chỉ dừng ở việc tách state corrupted sang path/artifact riêng (`papers_clean_corrupted.{csv,json}`) và giữ `corrupt_clean_dataframe()`/repair vẫn strict.
- **Xác minh:** corrupted build được (không ghi đè baseline), repaired 24/24 rows và ID unique qua `validate_clean.py` PASS.

## 7. Hiểu biết về luồng end-to-end

Raw được cleaning thành baseline; bản sao clean bị corrupt và ghi log; RAG index/evaluate nhánh corrupted; repair quay về raw và chạy lại cùng cleaning contract; RAG/evaluate nhánh repaired. Vì artifact tách biệt, comparison đo data quality thay vì lỗi ghi đè file.

## 8. Phân tích kết quả

Có 12 events, hai cho mỗi loại. Hai drop và hai duplicate giữ corrupted row count ở 24 nên count không đủ phản ánh lỗi; quality đo uniqueness/summary riêng. Metrics `1.00 → 0.75 → 1.00` (hit rate), `1.00 → 0.7616 → 1.00` (F1), `1.00 → 0.75 → 1.00` (judge accuracy), `5 → 4 → 5` (score); quality/freshness `True/True → False/False → True/True`; stale `0 → 2 → 0`. CP6 xác nhận 12/12 event IDs được rebuild từ raw.

## 9. Điều học được và hướng cải thiện

Tôi học được rằng “corruption có chủ đích” phải được thiết kế như một thí nghiệm: có seed, population mục tiêu, tham số, before/after count và artifact độc lập. Nếu chỉ sửa dữ liệu ngẫu nhiên hoặc không log, không thể tái lập lỗi và không thể nối impact về nguyên nhân cụ thể. Derived fields cũng là một phần của data contract; nếu chúng không được rebuild đúng, quality signal sẽ phản ánh lỗi của pipeline thay vì lỗi dữ liệu cần đo.

Một bài học khác là count không đủ để khẳng định dữ liệu tốt: hai records bị drop có thể được bù bằng hai duplicate rows, tổng vẫn là 24. Vì vậy validation phải kiểm tra uniqueness, null/length, date và embedding text, còn repair đúng nghĩa là chạy lại cleaning từ raw chứ không vá từng hàng corrupted.

Hướng cải thiện: thêm corruption cho author/DOI/category/ngôn ngữ; dùng severity levels để vẽ đường cong quality–retrieval; thêm property-based tests cho `summary_chars`, `age_days`, `text_for_embedding`; và lưu profile before/after theo từng cột. Thành công là mỗi event đều tái lập bằng seed, vi phạm signal dự kiến và repaired artifact quay lại strict contract.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** **Đỗ Việt Tùng**  
**Ngày xác nhận:** **2026-08-06**
