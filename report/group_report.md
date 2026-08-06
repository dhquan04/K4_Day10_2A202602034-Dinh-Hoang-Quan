# Báo cáo nhóm — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | ChickenFarmer |
| Repository | `K4_Day10_Nhom-ChickenFarmer` |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Deliverable chính |
| --: | --- | --- | --- | --- |
| 1 | Đinh Hoàng Quân | 2A202602034 | Integration, repair/comparison coordination | `corruption_flow.py`, CP4/CP6 review |
| 2 | Hoàng Thanh Sơn | 2A202601848 | Raw source, lineage, recovery point | `crossref.py`, checkpoint raw/lineage |
| 3 | Đỗ Việt Tùng | 2A202601876 | Controlled corruption, clean-data validation | `corruption.py`, corruption log, repaired validation |
| 4 | Vũ Bảo Chinh | 2A202601448 | RAG index, collection isolation, retrieval verification | Chroma manifests, Role 4 verification |
| 5 | Trịnh Hoàng Nam | 2A202601376 | Evaluation, quality/freshness, evidence | test-set lock, metrics, comparison evidence |

## 2. Tóm tắt kết quả

Nhóm hoàn thành pipeline từ raw Crossref snapshot đến clean dataset, Chroma retrieval, evaluation, quality/freshness observability, controlled corruption, repair từ raw và comparison ba trạng thái. Baseline có 24 records, test set khóa có 8 câu hỏi, collection `papers-baseline` có 24 documents. Corruption dùng seed 42 và 12 event thuộc sáu loại: drop latest, blank summary, noise summary, truncate title, stale date và duplicate rows. Dữ liệu corrupted vẫn 24 rows vì hai row bị drop được bù bởi hai row duplicate.

Corruption làm quality chuyển từ pass sang fail và freshness từ fresh sang stale; cụ thể stale rows tăng 0→2, đồng thời summary/uniqueness checks fail. Test set frozen có hai câu summary bám vào record bị drop, nên metric cũng giảm có chủ đích: retrieval hit rate `1.0→0.75`, token F1 `1.0→0.7616`, judge accuracy `1.0→0.75` và judge score `5→4`. Retrieval smoke test đồng thời cho thấy 2/3 frozen query mất expected top-1 trên collection corrupted. Repair được rebuild trực tiếp từ raw snapshot, không fetch dữ liệu mới và không sửa tay; toàn bộ metric, quality/freshness và frozen retrieval queries trở về mức baseline.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref snapshot → raw records → clean dataset → Chroma baseline
    → locked evaluation + quality/freshness
    → controlled corruption → papers-corrupted → evaluation/signals
    → rebuild from raw snapshot → papers-repaired → evaluation/signals
    → comparison report + CP6 review/demo
