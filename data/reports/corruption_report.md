# CP5 Corruption Comparison Report

## Controlled corruption

- Seed: `42`
- Rows: `24` baseline → `24` corrupted
- Events: drop_latest=2, blank_summary=2, noise_summary=2, truncate_title=2, stale_date=2, duplicate_rows=2
- Repair source: immutable raw snapshot (`data/raw/crossref_records.json`).
- Evaluation set: locked `data/eval/test_set.json` (same for all three states).

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| samples | 8 | 8 | 8 |
| retrieval_hit_rate | 1 | 1 | 1 |
| mean_token_f1 | 0.75 | 0.75 | 0.75 |
| judge_accuracy | 0.75 | 0.75 | 0.75 |
| mean_judge_score | 4 | 4 | 4 |

## Quality and freshness signals

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| quality.passed | True | False | True |
| row_count | pass | pass | pass |
| paper_id_unique | pass | fail | pass |
| summary_not_null | pass | fail | pass |
| summary_min_length | pass | fail | pass |
| freshness.is_fresh | True | False | True |
| freshness.stale_rows | 0 | 2 | 0 |
| freshness.max_age_days | 175 | 561 | 175 |
| freshness.latest_published | 2026-08-05 | 2026-07-10 | 2026-08-05 |

## Causal links (only with observed numbers)

- `blank_summary` → `summary_not_null`/`summary_min_length` fail on corrupted (2 missing) → repaired recovers (`pass`).
- `duplicate_rows` → `paper_id_unique` fail on corrupted → repaired unique again.
- `stale_date` → `freshness.stale_rows` 0→2→0; `is_fresh` True→False→True.
- `drop_latest` → `latest_published` 2026-08-05→2026-07-10 (repaired restores baseline date when clean rebuild succeeds).
- Agent metrics (`samples`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) **không đổi** giữa baseline/corrupted/repaired trên locked test set. Không kết luận corruption làm RAG kém hơn về metric khi số liệu không thay đổi.

## Evidence rule

Changes are reported as observed values above. A causal claim is limited to corruption events and signal/metric deltas present in these artifacts; no claim is inferred when the values do not change.
