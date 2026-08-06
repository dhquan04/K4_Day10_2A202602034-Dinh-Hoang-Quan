from __future__ import annotations

from datetime import UTC, datetime
import hashlib

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe, write_clean_artifacts
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import restore_from_raw_snapshot
from observability import build_freshness_report, generate_corruption_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def _require_baseline_artifacts(settings) -> None:
    """Prevent a corruption run from overwriting or preceding the baseline."""
    required = {
        "clean dataset": settings.paths.clean_json,
        "embedding manifest": settings.paths.embeddings_json,
        "baseline metrics": settings.paths.baseline_metrics,
        "baseline answers": settings.paths.baseline_answers,
        "baseline freshness": settings.paths.freshness_report,
        "phase-1 report": settings.paths.baseline_report,
    }
    missing = [f"{name}: {path}" for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Run and verify the CP3 baseline before corruption: " + "; ".join(missing)
        )


def prepare_corruption_handoff() -> dict[str, object]:
    """Create the controlled corrupted-data handoff for the CP5 owners.

    This is deliberately limited to Role 3/Role 1's handoff: baseline clean
    data becomes a separately persisted corrupted dataset and every change is
    recorded.  Role 4 then builds ``papers-corrupted`` from this exact input;
    Role 5 evaluates it using the already frozen test set.
    """
    settings = load_settings()
    _require_baseline_artifacts(settings)

    baseline_rows = read_json(settings.paths.clean_json)
    baseline_df = pd.DataFrame(baseline_rows)
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_clean_artifacts(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )

    corruption_log = read_json(settings.paths.corruption_log)
    handoff_path = settings.paths.project_dir / "data" / "results" / "corruption_handoff.json"
    handoff = {
        "checkpoint": 5,
        "status": "ready_for_role4",
        "baseline_clean_artifact": str(settings.paths.clean_json.relative_to(settings.paths.project_dir)),
        "corrupted_clean_artifact": str(
            settings.paths.corrupted_clean_json.relative_to(settings.paths.project_dir)
        ),
        "corruption_log": str(settings.paths.corruption_log.relative_to(settings.paths.project_dir)),
        "baseline_rows": len(baseline_df),
        "corrupted_rows": len(corrupted_df),
        "corruption_counts": corruption_log["counts"],
        "next_owner": "Role 4: build papers-corrupted from this artifact.",
    }
    write_json(handoff_path, handoff)
    return handoff


def _file_hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _baseline_snapshot(settings) -> dict[str, str]:
    """Fingerprint immutable baseline evidence before CP5 writes its own artifacts."""
    paths = {
        "raw_records": settings.paths.raw_records_json,
        "clean": settings.paths.clean_json,
        "test_set": settings.paths.eval_testset,
        "manifest": settings.paths.embeddings_json,
        "metrics": settings.paths.baseline_metrics,
        "answers": settings.paths.baseline_answers,
        "quality": settings.paths.quality_dir / "baseline_quality.json",
        "freshness": settings.paths.freshness_report,
        "signals": settings.paths.quality_dir / "baseline_signals.json",
    }
    return {name: _file_hash(path) for name, path in paths.items()}


def _assert_baseline_unchanged(settings, before: dict[str, str], baseline_document_count: int) -> None:
    after = _baseline_snapshot(settings)
    changed = [name for name, digest in before.items() if after[name] != digest]
    if changed:
        raise AssertionError(f"CP5 mutated immutable baseline artifacts: {changed}")
    baseline_index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    if baseline_index.collection.count() != baseline_document_count:
        raise AssertionError("CP5 changed papers-baseline document count.")


def run_corruption_flow() -> dict[str, object]:
    """Run CP5 end-to-end without rewriting any baseline artifact or collection."""
    settings = load_settings()
    _require_baseline_artifacts(settings)
    snapshot = _baseline_snapshot(settings)
    baseline_index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    baseline_document_count = baseline_index.collection.count()
    if baseline_document_count <= 0:
        raise AssertionError("papers-baseline is empty; cannot start CP5 comparison.")

    handoff = prepare_corruption_handoff()
    corrupted_df = pd.DataFrame(read_json(settings.paths.corrupted_clean_json))
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
        allow_intentional_corruption=True,
    )
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )

    # Repair always reconstructs from the frozen raw snapshot; it never copies
    # the corrupted dataframe and never refreshes the external source.
    raw_records = restore_from_raw_snapshot(settings)
    repaired_df, _ = build_clean_dataframe(raw_records, datetime.now(UTC))
    write_clean_artifacts(repaired_df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings=settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=read_json(settings.paths.baseline_metrics),
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=read_json(settings.paths.quality_dir / "baseline_quality.json"),
        baseline_freshness=read_json(settings.paths.freshness_report),
        corruption_log=read_json(settings.paths.corruption_log),
    )
    _assert_baseline_unchanged(settings, snapshot, baseline_document_count)
    return {
        **handoff,
        "status": "complete",
        "corrupted_collection": corrupted_index.collection_name,
        "repaired_collection": repaired_index.collection_name,
        "baseline_collection_documents": baseline_document_count,
        "corrupted_metrics": corrupted_evaluation.summary,
        "repaired_metrics": repaired_evaluation.summary,
        "comparison_report": str(settings.paths.comparison_report.relative_to(settings.paths.project_dir)),
    }


def main() -> None:
    handoff = run_corruption_flow()
    print(
        "Corruption flow PASS: "
        f"baseline={handoff['baseline_rows']} corrupted={handoff['corrupted_rows']} "
        f"artifact={handoff['corrupted_clean_artifact']}"
    )
