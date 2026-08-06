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
| Frozen test set | `data/eval/test_set.json`, `data/quality/test_set_lock.json` | questions/ground-truth DOI | 8 samples + SHA-256 lock | Hoàn thành |
| Evaluation | `src/evaluation/metrics.py:evaluate_pipeline()` | manifest/index state + frozen set | `data/results/{baseline,corrupted,repaired}_{answers,metrics}.json` | Hoàn thành |
| Observability | `src/observability/quality.py` | clean state + corruption log | `data/quality/*_{quality,freshness}.json` | Hoàn thành |
| Comparison | `src/observability/reporting.py:generate_corruption_report()` | metrics/signals/log | `data/reports/corruption_report.md` | Hoàn thành |

Tôi sở hữu evidence đánh giá và observability; không thay đổi raw, clean hoặc index ngoài việc đọc artifact đã bàn giao.

### Nhiệm vụ theo checkpoint CP1–CP6

| Checkpoint | Nhiệm vụ thực hiện | Kết quả/bằng chứng |
|---|---|---|
| CP1 | Chuẩn bị rule quality/freshness và draft câu hỏi có `ground_truth_doc_ids`. | Contract đánh giá đầu vào/đầu ra. |
| CP2 | Khóa 8 câu test set, audit baseline manifest và format evidence. | `data/quality/test_set_lock.json`. |
| CP3 | Xác minh answers, metrics, quality và freshness của baseline. | `baseline_{answers,metrics}.json`, `baseline_quality.json`, `freshness_report.json`. |
| CP4 | Khóa fingerprint test set và dự báo signal khi corruption. | `test_set_lock.json`. |
| CP5 | Evaluate corrupted bằng test set cũ; nối log → signal → metric khi có evidence. | `corrupted_{answers,metrics}.json`, quality/freshness, report. |
| CP6 | Evaluate repaired, tính delta ba state và review report. | `repaired_{answers,metrics}.json`, `cp6_final_review.json`. |

Chi tiết thực hiện: CP1 xác định rule quality/freshness và draft câu hỏi/ground truth; CP2 khóa test set, kiểm tra manifest baseline và chuẩn bị format evidence; CP3 chạy baseline answers/metrics/signals làm mốc. CP4 lưu test-set fingerprint và dự báo duplicate/blank summary sẽ làm quality fail, stale date sẽ làm freshness fail. CP5 đánh giá corrupted bằng đúng test set cũ, sinh answers/metrics/quality/freshness và chỉ liên kết event → signal → metric khi log hỗ trợ. CP6 đánh giá repaired, tính toàn bộ delta baseline–corrupted–repaired, kiểm tra JSON/report đồng nhất và ghi rõ recovery/giới hạn dựa trên dữ liệu thật.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Test sensitivity review | Cleaning/Lead | 2 questions nhắm drop records |
| State artifact check | Retrieval | evaluate đúng collection |
| Final evidence review | CP6 | metrics/signal/report nhất quán |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Khóa test set | `data/quality/test_set_lock.json` | 8 samples, SHA-256 cố định | lock assertion PASS |
| Evaluate ba state | `data/results/*_{answers,metrics}.json` | cùng 8 câu cho 3 state | 8 answers/state, metric JSON hợp lệ |
| Report causal evidence | `data/reports/corruption_report.md` | event → signal → metric | đối chiếu `corruption_log.json` và signal/metric JSON |

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

Tôi học được rằng frozen test set bảo đảm tính công bằng nhưng chưa tự động bảo đảm độ nhạy. Nếu test set không chứa câu hỏi liên quan record bị drop hoặc trường bị corrupt, metric có thể không đổi dù dữ liệu đã xấu. Vì vậy cần thiết kế câu hỏi theo failure mode và vẫn giữ cùng một tập đó cho ba trạng thái, thay vì thay câu hỏi để làm kết quả đẹp hơn.

Tôi cũng học được không nên suy diễn quality từ một metric duy nhất. Hit rate/judge score cho thấy ảnh hưởng tới retrieval/answer; quality checks giải thích duplicate/blank summary; freshness giải thích stale date; corruption log nối các quan sát này về nguyên nhân. Kết luận recovery chỉ đáng tin khi answers, metrics, signals và lineage cùng phục hồi.

Hướng cải thiện là tăng số sample theo từng corruption type, thêm Recall@k/MRR/nDCG và latency, chạy nhiều seed và báo confidence interval. Khi môi trường có model phù hợp, có thể bật RAGAS hoặc judge độc lập kèm trace đã che secret. Thành công được đo bằng coverage rõ ràng cho mỗi failure mode và comparison report có thể định lượng độ chắc chắn, không chỉ báo một điểm metric từ 8 câu hỏi.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Trịnh Hoàng Nam**  
**Ngày xác nhận:** **2026-08-06**
