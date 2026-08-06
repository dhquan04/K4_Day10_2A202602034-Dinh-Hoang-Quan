from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_csv, write_json
from ingestion.clean_schema import (
    CLEAN_COLUMNS,
    DEFAULT_PRIMARY_CATEGORY,
    build_text_for_embedding,
    compute_age_days,
    dedupe_records,
    drop_reason,
    empty_drop_log,
    format_date,
    normalize_authors,
    normalize_categories,
    normalize_paper_id,
    normalize_summary,
    normalize_title,
    parse_date,
)
from ingestion.crossref import PaperRecord


def _normalize_record(record: PaperRecord) -> dict[str, Any]:
    categories = normalize_categories(record.categories)
    published = format_date(parse_date(record.published))
    updated = format_date(parse_date(record.updated)) or published
    return {
        "paper_id": normalize_paper_id(record.paper_id),
        "title": normalize_title(record.title),
        "summary": normalize_summary(record.summary),
        "authors": normalize_authors(record.authors),
        "categories": categories,
        "primary_category": categories[0] if categories else DEFAULT_PRIMARY_CATEGORY,
        "published": published,
        "updated": updated,
        "abs_url": (record.abs_url or "").strip(),
        "pdf_url": (record.pdf_url or "").strip(),
        "comment": (record.comment or "").strip(),
    }


def _build_row(item: dict[str, Any], run_date: datetime) -> dict[str, Any]:
    authors_joined = ", ".join(item["authors"])
    categories_joined = ", ".join(item["categories"])
    summary = item["summary"]
    return {
        **item,
        "authors_joined": authors_joined,
        "categories_joined": categories_joined,
        "summary_chars": len(summary),
        "age_days": compute_age_days(item["published"], run_date),
        "text_for_embedding": build_text_for_embedding(
            title=item["title"],
            summary=summary,
            authors_joined=authors_joined,
            categories_joined=categories_joined,
            published=item["published"],
        ),
    }


def build_clean_dataframe(
    records: list[PaperRecord], run_date: datetime
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean raw records into an embedding-ready dataframe.

    Returns ``(clean_df, drop_log)``. ``drop_log`` counts every removed record
    by reason (see ``ingestion.clean_schema.DROP_REASONS``), so
    ``len(records) == len(clean_df) + sum(drop_log.values())`` always holds —
    no record disappears without a logged reason. Normalization/dedupe/date
    rules live in ``ingestion.clean_schema``; this function wires them
    together and builds the derived columns (``age_days``,
    ``text_for_embedding``, the ``*_joined`` helpers).
    """
    drop_log = empty_drop_log()
    normalized: list[dict[str, Any]] = []

    for record in records:
        candidate = _normalize_record(record)
        reason = drop_reason(candidate)
        if reason:
            drop_log[reason] += 1
            continue
        normalized.append(candidate)

    deduped, duplicate_count = dedupe_records(normalized)
    drop_log["duplicate_paper_id"] += duplicate_count

    rows = [_build_row(item, run_date) for item in deduped]
    df = pd.DataFrame(rows, columns=list(CLEAN_COLUMNS))
    if not df.empty:
        df = df.sort_values(
            ["published", "paper_id"], ascending=[False, True]
        ).reset_index(drop=True)
    return df, drop_log


def write_clean_artifacts(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Persist the clean dataframe as CSV and JSON, in contract column order."""
    ordered = df[list(CLEAN_COLUMNS)]
    write_csv(ordered, csv_path)
    write_json(json_path, ordered.to_dict(orient="records"))


def write_drop_log(drop_log: dict[str, int], path: Path) -> None:
    """Persist filter/dedupe counts so raw->clean loss is auditable.

    Consumed by ``script/validate_clean.py`` to check
    ``raw_count == clean_count + sum(drop_log.values())``.
    """
    write_json(path, drop_log)
