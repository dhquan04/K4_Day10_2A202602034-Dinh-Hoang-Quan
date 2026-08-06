# Phase 1 Baseline Report

> Khung report (Role 5 / observability). Số liệu metrics đầy đủ sau khi Lead chạy `phase1` ở CP3.

## 1. Source summary

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Raw records | 24 |
| Clean records | 24 |
| Fetched at | 2026-08-06T07:47:16.896756+00:00 |

## 2. Evaluation metrics

| Metric | Giá trị |
| --- | --- |
| samples | 8 |
| retrieval_hit_rate | 1.0 |
| mean_token_f1 | 0.75 |
| judge_accuracy | 0.75 |
| mean_judge_score | 4 |
| ragas | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |

## 3. Data quality

| Check | Dimension | Status | Detail |
| --- | --- | --- | --- |
| row_count | completeness | pass | 24 rows |
| paper_id_not_null | validity | pass | 0 null/blank paper_id values |
| paper_id_unique | uniqueness | pass | 0 duplicate rows across 24 unique ids |
| title_not_null | completeness | pass | 0 rows missing title |
| summary_not_null | completeness | pass | 0 rows missing summary |
| summary_min_length | validity | pass | 0 summaries shorter than 40 characters |
| text_for_embedding_present | completeness | pass | 0 rows missing text_for_embedding |
| age_days_present | freshness | pass | 0 rows missing age_days |
| age_days_non_negative | freshness | pass | 0 rows with negative age_days |

Overall quality passed: `True`

## 4. Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| freshness_threshold_days | 180 |
| latest_published | 2026-08-05 |
| oldest_published | 2026-02-12 |
| mean_age_days | 77.75 |
| max_age_days | 175 |
| stale_rows | 0 |
| total_rows | 24 |
| is_fresh | True |

## 5. Evidence paths

- Clean dataset: `data/clean/papers_clean.{csv,json}`
- Evaluation set: `data/eval/test_set.json`
- Embedding manifest: `data/embeddings/papers_embeddings.json`
- Quality: `data/quality/`
- Metrics: `data/results/baseline_metrics.json`
- Answers: `data/results/baseline_answers.json`

## 6. Baseline evaluation notes (CP3)

- Metrics lấy từ `data/results/baseline_metrics.json` (không hard-code).
- Retrieval hit: 8/8 (`retrieval_hit_rate=1.0`); mọi `ground_truth_doc_ids` có trong clean + index.
- Answer quality gap: `categories-07`/`categories-08` retrieval hit nhưng `answer=""` (metadata `categories_joined` rỗng) → `token_f1=0`, judge incorrect. GT dùng `primary_category=uncategorized`.
- Judge hiện dùng fallback heuristic khi LLM evaluator unavailable.
- Đối chiếu report ↔ quality/freshness/metrics JSON đã khớp trước khi đóng baseline.
