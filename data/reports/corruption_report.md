# CP5 Corruption Comparison Report

## Controlled corruption

- Seed: `42`
- Rows: `24` baseline → `24` corrupted
- Events: drop_latest=2, blank_summary=2, noise_summary=2, truncate_title=2, stale_date=2, duplicate_rows=2
- Repair source: immutable raw snapshot (`data/raw/crossref_records.json`).

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| samples | 8 | 8 | 8 |
| retrieval_hit_rate | 1.0 | 1.0 | 1.0 |
| mean_token_f1 | 0.75 | 0.75 | 0.75 |
| judge_accuracy | 0.75 | 0.75 | 0.75 |
| mean_judge_score | 4 | 4 | 4 |

## Quality and freshness signals

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| quality.passed | True | False | True |
| row_count | 24 | 24 | 24 |
| freshness.is_fresh | True | False | True |
| freshness.stale_rows | 0 | 2 | 0 |

## Evidence rule

Changes are reported as observed values above. A causal claim is limited to corruption events and signal/metric deltas present in these artifacts; no claim is inferred when the values do not change.