```

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref response | parse, normalize DOI, giữ raw snapshot | `data/raw/` | TV2 |
| Cleaning | raw records | validate, normalize, derived fields | `papers_clean.{csv,json}` | TV2/TV3 |
| Embedding/index | clean states | MiniLM + Chroma collections riêng | `data/embeddings/`, `data/chroma/` | TV4 |
| Evaluation | locked test set | retrieval, answer, F1, judge | `data/results/*answers,*metrics` | TV5 |
| Observability | three datasets | quality/freshness checks | `data/quality/` | TV5 |
| Corruption/repair | clean/raw snapshot | six corruption types; rebuild from raw | corrupted/repaired artifacts | TV1/TV3 |
| Orchestration | all artifacts | freeze baseline, compare, final review | `corruption_report.md`, CP6 demo | TV1 |

## 4. Cách tái hiện kết quả

| Cấu hình | Giá trị |
| --- | --- |
| LLM provider/model | cấu hình qua environment; không đưa API key vào report |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Crossref records | 24 |
| Retrieval top_k | 4 |
| Freshness threshold | 180 ngày |
| Corruption seed | 42 |

```powershell
uv sync
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
.\.venv\Scripts\python.exe script\verify_role4_cp5.py
.\.venv\Scripts\python.exe script\run_cp6_review.py
```

Các lệnh verify/review đã pass. `cp6_final_review.json` là evidence tổng hợp; `cp6_demo.md` là kịch bản demo dựa trên artifact đã persist.

## 5. Ingestion, cleaning và data contract

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API snapshot |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07,has-abstract:true` |
| Raw / clean records | 24 / 24 |
| Retry/backoff | có trong ingestion; CP3–CP6 đọc snapshot, không refresh source |

| Trường | Kiểu | Bắt buộc | Xử lý khi thiếu/sai |
| --- | --- | --- | --- |
| `paper_id` | string DOI | Có | loại record/kiểm tra unique |
| `title`, `summary` | string | Có | loại record nếu rỗng hoặc dưới ngưỡng |
| `published` | ISO date | Có | loại record nếu không parse được |
| `authors`, `categories` | list string | Không | normalize thành list/joined fields |
| `text_for_embedding`, `age_days` | derived | Có sau cleaning | rebuild từ clean fields |

`text_for_embedding` ghép title, authors, categories, published và summary. `paper_id` là DOI normalized xuyên suốt raw→clean→index→test set. `age_days` được tính từ ngày chạy và `published`.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Test set | 8 câu tại `data/eval/test_set.json` |
| Question types | summary, authors, date, categories |
| Ground truth | DOI trong `ground_truth_doc_ids`, đối chiếu manifest |
| Collections | `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Test-set lock | SHA-256 `A12649764805398145C1A89E1C84179B618C8BD72CC4129FACD79EF52AA66AAC` |

Cùng test set được giữ cho ba trạng thái để mọi delta chỉ có thể đến từ dữ liệu/index state, không đến từ thay đổi câu hỏi hay ground truth.

## 7. Kết quả baseline

| Artifact | Đường dẫn | Trạng thái |
| --- | --- | --- |
| Raw response/records | `data/raw/` | Có |
| Clean dataset | `data/clean/papers_clean.{csv,json}` | Có, 24 rows |
| Baseline manifest/index | `data/embeddings/papers_embeddings.json` | Có, 24 documents |
| Evaluation set | `data/eval/test_set.json` | Có, 8 samples |
| Metrics/answers | `data/results/baseline_{metrics,answers}.json` | Có |
| Quality/freshness | `data/quality/baseline_quality.json`, `freshness_report.json` | Có, pass/fresh |

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 8/8 câu có ground-truth document trong retrieval |
| `mean_token_f1` | 1.0 | Câu hỏi summary bám ground truth của baseline |
| `judge_accuracy` | 1.0 | 8/8 answer đúng theo fallback judge |
| `mean_judge_score` | 5.0 | trung bình score 1–5 |
| Ragas | skipped | chỉ chạy khi bật `RUN_RAGAS=1` |

## 8. Data quality và freshness

Baseline quality pass: 24 rows, DOI không null/unique, title/summary/text embedding đủ, `age_days` có và không âm. Baseline freshness có latest published `2026-08-05`, oldest `2026-02-12`, stale rows `0`, `is_fresh=true`.

## 9. Corruption scenarios và repair

| Corruption | Số record | Tác động quan sát được | Repair |
| --- | ---: | --- | --- |
| drop latest | 2 | latest published lùi tới `2026-07-10` | rebuild raw snapshot |
| blank summary | 2 | summary checks fail | rebuild raw snapshot |
| noise summary | 2 | embedding text bị nhiễu | rebuild raw snapshot |
| truncate title | 2 | exact title bị rút ngắn | rebuild raw snapshot |
| stale date | 2 | stale rows `0→2`, fresh `True→False` | rebuild raw snapshot |
| duplicate rows | 2 | `paper_id_unique` fail | rebuild raw snapshot |

`data/results/corruption_log.json` có ID, loại, tham số và before/after cho đủ 12 event. Repair dùng `restore_from_raw_snapshot()` rồi chạy cleaning lại, không copy corrupted dataframe hay gọi API mới.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.75 | 1.0 | giảm do record drop; repair phục hồi |
| `mean_token_f1` | 1.0 | 0.7616 | 1.0 | answer quality giảm rồi phục hồi |
| `judge_accuracy` | 1.0 | 0.75 | 1.0 | 2 câu mất ground truth ở corrupted |
| `mean_judge_score` | 5.0 | 4.0 | 5.0 | score phục hồi hoàn toàn |
| quality passed | True | False | True | repair phục hồi quality |
| fresh | True | False | True | repair phục hồi freshness |
| stale rows | 0 | 2 | 0 | stale-date corruption được khôi phục |

Kết luận có evidence:

1. `blank_summary` và `duplicate_rows` làm quality checks fail; repair từ raw đưa checks về pass.
2. `stale_date` làm freshness `True→False` và stale rows `0→2`; repair đưa lại `False→True` và `2→0`.
3. Frozen semantic retrieval mất expected top-1 ở 2/3 query trên corrupted; repaired khôi phục expected baseline ranks. Locked evaluation metrics cũng giảm ở corrupted và phục hồi hoàn toàn ở repaired.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** corrupted dataframe có duplicate DOI và blank summary nên strict index validation ban đầu từ chối build index.
- **Nguyên nhân:** strict validation được thiết kế cho clean baseline, trong khi CP5 phải giữ nguyên corruption để đo impact.
- **Cách xử lý:** thêm cờ `allow_intentional_corruption` chỉ cho corrupted flow; vẫn yêu cầu paper ID/title/text embedding hợp lệ để Chroma lưu được.
- **Xác minh:** tạo `papers-corrupted` riêng, chạy `script/verify_role4_cp5.py`; baseline logical fingerprint không đổi.

## 12. Giới hạn và hướng cải thiện

| Giới hạn | Ảnh hưởng | Hướng cải thiện |
| --- | --- | --- |
| Test set nhỏ, 8 câu | chỉ đo một phần corruption scenarios | mở rộng thêm câu hỏi cho blank/noise/truncate scenarios |
| Fallback judge khi LLM không khả dụng | judge score phụ thuộc heuristic | chạy LLM judge có credential và lưu trace đã che secret |
| Ragas chưa chạy | thiếu metric Ragas | bật `RUN_RAGAS=1` trong môi trường có model/credentials phù hợp |

## 13. Checklist trước khi nộp

- [x] Có thông tin nhóm và phân công thành viên.
- [x] Baseline, corrupted, repaired dùng cùng test set.
- [x] Metrics/quality/freshness khớp artifact thực tế.
- [x] Có repaired artifacts, comparison report và CP6 demo.
- [x] Ba collection tách biệt; baseline logical content được kiểm tra.
- [x] Secret scan và portable-path scan pass; `.env` không được Git track.
