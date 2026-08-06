"""Create CP1/CP2 evaluation, quality, freshness, and report artifacts without fetching a new source."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd  # noqa: E402

from core.config import load_settings  # noqa: E402
from core.utils import read_json  # noqa: E402
from evaluation.testset import build_test_set  # noqa: E402
from observability.quality import build_freshness_report, run_data_quality_checks  # noqa: E402
from observability.reporting import generate_phase1_report  # noqa: E402


REQUIRED_TEST_SET_FIELDS = {
    "id",
    "question_type",
    "question",
    "ground_truth",
    "ground_truth_doc_ids",
}


def main() -> int:
    settings = load_settings()
    clean_rows = read_json(settings.paths.clean_json)
    clean_df = pd.DataFrame(clean_rows)
    indexed_ids = {
        document["paper_id"]
        for document in read_json(settings.paths.embeddings_json)["documents"]
    }

    if not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)
    test_set = read_json(settings.paths.eval_testset)
    for item in test_set:
        if not REQUIRED_TEST_SET_FIELDS <= set(item):
            raise ValueError(f"Invalid test-set item: {item.get('id', '<missing id>')}")
        if not set(item["ground_truth_doc_ids"]) <= indexed_ids:
            raise ValueError(f"Test-set ID absent from baseline index: {item['id']}")

    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    source_path = settings.paths.raw_api_response
    fetched_at = datetime.fromtimestamp(source_path.stat().st_mtime, UTC).isoformat()
    generate_phase1_report(
        settings.paths.baseline_report,
        {
            "source": settings.source_api,
            "query": settings.source_query,
            "filter": settings.source_filter,
            "raw_records": len(read_json(settings.paths.raw_records_json)),
            "clean_records": len(clean_df),
            "fetched_at": fetched_at,
        },
        metrics={},
        quality=quality,
        freshness=freshness,
    )
    print(f"test set: {settings.paths.eval_testset} ({len(test_set)} questions)")
    print(f"quality: {settings.paths.quality_dir / 'baseline_quality.json'} (pass={quality['passed']})")
    print(f"freshness: {settings.paths.freshness_report} (fresh={freshness['is_fresh']})")
    print(f"report scaffold: {settings.paths.baseline_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
