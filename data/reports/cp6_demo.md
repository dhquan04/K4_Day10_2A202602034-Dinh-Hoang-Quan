# CP6 Demo — Clean → Corrupted → Repaired

## Scope and evidence

- Source refresh: disabled; repair reads `data/raw/crossref_records.json`.
- Raw records: 24; corruption-event IDs restored: 12/12.
- Repaired schema: PASS; repaired core fields match baseline: True.
- Locked test set: 8 samples; SHA-256 `a12649764805398145c1a89e1c84179b618c8bd72cc4129facd79ef52aa66aac`.

## Collection separation and retrieval smoke test

| State | Collection | Documents | Frozen-query expected ranks |
| --- | --- | ---: | --- |
| baseline | papers-baseline | 24 | 1, 1, 1 |
| corrupted | papers-corrupted | 24 | None, None, 1 |
| repaired | papers-repaired | 24 | 1, 1, 1 |

`lookup()` is available on all three indexes; the CP3 agent/tool trace remains the factual-agent evidence for the baseline corpus.

## Observed comparison

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| quality.passed | True | False | True |
| freshness.is_fresh | True | False | True |
| stale_rows | 0 | 2 | 0 |
| retrieval_hit_rate | 1.0 | 0.75 | 1.0 |
| mean_token_f1 | 1.0 | 0.7616279069767442 | 1.0 |

Recovery is confirmed for data quality and freshness. The locked test set did not show an aggregate retrieval/answer-metric delta, therefore recovery is not claimed for a metric that did not change.
