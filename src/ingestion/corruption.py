from __future__ import annotations

from datetime import timedelta
import random
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json
from ingestion.clean_schema import (
    CLEAN_COLUMNS,
    build_text_for_embedding,
    compute_age_days,
    format_date,
    parse_date,
)

#: Fixed seed so a corruption run is reproducible and diffable against its own log.
_CORRUPTION_SEED = 42

_DROP_LATEST_COUNT = 2
_BLANK_SUMMARY_COUNT = 2
_NOISE_COUNT = 2
_TRUNCATE_TITLE_COUNT = 2
_STALE_DATE_COUNT = 2
_DUPLICATE_COUNT = 2

_STALE_SHIFT_DAYS = 400
_TRUNCATE_TITLE_CHARS = 12
_NOISE_SUFFIX = " qxzjk noise7712 !!garbled!! asdkjh"


def _rebuild_derived(row: dict[str, Any]) -> None:
    """Recompute summary_chars/text_for_embedding after a row's fields change."""
    row["summary_chars"] = len(row["summary"])
    row["text_for_embedding"] = build_text_for_embedding(
        title=row["title"],
        summary=row["summary"],
        authors_joined=row["authors_joined"],
        categories_joined=row["categories_joined"],
        published=row["published"],
    )


def _apply_row(working: pd.DataFrame, paper_id: str, row_dict: dict[str, Any]) -> None:
    """Write a mutated row back column-by-column.

    ``working.loc[id, cols] = list(values)`` mis-broadcasts when a cell holds
    a list (``authors``/``categories``), so each column is set individually
    through ``.at`` instead of one bulk assignment.
    """
    for column, value in row_dict.items():
        working.at[paper_id, column] = value


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject controlled, logged corruption into a clean dataframe.

    Six independent corruption types run over disjoint rows (picked from a
    seeded shuffle so the run is reproducible): drop latest records, blank
    summary, noise summary, truncate title, stale publish date, duplicate
    rows. Every event is logged to ``output_log_path`` with record id, type,
    parameter and before/after so impact is auditable and repair (CP6) can be
    verified against it.
    """
    rng = random.Random(_CORRUPTION_SEED)
    run_date = now_utc()
    working = df.reset_index(drop=True).copy()
    row_count_before = int(len(working))

    events: dict[str, list[dict[str, Any]]] = {
        "drop_latest": [],
        "blank_summary": [],
        "noise_summary": [],
        "truncate_title": [],
        "stale_date": [],
        "duplicate_rows": [],
    }

    # 1. Drop the N most recently published records.
    drop_n = min(_DROP_LATEST_COUNT, len(working))
    latest_first = working.sort_values(["published", "paper_id"], ascending=[False, True])
    drop_ids = latest_first.head(drop_n)["paper_id"].tolist()
    for paper_id in drop_ids:
        row = working.loc[working["paper_id"] == paper_id].iloc[0]
        events["drop_latest"].append(
            {
                "paper_id": paper_id,
                "type": "drop_latest",
                "parameter": f"top_{drop_n}_by_published",
                "before": row["published"],
                "after": None,
            }
        )
    working = working[~working["paper_id"].isin(drop_ids)].reset_index(drop=True)

    # Disjoint row pools for the remaining corruption types so effects don't
    # overlap and stay attributable to a single cause.
    pool = working["paper_id"].tolist()
    rng.shuffle(pool)

    def take(n: int) -> list[str]:
        nonlocal pool
        chosen, pool = pool[:n], pool[n:]
        return chosen

    blank_ids = take(min(_BLANK_SUMMARY_COUNT, len(pool)))
    noise_ids = take(min(_NOISE_COUNT, len(pool)))
    truncate_ids = take(min(_TRUNCATE_TITLE_COUNT, len(pool)))
    stale_ids = take(min(_STALE_DATE_COUNT, len(pool)))
    duplicate_ids = take(min(_DUPLICATE_COUNT, len(pool)))

    working = working.set_index("paper_id", drop=False)

    # 2. Blank summary.
    for paper_id in blank_ids:
        row = working.loc[paper_id]
        before = row["summary"]
        row_dict = row.to_dict()
        row_dict["summary"] = ""
        _rebuild_derived(row_dict)
        _apply_row(working, paper_id, row_dict)
        events["blank_summary"].append(
            {
                "paper_id": paper_id,
                "type": "blank_summary",
                "parameter": "summary=''",
                "before": before,
                "after": "",
            }
        )

    # 3. Noise injected into summary text.
    for paper_id in noise_ids:
        row = working.loc[paper_id]
        before = row["summary"]
        row_dict = row.to_dict()
        row_dict["summary"] = (before + _NOISE_SUFFIX).strip()
        _rebuild_derived(row_dict)
        _apply_row(working, paper_id, row_dict)
        events["noise_summary"].append(
            {
                "paper_id": paper_id,
                "type": "noise_summary",
                "parameter": f"suffix={_NOISE_SUFFIX.strip()!r}",
                "before": before,
                "after": row_dict["summary"],
            }
        )

    # 4. Truncate title.
    for paper_id in truncate_ids:
        row = working.loc[paper_id]
        before = row["title"]
        row_dict = row.to_dict()
        row_dict["title"] = before[:_TRUNCATE_TITLE_CHARS].rstrip()
        _rebuild_derived(row_dict)
        _apply_row(working, paper_id, row_dict)
        events["truncate_title"].append(
            {
                "paper_id": paper_id,
                "type": "truncate_title",
                "parameter": f"max_chars={_TRUNCATE_TITLE_CHARS}",
                "before": before,
                "after": row_dict["title"],
            }
        )

    # 5. Make the publish date stale.
    for paper_id in stale_ids:
        row = working.loc[paper_id]
        before = row["published"]
        stale_date = parse_date(before) - timedelta(days=_STALE_SHIFT_DAYS)
        row_dict = row.to_dict()
        row_dict["published"] = format_date(stale_date)
        row_dict["age_days"] = compute_age_days(row_dict["published"], run_date)
        _rebuild_derived(row_dict)
        _apply_row(working, paper_id, row_dict)
        events["stale_date"].append(
            {
                "paper_id": paper_id,
                "type": "stale_date",
                "parameter": f"shift_days={_STALE_SHIFT_DAYS}",
                "before": before,
                "after": row_dict["published"],
            }
        )

    working = working.reset_index(drop=True)

    # 6. Duplicate rows (exact copy, same paper_id -> intentional uniqueness break).
    duplicate_rows = working[working["paper_id"].isin(duplicate_ids)]
    for paper_id in duplicate_ids:
        events["duplicate_rows"].append(
            {
                "paper_id": paper_id,
                "type": "duplicate_rows",
                "parameter": "exact_copy",
                "before": 1,
                "after": 2,
            }
        )
    working = pd.concat([working, duplicate_rows], ignore_index=True)

    working = working[list(CLEAN_COLUMNS)]
    row_count_after = int(len(working))

    log_payload = {
        "generated_at": run_date.isoformat(),
        "seed": _CORRUPTION_SEED,
        "row_count_before": row_count_before,
        "row_count_after": row_count_after,
        "counts": {key: len(value) for key, value in events.items()},
        "events": events,
    }
    write_json(output_log_path, log_payload)

    return working
