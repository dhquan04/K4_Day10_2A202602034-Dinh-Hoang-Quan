# CP5 corruption plan and Role 4 baseline lock

This document freezes the controlled-corruption handoff from Member 3 and the
baseline retrieval comparison set owned by Member 4. The plan is generated
with seed `42`; the executed event details are stored in
`data/results/corruption_log.json`.

## Member 3 — planned corruption records

Baseline has 24 rows. The planned corrupted artifact has 24 rows: two latest
records are removed and two rows are duplicated. Corruption categories are
disjoint except the two duplicate copies.

| Type | paper_id | Parameter | Expected change |
| --- | --- | --- | --- |
| drop_latest | `10.2118/234689-pa` | `top_2_by_published` | Remove paper (published `2026-08-05`). |
| drop_latest | `10.1007/s10278-026-02086-9` | `top_2_by_published` | Remove paper (published `2026-07-13`). |
| blank_summary | `10.20944/preprints202602.0996.v1` | `summary=''` | Empty summary and rebuilt embedding text. |
| blank_summary | `10.63646/kpqm1958` | `summary=''` | Empty summary and rebuilt embedding text. |
| noise_summary | `10.3390/buildings16132637` | suffix `qxzjk noise7712 !!garbled!! asdkjh` | Append deterministic noise to summary. |
| noise_summary | `10.55041/isjem07213` | suffix `qxzjk noise7712 !!garbled!! asdkjh` | Append deterministic noise to summary. |
| truncate_title | `10.52060/juptik.v4i1.4318` | `max_chars=12` | Title becomes `Chatbot Hybr`. |
| truncate_title | `10.21203/rs.3.rs-9770645/v1` | `max_chars=12` | Title becomes `Adapting Lar`. |
| stale_date | `10.20944/preprints202604.0339.v1` | `shift_days=400` | Published date `2026-04-06` → `2025-03-02`. |
| stale_date | `10.3390/app16052244` | `shift_days=400` | Published date `2026-02-26` → `2025-01-22`. |
| duplicate_rows | `10.21203/rs.3.rs-10012178/v1` | `exact_copy` | Retain two rows with the same `paper_id`. |
| duplicate_rows | `10.1093/sleep/zsag091.0346` | `exact_copy` | Retain two rows with the same `paper_id`. |

The handoff artifacts are `data/clean/papers_clean_corrupted.json` and
`data/results/corruption_log.json`. The log is the source of truth for the
actual run; CP5 must not change the baseline artifact.

## Member 4 — baseline comparison lock

The comparison baseline is frozen before building `papers-corrupted`.

| Item | Locked value |
| --- | --- |
| Clean artifact | `data/clean/papers_clean.json` — 24 rows / 24 unique IDs |
| Clean SHA-256 | `EC7AD1E074093FA0A48E4022DC8EAFFB623558013F0675AD64359761340F530A` |
| Collection | `papers-baseline` — 24 documents |
| Manifest | `data/embeddings/papers_embeddings.json` |
| Manifest SHA-256 | `19850BCEC20081B9CFAA8F0B65989D8E24B186EAF1AD81473B27F816A6C935F8` |
| Verification evidence | `data/results/role4_cp3_verification.json` (status `pass`) |
| Collection mutation rule | CP5 may only create/use `papers-corrupted`; it must not delete or rebuild `papers-baseline`. |

### Frozen semantic queries

1. `Which paper proposes a retrieval-augmented framework for oil and gas safety report generation?`
   Expected baseline top-1: `10.2118/234689-pa`.
2. `Which paper uses multimodal agentic retrieval for diagnostic support of jawbone lesions?`
   Expected baseline top-1: `10.1007/s10278-026-02086-9`.
3. `Which paper studies retrieval-augmented language models for cross-market equity time-series forecasting?`
   Expected baseline top-1: `10.21203/rs.3.rs-10178277/v1`.

### Frozen exact and agent checks

- Exact lookup: paper ID and title for `10.2118/234689-pa` / *SafeRAG: A
  Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil
  and Gas Safety Report Generation*.
- Agent factual check: ask for the SafeRAG authors; require `lookup_paper` and
  verify the answer is grounded in that tool output.

At CP5, run the same checks against `papers-corrupted` and record the delta
without altering these locked baseline inputs.
