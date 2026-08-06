# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | **Trịnh Hoàng Nam** |
| MSSV | **2A202601376** |
| Khóa/Lớp | K4 |
| Tên nhóm | ChickenFarmer |
| Vai trò chính | Thành viên 5 — Evaluation, quality/freshness và comparison evidence |
| Repository | `K4_Day10_Nhom-ChickenFarmer` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Frozen test set | `test_set.json`, `test_set_lock.json` | questions/ground truths | 8 samples + SHA-256 lock | Hoàn thành |
| Evaluation | `evaluate_pipeline()` | index state + frozen set | answers/metrics JSON | Hoàn thành |
| Observability | quality/freshness modules | clean state + log | quality/freshness JSON | Hoàn thành |
| Comparison | `generate_corruption_report()` | metrics/signals/log | corruption report | Hoàn thành |

Tôi sở hữu evidence đánh giá và observability; không thay đổi raw, clean hoặc index ngoài việc đọc artifact đã bàn giao.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Test sensitivity review | Cleaning/Lead | 2 questions nhắm drop records |
| State artifact check | Retrieval | evaluate đúng collection |
| Final evidence review | CP6 | metrics/signal/report nhất quán |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Khóa test set | `test_set_lock.json` | 8 samples, hash cố định | lock assertion PASS |
| Evaluate ba state | answers/metrics JSON | cùng câu hỏi cho 3 state | đủ 8 answers/state |
| Report causal evidence | `corruption_report.md` | event → signal → metric | đối chiếu log/JSON |

## 4. Giải thích phần kỹ thuật đã thực hiện

`evaluate_pipeline()` nhận state-specific index và frozen test set, phát answers cùng hit rate, token F1, judge accuracy/score. Quality/freshness đọc clean artifact để đo uniqueness, summary/content và stale date. Contract bắt buộc mọi run dùng 8 samples với SHA-256 `a12649764805398145c1a89e1c84179b618c8bd72cc4129facd79ef52aa66aac`; output ghi đúng state để report không trộn số liệu.

## 5. Một quyết định kỹ thuật quan trọng

- **Quyết định:** giữ một test set frozen chung cho baseline/corrupted/repaired.
- **Lý do:** thay đổi câu hỏi hoặc ground truth giữa state sẽ làm metric không còn comparable.
- **Bằng chứng:** cả ba output có 8 answers, hash lock được CP6 xác minh.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** test set ban đầu không đủ nhạy, có corruption nhưng metric có thể chưa giảm.
- **Nguyên nhân:** câu hỏi chưa phủ hai record `drop_latest`.
- **Xử lý:** trước full rerun, chọn hai câu hỏi summary trỏ đúng affected records rồi khóa lại test set; không đổi test set theo state.
- **Xác minh:** rerun cho delta `1.00 → 0.75 → 1.00` và report/CP6 PASS.

## 7. Hiểu biết về luồng end-to-end

RAG bàn giao index/manifest theo state; evaluator dùng một test set immutable để tạo answers/metrics; observability đọc artifact clean và corruption log; comparison report liên kết event, signal và evaluation delta. Repair chỉ được kết luận sau khi repaired data, index và metrics được tạo lại từ raw path.

## 8. Phân tích kết quả

12 events gồm hai event cho mỗi loại: drop latest, blank summary, noise, truncate title, stale date và duplicate. Kết quả thật:

| Chỉ số | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 1.00 | 0.75 | 1.00 |
| Mean token F1 | 1.00 | 0.7616 | 1.00 |
| Judge accuracy | 1.00 | 0.75 | 1.00 |
| Mean judge score | 5 | 4 | 5 |
| Quality/Freshness | True/True | False/False | True/True |
| Stale rows | 0 | 2 | 0 |

Hai drop events giải thích hit rate/judge giảm tại hai câu hỏi tương ứng; blank/noise/truncate/duplicate/stale có evidence thêm ở signals. CP6 kiểm tra 12/12 affected IDs được recovery, do đó kết luận dựa trên metrics, quality/freshness và lineage thay vì một score đơn lẻ.

## 9. Điều học được và hướng cải thiện

Metric chỉ có ý nghĩa khi test set phủ failure mode. Có thể tăng số samples, thêm MRR/nDCG/Recall@k, chạy nhiều seed, dùng judge độc lập/RAGAS và báo confidence interval.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Trịnh Hoàng Nam**  
**Ngày xác nhận:** **2026-08-06**
