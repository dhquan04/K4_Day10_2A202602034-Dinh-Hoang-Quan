from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, read_json, write_json


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


def audit_embedding_manifest(
    settings: Settings,
    report_name: str = "embedding_audit_baseline",
    expected_collection_name: str | None = None,
    clean_row_count: int | None = None,
) -> dict[str, Any]:
    """Audit embedding manifest collection name and document counts for CP2 handoff."""
    manifest_path = Path(settings.paths.embeddings_json)
    expected_collection = expected_collection_name or settings.baseline_collection_name
    checks: list[dict[str, Any]] = []

    if not manifest_path.exists():
        report = {
            "report_name": report_name,
            "generated_at": now_utc().isoformat(),
            "manifest_path": str(manifest_path),
            "collection_name": None,
            "embedding_model": None,
            "backend": None,
            "document_count": 0,
            "unique_paper_ids": 0,
            "passed": False,
            "checks": [
                _check(
                    "manifest_exists",
                    False,
                    f"missing manifest at {manifest_path}",
                    dimension="availability",
                )
            ],
        }
        write_json(settings.paths.quality_dir / f"{report_name}.json", report)
        return report

    payload = read_json(manifest_path)
    documents = payload.get("documents") or []
    paper_ids = [str(doc.get("paper_id", "")).strip() for doc in documents]
    unique_paper_ids = len({paper_id for paper_id in paper_ids if paper_id})
    document_count = len(documents)
    collection_name = payload.get("collection_name")
    embedding_model = payload.get("embedding_model")
    backend = payload.get("backend")

    checks.append(
        _check(
            "manifest_exists",
            True,
            f"found manifest at {manifest_path}",
            dimension="availability",
        )
    )
    checks.append(
        _check(
            "collection_name",
            collection_name == expected_collection,
            f"collection_name={collection_name!r}, expected={expected_collection!r}",
            value=collection_name,
            expected=expected_collection,
            dimension="validity",
        )
    )
    checks.append(
        _check(
            "embedding_model_present",
            bool(embedding_model),
            str(embedding_model) if embedding_model else "missing embedding_model",
            value=embedding_model,
            dimension="completeness",
        )
    )
    checks.append(
        _check(
            "backend_present",
            bool(backend),
            str(backend) if backend else "missing backend",
            value=backend,
            dimension="completeness",
        )
    )
    checks.append(
        _check(
            "document_count_positive",
            document_count > 0,
            f"{document_count} documents",
            value=document_count,
            dimension="completeness",
        )
    )
    checks.append(
        _check(
            "paper_id_unique_in_manifest",
            unique_paper_ids == document_count and document_count > 0,
            f"{unique_paper_ids} unique paper_id across {document_count} documents",
            value=unique_paper_ids,
            dimension="uniqueness",
        )
    )
    if clean_row_count is not None:
        checks.append(
            _check(
                "document_count_matches_clean",
                document_count == clean_row_count,
                f"manifest={document_count}, clean={clean_row_count}",
                value=document_count,
                expected=clean_row_count,
                dimension="consistency",
            )
        )

    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "manifest_path": str(manifest_path),
        "collection_name": collection_name,
        "embedding_model": embedding_model,
        "backend": backend,
        "document_count": document_count,
        "unique_paper_ids": unique_paper_ids,
        "passed": all(check["status"] == "pass" for check in checks),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", report)
    return report


def freeze_baseline_signals(
    settings: Settings,
    quality: dict[str, Any],
    freshness: dict[str, Any],
    embedding_audit: dict[str, Any] | None = None,
    output_name: str = "baseline_signals.json",
) -> dict[str, Any]:
    """Freeze baseline quality/freshness signals for post-corruption comparison."""
    payload: dict[str, Any] = {
        "generated_at": now_utc().isoformat(),
        "purpose": "Baseline signals frozen at CP2 for post-corruption comparison.",
        "quality": {
            "report_name": quality.get("report_name"),
            "passed": quality.get("passed"),
            "row_count": quality.get("row_count"),
            "checks": [
                {
                    "check": item.get("check"),
                    "status": item.get("status"),
                    "value": item.get("value"),
                    "detail": item.get("detail"),
                }
                for item in quality.get("checks", [])
            ],
        },
        "freshness": {
            "is_fresh": freshness.get("is_fresh"),
            "stale_rows": freshness.get("stale_rows"),
            "total_rows": freshness.get("total_rows"),
            "freshness_threshold_days": freshness.get("freshness_threshold_days"),
            "latest_published": freshness.get("latest_published"),
            "oldest_published": freshness.get("oldest_published"),
            "mean_age_days": freshness.get("mean_age_days"),
            "max_age_days": freshness.get("max_age_days"),
        },
    }
    if embedding_audit is not None:
        payload["embedding_audit"] = embedding_audit
    write_json(settings.paths.quality_dir / output_name, payload)
    return payload
