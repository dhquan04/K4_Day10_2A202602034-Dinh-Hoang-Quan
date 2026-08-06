"""Baseline raw-to-report pipeline used at checkpoint 3."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import traceback

from core.config import load_settings
from core.utils import read_json, write_json, write_text
from evaluation import (
    build_test_set,
    evaluate_pipeline,
    load_indexed_paper_ids,
    validate_test_set_against_index,
)
from ingestion.clean_schema import validate_clean_dataframe
from ingestion.cleaning import build_clean_dataframe, write_clean_artifacts, write_drop_log
from ingestion.crossref import fetch_source_records
from observability import (
    audit_embedding_manifest,
    build_freshness_report,
    freeze_baseline_signals,
    generate_phase1_report,
    run_data_quality_checks,
)
from retrieval.index import LocalEmbeddingIndex


def _source_summary(settings, raw_count: int, clean_count: int) -> dict[str, object]:
    raw_path = settings.paths.raw_api_response
    fetched_at = None
    if raw_path.exists():
        fetched_at = datetime.fromtimestamp(raw_path.stat().st_mtime, tz=UTC).isoformat()
    return {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": raw_count,
        "clean_records": clean_count,
        "fetched_at": fetched_at,
    }


def _load_or_build_test_set(settings, clean_df):
    indexed_paper_ids = load_indexed_paper_ids(settings.paths.embeddings_json)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        return build_test_set(
            clean_df,
            settings.paths.eval_testset,
            indexed_paper_ids=indexed_paper_ids,
        )

    test_set = read_json(settings.paths.eval_testset)
    missing_ids = validate_test_set_against_index(test_set, indexed_paper_ids)
    if missing_ids:
        raise ValueError(
            "Existing test set references document IDs missing from the baseline index: "
            f"{missing_ids}. Set REFRESH_TEST_SET=true to rebuild it."
        )
    return test_set


def _verify_baseline_artifacts(settings) -> None:
    required = {
        "test set": settings.paths.eval_testset,
        "embedding manifest": settings.paths.embeddings_json,
        "baseline metrics": settings.paths.baseline_metrics,
        "baseline answers": settings.paths.baseline_answers,
        "quality report": settings.paths.quality_dir / "baseline_quality.json",
        "freshness report": settings.paths.freshness_report,
        "phase-1 report": settings.paths.baseline_report,
    }
    missing = [f"{name}: {path}" for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError("Baseline artifacts missing after pipeline run: " + "; ".join(missing))

    metrics = read_json(settings.paths.baseline_metrics)
    answers = read_json(settings.paths.baseline_answers)
    if metrics.get("samples") != len(answers):
        raise AssertionError(
            "Baseline metrics and answers disagree: "
            f"samples={metrics.get('samples')}, answers={len(answers)}"
        )


def run_baseline() -> dict[str, object]:
    """Run the reproducible baseline without refreshing the source by default."""
    settings = load_settings()
    records = fetch_source_records(settings)
    run_date = datetime.now(UTC)
    clean_df, drop_log = build_clean_dataframe(records, run_date)
    write_clean_artifacts(clean_df, settings.paths.clean_csv, settings.paths.clean_json)
    write_drop_log(drop_log, settings.paths.quality_dir / "clean_drop_log.json")

    clean_validation = validate_clean_dataframe(
        clean_df,
        run_date=run_date,
        raw_count=len(records),
        drop_log=drop_log,
        freshness_threshold_days=settings.freshness_threshold_days,
    )
    if not clean_validation["passed"]:
        raise ValueError(f"Clean contract validation failed: {clean_validation['checks']}")

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    test_set = _load_or_build_test_set(settings, clean_df)
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    embedding_audit = audit_embedding_manifest(
        settings,
        clean_row_count=len(clean_df),
    )
    freeze_baseline_signals(settings, quality, freshness, embedding_audit)
    generate_phase1_report(
        settings.paths.baseline_report,
        _source_summary(settings, len(records), len(clean_df)),
        # Read the written artifact so the report is tied to the same metrics
        # JSON that CP3 reviewers inspect, rather than an in-memory copy.
        read_json(settings.paths.baseline_metrics),
        quality,
        freshness,
    )
    _verify_baseline_artifacts(settings)
    return {
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "test_set_rows": len(test_set),
        "collection": index.collection_name,
        "metrics": evaluation.summary,
    }


def main() -> None:
    """Run CP3 baseline and retain a traceback artifact if any stage fails."""
    settings = load_settings()
    failure_path = settings.paths.project_dir / "data" / "results" / "phase1_failure_traceback.txt"
    try:
        result = run_baseline()
    except Exception:
        write_text(failure_path, traceback.format_exc())
        raise
    else:
        if failure_path.exists():
            failure_path.unlink()
        write_json(settings.paths.project_dir / "data" / "results" / "phase1_run_summary.json", result)
        print(
            "Baseline PASS: "
            f"raw={result['raw_records']} clean={result['clean_records']} "
            f"test_set={result['test_set_rows']} collection={result['collection']}"
        )
