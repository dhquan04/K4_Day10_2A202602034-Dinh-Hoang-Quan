# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | **Đinh Hoàng Quân** |
| MSSV | **2A202602034** |
| Khóa/Lớp | K4 |
| Tên nhóm | ChickenFarmer |
| Vai trò chính | Thành viên 1 — Pipeline integration, repair/comparison coordination |
| Repository | `K4_Day10_Nhom-ChickenFarmer` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Baseline gate | `report/cp4_member1_baseline_checklist.md` | raw/clean/test lock/metrics baseline | checklist, hash, blocker | Hoàn thành |
| Corruption–repair orchestration | `src/pipelines/corruption_flow.py` | clean/raw/test lock | corrupted/repaired artifacts theo state | Hoàn thành |
| Comparison report | `src/observability/reporting.py:generate_corruption_report()` | metrics, signals, corruption log | `data/reports/corruption_report.md` | Hoàn thành |
| Final review/demo | `script/run_cp6_review.py` | artifacts ba trạng thái | `data/results/cp6_final_review.json`, `data/reports/cp6_demo.md` | Hoàn thành |

Phạm vi của tôi là điều phối contract và handoff giữa raw, clean, retrieval, evaluation và observability; không nhận thay đổi raw source hoặc tự sửa tay dữ liệu repaired.

### Nhiệm vụ theo checkpoint CP1–CP6

| Checkpoint | Nhiệm vụ thực hiện | Kết quả/bằng chứng |
|---|---|---|
| CP1 | Điều phối chốt contract raw/clean và điều kiện bàn giao pipeline. | Handoff schema và phạm vi ownership rõ ràng. |
| CP2 | Rà dependency giữa clean data, index và evaluation; kiểm tra I/O handoff. | Pipeline baseline có các handoff xác định. |
| CP3 | Kiểm tra baseline run, metrics, manifest và artifact trước phase corruption. | Baseline metrics/manifest được dùng làm mốc comparison. |
| CP4 | Ghi baseline checklist, khóa hash và các blocker còn lại. | `report/cp4_member1_baseline_checklist.md`. |
| CP5 | Hoàn thiện flow corrupt → rebuild → evaluate → signals → repair → compare. | `corruption_flow.py`, corruption report. |
| CP6 | Freeze scope, review artifacts/no secret/no hard-code path, chỉ công bố recovery khi có số liệu. | `cp6_final_review.json`, `cp6_demo.md`. |

Chi tiết thực hiện: CP1 chốt các contract/handoff raw → clean → index → evaluation; CP2 rà input/output của từng handoff và điều kiện pipeline có thể tái chạy; CP3 kiểm tra baseline raw/clean/index/metrics trước khi cho chuyển phase. Tại CP4 tôi lập checklist gồm raw/clean/test lock/manifest/metrics, ghi fingerprint và blocker. CP5 tôi điều phối toàn bộ flow có guard không ghi đè baseline, gọi corruption, build index state riêng, evaluation, quality/freshness, repair từ raw và report so sánh. CP6 tôi chạy review tự động kiểm tra artifacts, collection separation, lineage/schema, portable path và secret scan, sau đó freeze scope và chuẩn bị demo.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Khóa collection baseline | Retrieval | Không ghi đè `papers-baseline` |
| Chốt điều kiện repair | Source/Cleaning | Repair luôn rebuild từ raw snapshot |
| Review số liệu recovery | Evaluation | Chỉ công bố khi metrics và signals cùng khớp |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Khóa baseline | `report/cp4_member1_baseline_checklist.md` | fingerprint và artifacts bắt buộc | baseline không thay đổi |
| Chạy full flow | `src/pipelines/corruption_flow.py` | corrupt → index → evaluate → repair → compare | `script/run_corruption_flow.py` PASS |
| Final review | `data/results/cp6_final_review.json` | PASS, 3 collection tách biệt | `script/run_cp6_review.py` PASS |

Output gồm corrupted/repaired clean, embeddings, answers, metrics, quality/freshness và report; baseline luôn giữ path/manifest riêng.

## 4. Giải thích phần kỹ thuật đã thực hiện

Flow kiểm tra baseline trước khi chạy, tạo corruption trên bản sao, build collection riêng, evaluate cùng frozen test set; sau đó rebuild clean từ raw snapshot và lặp lại chính chuỗi kiểm tra. Contract: baseline chỉ-đọc; corrupted được phép dirty có chủ đích; repaired phải qua strict validation. Input là raw/clean/test lock/manifest; output là artifact state-specific và comparison report.

## 5. Một quyết định kỹ thuật quan trọng

- **Quyết định:** tách hoàn toàn baseline, corrupted, repaired theo artifact và collection.
- **Lý do:** tránh baseline bị mutate và bảo đảm delta chỉ đến từ corruption/repair.
- **Bằng chứng:** CP6 xác nhận ba collection có 24 documents và baseline fingerprint không đổi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** index strict validation từ chối duplicate `paper_id` và summary rỗng.
- **Nguyên nhân:** đó là corruption cố ý nhưng không hợp lệ theo clean contract.
- **Xử lý:** chỉ cho phép `allow_intentional_corruption` khi build corrupted index; baseline/repaired vẫn strict.
- **Xác minh:** corrupted index build được; repaired validation và CP6 review PASS.

## 7. Hiểu biết về luồng end-to-end

Raw snapshot → cleaning baseline → index/retrieval → frozen evaluation → corruption có log → corrupted evaluation/signals → rebuild từ raw → repaired index/evaluation → comparison. Mỗi handoff có artifact, manifest/hash hoặc corruption log, nên downstream không phụ thuộc state bộ nhớ.

## 8. Phân tích kết quả

12 events gồm drop latest, blank summary, noise, truncate title, stale date và duplicate, mỗi loại 2 records. Kết quả `baseline → corrupted → repaired`: hit rate `1.00 → 0.75 → 1.00`; token F1 `1.00 → 0.7616 → 1.00`; judge accuracy `1.00 → 0.75 → 1.00`; judge score `5 → 4 → 5`; quality/freshness `True/True → False/False → True/True`; stale rows `0 → 2 → 0`. CP6 đối chiếu 12/12 ID bị tác động quay lại repaired data.

## 9. Điều học được và hướng cải thiện

Tôi học được rằng điều phối pipeline không chỉ là gọi các script theo đúng thứ tự. Điều quan trọng là biến mỗi handoff thành contract có thể kiểm tra: input có schema/path rõ ràng, output có manifest/hash/log, và baseline được xem như dữ liệu chỉ-đọc. Khi có corruption, pipeline có thể chạy xong nhưng chưa đủ để kết luận recovery; cần đồng thời thấy raw lineage, repaired schema, collection isolation, quality/freshness và evaluation metrics phục hồi.

Tôi cũng học được cách xử lý blocker liên vai trò: strict validation đúng cho clean data nhưng cần một ngoại lệ có phạm vi hẹp cho corruption experiment. Cờ cho phép intentional corruption chỉ có ý nghĩa khi không làm yếu contract baseline/repaired và có log để truy nguyên.

Hướng cải thiện là (1) đưa baseline fingerprint, test-lock assertion và comparison threshold vào CI; (2) chạy nhiều seed/mức severity để tránh kết luận từ một corruption configuration; (3) mở rộng test matrix theo corruption × field × query type; và (4) thêm dashboard tự động biểu diễn chuỗi `event → quality/freshness signal → retrieval/answer delta`. Thành công được đo bằng regression job tự chặn baseline mutation và report tái tạo cùng kết quả từ artifact đã persist.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Đinh Hoàng Quân**  
**Ngày xác nhận:** **2026-08-06**
