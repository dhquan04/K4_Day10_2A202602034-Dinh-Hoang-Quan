from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json
from ingestion.cleaning import write_clean_artifacts
from ingestion.corruption import corrupt_clean_dataframe


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


def main() -> None:
    handoff = prepare_corruption_handoff()
    print(
        "Corruption handoff PASS: "
        f"baseline={handoff['baseline_rows']} corrupted={handoff['corrupted_rows']} "
        f"artifact={handoff['corrupted_clean_artifact']}"
    )
