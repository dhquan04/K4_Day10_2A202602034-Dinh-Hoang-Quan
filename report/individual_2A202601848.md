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
| Source/lineage contract | `src/ingestion/crossref.py:trace_paper_lineage()` | raw, clean, manifest | raw → clean → index proof | Hoàn thành |
| Raw recovery point | `crossref.py:restore_from_raw_snapshot()` | raw snapshot | repaired source input | Hoàn thành |
| Corruption lineage | `crossref.py:trace_corrupted_lineage()` | log, corrupted/repaired clean | affected/recovered ID proof | Hoàn thành |
| CP6 source review | `data/results/cp6_final_review.json` | raw/repaired artifacts | hash và field comparison | Hoàn thành |

Tôi sở hữu tính nguyên vẹn nguồn và traceability, không fetch dữ liệu mới trong CP5/CP6 để tránh làm lệch experiment.

### Nhiệm vụ theo checkpoint CP1–CP6

| Checkpoint | Nhiệm vụ thực hiện | Kết quả/bằng chứng |
|---|---|---|
| CP1 | Xác nhận source contract, raw schema và identity ban đầu của paper. | Raw `PaperRecord`/`paper_id` dùng nhất quán. |
| CP2 | Kiểm tra lineage raw → clean → index và raw/clean count. | `report/role2_checkpoint_3.md`. |
| CP3 | Đối chiếu raw snapshot, khóa nguyên tắc không fetch source mới. | Raw snapshot 24 records làm baseline source. |
| CP4 | Giữ raw source làm recovery point và chuẩn bị trace record có lineage. | Snapshot/hash raw. |
| CP5 | Xác nhận raw không mutate; trace record corrupted/drop về đúng raw record. | Role 2 checkpoint/lineage evidence. |
| CP6 | Reload raw snapshot; chứng minh record bị corrupt/drop được khôi phục và kiểm tra secret. | CP6 review: 12/12 affected IDs recovered. |

Chi tiết thực hiện: CP1 kiểm tra các trường nguồn, DOI/paper ID và quy tắc parse raw; CP2 đối chiếu ID/count giữa raw, clean và manifest để chứng minh provenance; CP3 giữ raw snapshot cố định sau baseline. CP4 chuẩn bị raw recovery point và chọn record có lineage rõ ràng. CP5 không fetch mới, đối chiếu corruption log với raw source, xác nhận raw không bị mutate. CP6 reload đúng snapshot, kiểm tra từng affected ID (kể cả drop) xuất hiện lại trong repaired dataset, đối chiếu core fields với baseline và cùng nhóm kiểm tra repository không lộ API key.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Handoff raw cho cleaning | Cleaning | Repair có input tái lập |
| Đối chiếu event ID | Observability | Event → record evidence |
| Review secret | Lead | `.env` không được Git track |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Khóa snapshot | `data/raw/` và CP6 hash | 24 raw records bất biến | `cp6_final_review.json` |
| Trace corruption | `report/role2_checkpoint_5.md` | mọi event có raw ancestor | log/lineage trace |
| Chứng minh repair | `data/results/cp6_final_review.json` | 12/12 affected IDs recovered | core fields khớp baseline |

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

Tôi học được rằng lineage không phải phần mô tả bổ sung ở cuối dự án mà là điều kiện để kết luận nguyên nhân. Nếu không giữ một raw snapshot bất biến, mọi thay đổi từ source bên ngoài có thể bị nhầm với tác động của corruption hoặc hiệu quả repair. Identity ổn định theo `paper_id`/DOI cũng quan trọng hơn count: count có thể bằng nhau trong corrupted state nhưng record cụ thể đã thay đổi.

Khi phối hợp end-to-end, raw cần bàn giao không chỉ file mà còn contract về schema, origin, thời điểm và hash. Nhờ đó cleaning có thể rebuild, retrieval có identity nhất quán, còn evaluation có thể chứng minh ground truth đã quay lại. Tôi cũng nhận ra “không fetch mới” là một quyết định thực nghiệm để bảo toàn khả năng tái lập, không đơn thuần là tối ưu chi phí.

Hướng cải thiện là lưu version/timestamp/hash cho mọi artifact raw và clean, tự động kiểm tra mỗi corruption event có raw ancestor và repaired equivalent, và bổ sung lineage graph có thể truy vấn. Khi corpus lớn hơn, nên dùng object storage versioning hoặc data catalog thay cho snapshot file đơn; tiêu chí thành công là tái tạo repaired state đúng hash mà không cần gọi lại nguồn ngoài.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Hoàng Thanh Sơn**  
**Ngày xác nhận:** **2026-08-06**
