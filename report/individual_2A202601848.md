# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | **Hoàng Thanh Sơn** |
| MSSV | **2A202601848** |
| Khóa/Lớp | K4 |
| Tên nhóm | ChickenFarmer |
| Vai trò chính | Thành viên 2 — Raw source, lineage và recovery proof |
| Repository | `K4_Day10_Nhom-ChickenFarmer` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Source/lineage contract | `trace_paper_lineage()` | raw, clean, manifest | raw → clean → index proof | Hoàn thành |
| Raw recovery point | `restore_from_raw_snapshot()` | raw snapshot | repaired source input | Hoàn thành |
| Corruption lineage | `trace_corrupted_lineage()` | log, corrupted/repaired clean | affected/recovered ID proof | Hoàn thành |
| CP6 source review | `cp6_final_review.json` | raw/repaired artifacts | hash và field comparison | Hoàn thành |

Tôi sở hữu tính nguyên vẹn nguồn và traceability, không fetch dữ liệu mới trong CP5/CP6 để tránh làm lệch experiment.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Handoff raw cho cleaning | Cleaning | Repair có input tái lập |
| Đối chiếu event ID | Observability | Event → record evidence |
| Review secret | Lead | `.env` không được Git track |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Khóa snapshot | raw artifacts/hash | 24 raw records bất biến | CP6 raw hash |
| Trace corruption | role2 checkpoint evidence | mọi event có raw ancestor | log/lineage trace |
| Chứng minh repair | CP6 review | 12/12 affected IDs recovered | core fields khớp baseline |

## 4. Giải thích phần kỹ thuật đã thực hiện

Input là raw `PaperRecord`, corrupted/repaired clean và corruption log. Output là lineage trace, recovered-ID list và so sánh core fields. Contract dùng `paper_id`/DOI ổn định để một paper được nhận diện như nhau ở raw, clean và index. `restore_from_raw_snapshot()` chỉ đọc snapshot đã khóa; không dùng API upstream khi repair.

## 5. Một quyết định kỹ thuật quan trọng

- **Quyết định:** raw snapshot là source of truth duy nhất cho recovery.
- **Lý do:** fetch mới có thể thay count, metadata hoặc thời điểm dữ liệu, làm mất tính công bằng comparison.
- **Bằng chứng:** repaired có 24 rows, 12/12 IDs bị ảnh hưởng trở lại và core fields khớp baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Rủi ro:** repair bằng dữ liệu refresh có thể tạo “recovery” giả.
- **Nguyên nhân:** nguồn bên ngoài có thể thay đổi giữa các checkpoint.
- **Xử lý:** giữ snapshot/hash, trace event ID về raw và cấm fetch mới.
- **Xác minh:** CP6 raw hash PASS, repaired lineage PASS.

## 7. Hiểu biết về luồng end-to-end

Raw là provenance root; cleaning sinh clean artifact; retrieval chỉ index clean; evaluator dùng frozen set; corruption tạo nhánh derived; repair quay trở lại raw rồi chạy lại clean/index/evaluation. Vì source không đổi, metric delta phản ánh chất lượng dữ liệu chứ không phải upstream drift.

## 8. Phân tích kết quả

12 events (mỗi loại 2: drop latest, blank summary, noise, truncate title, stale date, duplicate) được trace về raw. Metrics đi từ hit rate `1.00 → 0.75 → 1.00`, token F1 `1.00 → 0.7616 → 1.00`, judge accuracy `1.00 → 0.75 → 1.00`, score `5 → 4 → 5`. Quality/freshness cũng hồi `True/True → False/False → True/True`, stale rows `0 → 2 → 0`. Bằng chứng theo record: 12/12 affected IDs được recovery.

## 9. Điều học được và hướng cải thiện

Lineage phải là contract dữ liệu thay vì ghi chú thủ công. Có thể lưu version/timestamp/hash ở mọi handoff và tự động test raw ancestor/repaired equivalent cho từng event.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Hoàng Thanh Sơn**  
**Ngày xác nhận:** **2026-08-06**
