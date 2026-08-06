"""CP0 deliverable (clean/data-model owner): raw -> clean validation runner.

Run this after `cleaning.py` produces `data/clean/papers_clean.{csv,json}` (CP1)
to check the output against the contract in `src/ingestion/clean_schema.py`:
null/duplicate/date rules, `text_for_embedding`, `age_days`.

Usage:
    uv run python script/validate_clean.py
    python script/validate_clean.py --clean-json data/clean/papers_clean_corrupted.json

Exit code is 0 on pass, 1 on fail, so it can be dropped into a pre-index check.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd  # noqa: E402

from core.config import load_settings  # noqa: E402
from core.utils import read_json  # noqa: E402
from ingestion.clean_schema import (  # noqa: E402
    CLEAN_COLUMNS,
    format_validation_report,
    validate_clean_dataframe,
)

# Convention for where cleaning.py should log per-reason drop counts. Not part
# of core.config.Paths (that file is a shared contract) -- if cleaning.py ends
# up writing the log somewhere else, pass --drop-log to point here at it.
DEFAULT_DROP_LOG_NAME = "clean_drop_log.json"


def _load_clean_dataframe(csv_path: Path, json_path: Path) -> pd.DataFrame:
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for column in ("authors", "categories"):
            if column in df.columns:
                df[column] = df[column].apply(_coerce_list_cell)
        return df
    if json_path.exists():
        return pd.DataFrame(read_json(json_path))
    raise FileNotFoundError(
        f"No clean artifact found at {csv_path} or {json_path}. "
        "Run the cleaning step (or script/run_phase1.py) before validating."
    )


def _coerce_list_cell(value):
    if isinstance(value, list):
        return value
    if isinstance(value, float):  # NaN
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            return json.loads(text.replace("'", '"'))
        except json.JSONDecodeError:
            pass
    return [item.strip() for item in text.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-csv", type=Path, default=None)
    parser.add_argument("--clean-json", type=Path, default=None)
    parser.add_argument("--drop-log", type=Path, default=None)
    parser.add_argument(
        "--run-date",
        type=str,
        default=None,
        help="ISO date to recompute age_days against (default: now UTC).",
    )
    args = parser.parse_args()

    settings = load_settings()
    clean_csv = args.clean_csv or settings.paths.clean_csv
    clean_json = args.clean_json or settings.paths.clean_json
    drop_log_path = args.drop_log or (settings.paths.quality_dir / DEFAULT_DROP_LOG_NAME)
    run_date = (
        datetime.fromisoformat(args.run_date).replace(tzinfo=timezone.utc)
        if args.run_date
        else datetime.now(timezone.utc)
    )

    print(f"clean columns expected: {list(CLEAN_COLUMNS)}")

    try:
        df = _load_clean_dataframe(clean_csv, clean_json)
    except FileNotFoundError as error:
        print(f"[SKIP] {error}")
        print("This is expected before CP1. Re-run once cleaning.py has written clean output.")
        return 0

    raw_count = None
    if settings.paths.raw_records_json.exists():
        raw_count = len(read_json(settings.paths.raw_records_json))
    else:
        print(f"[WARN] no raw snapshot at {settings.paths.raw_records_json}; "
              "skipping raw/clean row reconciliation.")

    drop_log = read_json(drop_log_path) if drop_log_path.exists() else None
    if drop_log is None:
        print(f"[WARN] no drop log at {drop_log_path}; "
              "cleaning.py should log a count per DROP_REASONS entry.")

    report = validate_clean_dataframe(
        df,
        run_date=run_date,
        raw_count=raw_count,
        drop_log=drop_log,
        freshness_threshold_days=settings.freshness_threshold_days,
    )
    print(format_validation_report(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
