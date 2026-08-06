# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | **Vũ Bảo Chinh** |
| MSSV | **2A202601448** |
| Khóa/Lớp | K4 |
| Tên nhóm | ChickenFarmer |
| Vai trò chính | Thành viên 4 — Retrieval, vector index và collection validation |
| Repository | `K4_Day10_Nhom-ChickenFarmer` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Baseline index | `src/retrieval/index.py:LocalEmbeddingIndex` | `papers_clean.{csv,json}` | `papers-baseline`, `papers_embeddings.json` | Hoàn thành |
| Corrupted index | `LocalEmbeddingIndex.build()` | corrupted clean | `papers-corrupted`, `papers_embeddings_corrupted.json` | Hoàn thành |
| Repaired index | `LocalEmbeddingIndex.build()` | repaired clean | `papers-repaired`, `papers_embeddings_repaired.json` | Hoàn thành |
| Retrieval validation | `script/verify_role4_cp5.py` | manifests/frozen queries | `data/results/role4_cp5_verification.json` | Hoàn thành |

Tôi sở hữu retrieval/index contract và tính tách biệt collection; evaluation chỉ dùng index state được bàn giao.

### Nhiệm vụ theo checkpoint CP1–CP6

| Checkpoint | Nhiệm vụ thực hiện | Kết quả/bằng chứng |
|---|---|---|
| CP1 | Kiểm tra clean schema và chuẩn bị retrieval/index contract. | Identity, metadata và embedding input được chốt. |
| CP2 | Build `papers-baseline`, manifest và smoke test retrieval. | `papers_embeddings.json`, collection 24 docs. |
| CP3 | Xác minh exact lookup, semantic retrieval và agent grounding baseline. | `data/results/role4_cp3_verification.json`. |
| CP4 | Khóa collection baseline và frozen comparison queries. | Baseline không bị mutate. |
| CP5 | Tạo `papers-corrupted`, chạy lại baseline query và xác minh index baseline tách biệt. | `role4_cp5_verification.json`. |
| CP6 | Tạo `papers-repaired`, smoke test agent/tool/retrieval và demo ba collection/path. | CP6 review/demo PASS. |

Chi tiết thực hiện: CP1 đọc contract về `paper_id`, metadata và `text_for_embedding`; CP2 build collection/manifest baseline và kiểm tra semantic search; CP3 xác minh exact DOI/title lookup, semantic retrieval và agent tool grounding. CP4 khóa manifest baseline và frozen queries dùng để so sánh. CP5 tạo `papers-corrupted` tách biệt, cho phép intentional dirty input chỉ tại nhánh này, chạy lại query baseline và đối chiếu fingerprint. CP6 build `papers-repaired`, chạy smoke retrieval/agent trên ba path riêng, đối chiếu expected rank với baseline và bàn giao evidence cho review/demo.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Chốt document/metadata | Cleaning | `text_for_embedding` và identity hợp lệ |
| Query delta | Evaluation | retrieval evidence theo state |
| Agent/tool smoke test | Lead | agent grounded vào retrieval |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Tạo ba collection | `data/embeddings/papers_embeddings*.json` | collection/path riêng, 24 docs/state | `cp6_final_review.json` |
| Bảo vệ baseline | `data/results/role4_cp5_verification.json` | fingerprint không đổi | `script/verify_role4_cp5.py` |
| Smoke retrieval | `data/reports/cp6_demo.md` | 3 frozen queries chạy theo state | expected ranks được đối chiếu |

## 4. Giải thích phần kỹ thuật đã thực hiện

Input là clean artifact có `paper_id`, `title`, `text_for_embedding` và metadata; output là Chroma collection/manifest và ranked retrieval results. `paper_id::row_index` định danh record index, semantic search dùng vector collection và lookup dùng identity exact. Contract yêu cầu collection/manifest khớp state; baseline không bị write khi build corrupted/repaired.

## 5. Một quyết định kỹ thuật quan trọng

- **Quyết định:** dùng ba collection `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- **Lý do:** một collection chung có thể trộn vector hoặc ghi đè baseline.
- **Bằng chứng:** CP6 xác nhận mỗi collection 24 documents; baseline fingerprint không đổi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** index reject `paper_id` trùng và summary rỗng trong corrupted data.
- **Nguyên nhân:** validation clean đúng nhưng không phân biệt state thí nghiệm.
- **Xử lý:** `allow_intentional_corruption` chỉ áp dụng lúc build `papers-corrupted`.
- **Xác minh:** corrupted index build thành công; baseline/repaired vẫn strict validation PASS.

## 7. Hiểu biết về luồng end-to-end

Clean artifact → embeddings/index manifest → semantic search/exact lookup → answers/metrics. Corruption và repair lặp lại chính flow với collection khác; Role 5 nhận đúng index state và Role 1 compare bằng manifest/artifact thay vì collection mutable.

## 8. Phân tích kết quả

12 events gồm drop latest, blank summary, noise, truncate title, stale date, duplicate (mỗi loại 2). Ba frozen semantic queries cho thấy corrupted mất expected top-1 ở 2/3 query, repaired quay về rank baseline. Aggregate metrics là hit rate `1.00 → 0.75 → 1.00`, token F1 `1.00 → 0.7616 → 1.00`, judge accuracy `1.00 → 0.75 → 1.00`, judge score `5 → 4 → 5`; quality/freshness `True/True → False/False → True/True`, stale rows `0 → 2 → 0`.

## 9. Điều học được và hướng cải thiện

Tôi học được rằng vector index không chỉ là nơi lưu embedding; collection name, manifest và record identity là ranh giới tái lập của experiment. Dùng chung một collection cho baseline/corrupted/repaired có thể trả kết quả tưởng đúng nhưng không biết vector nào đang được query. Manifest tách biệt giúp biết chính xác clean state, embedding artifact và collection nào tạo ra một metric.

Tôi cũng học được cần phân tích semantic retrieval và exact lookup riêng. Một câu chứa DOI có thể vẫn trả lời đúng nhờ lookup dù semantic content bị noise; vì vậy chỉ xem answer score sẽ không đủ, cần xem retrieved IDs/ranks và query type. Ngoại lệ index cho intentional corruption cũng phải được khoanh vùng để không biến validation strict thành hình thức.

Hướng cải thiện: dùng versioned collection names và assertion manifest–collection trước query; ghi retrieval trace gồm query, IDs, distances và state; đánh giá Recall@k, MRR, nDCG, latency trên tập query không lộ DOI/exact title. Cải thiện đạt yêu cầu khi ranking metrics và trace chỉ rõ degradation/recovery, đồng thời không có cross-state contamination.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Vũ Bảo Chinh**  
**Ngày xác nhận:** **2026-08-06**
