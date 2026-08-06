from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def _check(name: str, passed: bool, detail: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "check": name,
        "status": "pass" if passed else "fail",
        "detail": detail,
    }
    payload.update(extra)
    return payload


def _is_blank(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return not str(value).strip()


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run baseline data-quality checks and write a JSON report under ``data/quality/``."""
    checks: list[dict[str, Any]] = []
    row_count = int(len(df))

    checks.append(
        _check(
            "row_count",
            row_count > 0,
            f"{row_count} rows" if row_count > 0 else "dataset is empty",
            value=row_count,
            dimension="completeness",
        )
    )

    if "paper_id" in df.columns:
        null_ids = int(df["paper_id"].apply(_is_blank).sum())
        duplicate_ids = int(df["paper_id"].duplicated(keep=False).sum())
        unique_ids = int(df["paper_id"].nunique(dropna=False))
        checks.append(
            _check(
                "paper_id_not_null",
                null_ids == 0,
                f"{null_ids} null/blank paper_id values",
                value=null_ids,
                dimension="validity",
            )
        )
        checks.append(
            _check(
                "paper_id_unique",
                duplicate_ids == 0 and unique_ids == row_count,
                f"{duplicate_ids} duplicate rows across {unique_ids} unique ids",
                value=unique_ids,
                duplicate_rows=duplicate_ids,
                dimension="uniqueness",
            )
        )
    else:
        checks.append(_check("paper_id_not_null", False, "missing paper_id column", dimension="validity"))
        checks.append(_check("paper_id_unique", False, "missing paper_id column", dimension="uniqueness"))

    if "title" in df.columns:
        missing_titles = int(df["title"].apply(_is_blank).sum())
        checks.append(
            _check(
                "title_not_null",
                missing_titles == 0,
                f"{missing_titles} rows missing title",
                value=missing_titles,
                dimension="completeness",
            )
        )
    else:
        checks.append(_check("title_not_null", False, "missing title column", dimension="completeness"))

    if "summary" in df.columns:
        missing_summaries = int(df["summary"].apply(_is_blank).sum())
        short_summaries = int(df["summary"].fillna("").astype(str).str.len().lt(40).sum())
        checks.append(
            _check(
                "summary_not_null",
                missing_summaries == 0,
                f"{missing_summaries} rows missing summary",
                value=missing_summaries,
                dimension="completeness",
            )
        )
        checks.append(
            _check(
                "summary_min_length",
                short_summaries == 0,
                f"{short_summaries} summaries shorter than 40 characters",
                value=short_summaries,
                dimension="validity",
            )
        )
    else:
        checks.append(_check("summary_not_null", False, "missing summary column", dimension="completeness"))

    if "text_for_embedding" in df.columns:
        missing_embedding_text = int(df["text_for_embedding"].apply(_is_blank).sum())
        checks.append(
            _check(
                "text_for_embedding_present",
                missing_embedding_text == 0,
                f"{missing_embedding_text} rows missing text_for_embedding",
                value=missing_embedding_text,
                dimension="completeness",
            )
        )

    if "age_days" in df.columns:
        missing_age = int(df["age_days"].isna().sum())
        negative_age = int((pd.to_numeric(df["age_days"], errors="coerce") < 0).sum())
        checks.append(
            _check(
                "age_days_present",
                missing_age == 0,
                f"{missing_age} rows missing age_days",
                value=missing_age,
                dimension="freshness",
            )
        )
        checks.append(
            _check(
                "age_days_non_negative",
                negative_age == 0,
                f"{negative_age} rows with negative age_days",
                value=negative_age,
                dimension="freshness",
            )
        )

    passed = all(check["status"] == "pass" for check in checks)
    report: dict[str, Any] = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "row_count": row_count,
        "passed": passed,
        "checks": checks,
    }

    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize dataset freshness from ``published`` / ``age_days`` and write JSON."""
    total_rows = int(len(df))
    threshold = settings.freshness_threshold_days

    if total_rows == 0 or "published" not in df.columns:
        payload: dict[str, Any] = {
            "generated_at": now_utc().isoformat(),
            "freshness_threshold_days": threshold,
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": total_rows,
            "is_fresh": False,
            "mean_age_days": None,
            "max_age_days": None,
        }
        write_json(report_path, payload)
        return payload

    published_dates = pd.to_datetime(df["published"], errors="coerce")
    if "age_days" in df.columns:
        age_days = pd.to_numeric(df["age_days"], errors="coerce").fillna(0).astype(int)
    else:
        today = datetime.now(UTC).date()
        age_days = published_dates.apply(
            lambda value: max(0, (today - value.date()).days) if pd.notna(value) else 0
        )

    stale_rows = int((age_days > threshold).sum())
    latest_published = published_dates.max()
    oldest_published = published_dates.min()

    payload = {
        "generated_at": now_utc().isoformat(),
        "freshness_threshold_days": threshold,
        "latest_published": latest_published.date().isoformat() if pd.notna(latest_published) else None,
        "oldest_published": oldest_published.date().isoformat() if pd.notna(oldest_published) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": stale_rows == 0,
        "mean_age_days": round(float(age_days.mean()), 2),
        "max_age_days": int(age_days.max()),
    }
    write_json(report_path, payload)
    return payload
