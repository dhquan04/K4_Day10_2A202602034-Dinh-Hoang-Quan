# CP4 — Thành viên 1: Baseline checklist & blocker

**Thời điểm kiểm tra:** 2026-08-06 02:00–02:15 (Asia/Ho_Chi_Minh)  
**Mục đích:** chốt các input cho CP5 mà không chạy corruption, không fetch nguồn mới và không ghi đè baseline.

## Kết luận handoff

Các artifact logic của baseline đã đủ để chuẩn bị CP5. Tuy nhiên, trạng thái **baseline index chưa được khóa hoàn toàn** vì Git đang báo ba file thuộc `data/chroma/` đã thay đổi. Không được rebuild hoặc ghi vào collection `papers-baseline` cho đến khi chủ sở hữu index xác nhận các thay đổi này vô hại hoặc khôi phục snapshot phù hợp.

## Checklist

| Hạng mục | Trạng thái | Bằng chứng / điểm khóa |
| --- | --- | --- |
| Raw source để repair | PASS | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`; raw records = 24 |
| Clean baseline | PASS | `data/clean/papers_clean.json`; clean records = 24 |
| Lineage raw → clean → index | PASS | `report/role2_checkpoint_3.md`; `data/results/role4_cp3_verification.json` |
| Test set cố định | PASS | `data/eval/test_set.json`; 8 samples; dùng nguyên file này cho baseline/corrupted/repaired |
| Query / RAG baseline | PASS | collection `papers-baseline`, 24 documents; CP3 verification có `status: pass` |
| Baseline answers & metrics | PASS | `data/results/baseline_answers.json`, `data/results/baseline_metrics.json` |
| Baseline quality & freshness | PASS | `data/quality/baseline_quality.json`, `data/quality/baseline_signals.json`, `data/quality/freshness_report.json` |
| Index baseline không mutate | HOLD | `data/chroma/chroma.sqlite3`, `data_level0.bin`, `length.bin` đang modified theo Git status; cần xác nhận/khóa trước CP5 |
| Corruption flow sẵn sàng chạy | BLOCKED | `src/ingestion/corruption.py` và `src/pipelines/corruption_flow.py` còn `NotImplementedError` |

## Fingerprint snapshot

Các hash SHA-256 sau là mốc đối chiếu trước/sau CP5. Bất kỳ thay đổi nào ở raw, clean, test set hoặc baseline evidence phải được ghi nhận và không được dùng để thay thế baseline hiện tại.

| Artifact | SHA-256 |
| --- | --- |
| `data/raw/crossref_response.json` | `69EAD15516FE024BDDD1F444BA3B2EBF0744A09C1FA3CD05A044BA22BF4BD0AC` |
| `data/raw/crossref_records.json` | `CFE7451E6CEE059BE5C28FA8A38B2C4CCDAA9AC9BC7CFD2D50A121BEAE2390CD` |
| `data/clean/papers_clean.json` | `EC7AD1E074093FA0A48E4022DC8EAFFB623558013F0675AD64359761340F530A` |
| `data/eval/test_set.json` | `D4BA5764269EFE3D32EF4C3873ABD393C16AFB9D90C34FC337AD66981F4F6450` |
| `data/results/baseline_metrics.json` | `D59B8018664583439C40B0CD8AB477F15078DC07C41FE0CFE4BDA0C7AFA40A97` |
| `data/quality/baseline_signals.json` | `353F282071F77A1905B6548C313D985A4090814E2D47B2CB30FC3BBBA2D33BC9` |
| `data/results/role4_cp3_verification.json` | `E2AC35E7F75BA150041D2F18B74A6E3E11F0E48DE9C70076A092C63256479032` |

## Blocker và hành động chuyển CP5

1. **Owner index (Thành viên 4):** xác nhận `papers-baseline` vẫn có 24 documents và dừng mọi thao tác ghi vào `data/chroma/`. Corruption phải dùng collection tách biệt `papers-corrupted`.
2. **Owner corruption (Thành viên 3):** implement `corrupt_clean_dataframe` và `corruption_flow`; ghi log gồm ID, loại corruption, tham số, số record trước/sau; output phải nằm ở các artifact corrupted/repaired riêng.
3. **Owner source (Thành viên 2):** giữ nguyên hai raw artifacts ở trên; repair chỉ đọc từ snapshot này, không gọi fetch mới.
4. **Owner evaluation (Thành viên 5):** dùng đúng test-set hash ở trên khi evaluate corrupted và repaired; liên kết corruption log → quality/freshness signal → metric chỉ khi có evidence.

## Quy tắc khóa baseline

- Không thay đổi `data/raw/`, `data/clean/papers_clean.*`, `data/eval/test_set.json`, baseline metrics/answers hoặc `papers-baseline`.
- Không fetch Crossref hoặc các nguồn mới.
- Tất cả corrupted/repaired datasets, manifests, collections, quality reports, answers và metrics phải dùng đường dẫn/tên tách biệt.
- So sánh CP5 phải lấy baseline evidence trong checklist này làm mốc, không chạy lại baseline trên nguồn dữ liệu đã thay đổi.
