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
| Fetched at | N/A (fill at CP3) |

## 2. Evaluation metrics

| Metric | Giá trị |
| --- | --- |
| samples | N/A (fill at CP3) |
| retrieval_hit_rate | N/A (fill at CP3) |
| mean_token_f1 | N/A (fill at CP3) |
| judge_accuracy | N/A (fill at CP3) |
| mean_judge_score | N/A (fill at CP3) |
| ragas | N/A (fill at CP3) |

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

## 6. Notes for CP3

- Điền metrics từ `evaluate_pipeline` (không hard-code).
- Giải thích ít nhất một retrieval hit/miss bằng `baseline_answers.json`.
- Đối chiếu quality/freshness với artifact JSON trong `data/quality/`.
