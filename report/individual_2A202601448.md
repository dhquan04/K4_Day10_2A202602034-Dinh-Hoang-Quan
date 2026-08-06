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
| Baseline index | `LocalEmbeddingIndex` | clean baseline | `papers-baseline`, manifest | Hoàn thành |
| Corrupted index | index build | corrupted clean | `papers-corrupted`, manifest | Hoàn thành |
| Repaired index | index build | repaired clean | `papers-repaired`, manifest | Hoàn thành |
| Retrieval validation | `verify_role4_cp5.py` | manifests/frozen queries | verification JSON | Hoàn thành |

Tôi sở hữu retrieval/index contract và tính tách biệt collection; evaluation chỉ dùng index state được bàn giao.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Chốt document/metadata | Cleaning | `text_for_embedding` và identity hợp lệ |
| Query delta | Evaluation | retrieval evidence theo state |
| Agent/tool smoke test | Lead | agent grounded vào retrieval |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Tạo ba collection | embedding manifests | collection/path riêng, 24 docs/state | CP6 review |
| Bảo vệ baseline | role4 verification | fingerprint không đổi | `verify_role4_cp5.py` |
| Smoke retrieval | CP6 demo/review | 3 frozen queries chạy theo state | ranks được đối chiếu |

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

Collection namespace và manifest là ranh giới experiment quan trọng. Nên bổ sung versioned collection names, assertion chống trộn manifest, cùng ranking metrics MRR/nDCG/Recall@k.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end và evidence đi kèm.
- [x] Không có kết luận recovery thiếu artifact hoặc metric.
- [x] Báo cáo không chứa API key, token hoặc secret.

**Họ và tên:** **Vũ Bảo Chinh**  
**Ngày xác nhận:** **2026-08-06**
