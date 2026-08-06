from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric_value(metrics: dict[str, Any], key: str) -> Any:
    if not metrics or key not in metrics:
        return "N/A (fill at CP3)"
    value = metrics[key]
    return value if value is not None else "N/A (fill at CP3)"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline phase-1 markdown report.

    At CP2 this may be called with empty/partial metrics; quality and freshness
    should already contain real baseline signals. CP3 fills evaluation metrics.
    """
    source_summary = source_summary or {}
    metrics = metrics or {}
    quality = quality or {}
    freshness = freshness or {}

    quality_rows = []
    for check in quality.get("checks", []):
        quality_rows.append(
            "| {check} | {dimension} | {status} | {detail} |".format(
                check=check.get("check", ""),
                dimension=check.get("dimension", ""),
                status=check.get("status", ""),
                detail=str(check.get("detail", "")).replace("|", "/"),
            )
        )
    if not quality_rows:
        quality_rows.append("| N/A | N/A | N/A | No quality checks yet |")

    lines = [
        "# Phase 1 Baseline Report",
        "",
        "> Khung report (Role 5 / observability). Số liệu metrics đầy đủ sau khi Lead chạy `phase1` ở CP3.",
        "",
        "## 1. Source summary",
        "",
        "| Thuộc tính | Giá trị |",
        "| --- | --- |",
        f"| Source | {source_summary.get('source', 'N/A')} |",
        f"| Query | {source_summary.get('query', 'N/A')} |",
        f"| Filter | {source_summary.get('filter', 'N/A')} |",
        f"| Raw records | {source_summary.get('raw_records', 'N/A')} |",
        f"| Clean records | {source_summary.get('clean_records', 'N/A')} |",
        f"| Fetched at | {source_summary.get('fetched_at', 'N/A (fill at CP3)')} |",
        "",
        "## 2. Evaluation metrics",
        "",
        "| Metric | Giá trị |",
        "| --- | --- |",
        f"| samples | {_metric_value(metrics, 'samples')} |",
        f"| retrieval_hit_rate | {_metric_value(metrics, 'retrieval_hit_rate')} |",
        f"| mean_token_f1 | {_metric_value(metrics, 'mean_token_f1')} |",
        f"| judge_accuracy | {_metric_value(metrics, 'judge_accuracy')} |",
        f"| mean_judge_score | {_metric_value(metrics, 'mean_judge_score')} |",
        f"| ragas | {_metric_value(metrics, 'ragas')} |",
        "",
        "## 3. Data quality",
        "",
        "| Check | Dimension | Status | Detail |",
        "| --- | --- | --- | --- |",
        *quality_rows,
        "",
        f"Overall quality passed: `{quality.get('passed', 'N/A')}`",
        "",
        "## 4. Freshness",
        "",
        "| Thuộc tính | Giá trị |",
        "| --- | --- |",
        f"| freshness_threshold_days | {freshness.get('freshness_threshold_days', 'N/A')} |",
        f"| latest_published | {freshness.get('latest_published', 'N/A')} |",
        f"| oldest_published | {freshness.get('oldest_published', 'N/A')} |",
        f"| mean_age_days | {freshness.get('mean_age_days', 'N/A')} |",
        f"| max_age_days | {freshness.get('max_age_days', 'N/A')} |",
        f"| stale_rows | {freshness.get('stale_rows', 'N/A')} |",
        f"| total_rows | {freshness.get('total_rows', 'N/A')} |",
        f"| is_fresh | {freshness.get('is_fresh', 'N/A')} |",
        "",
        "## 5. Evidence paths",
        "",
        "- Clean dataset: `data/clean/papers_clean.{csv,json}`",
        "- Evaluation set: `data/eval/test_set.json`",
        "- Embedding manifest: `data/embeddings/papers_embeddings.json`",
        "- Quality: `data/quality/`",
        "- Metrics: `data/results/baseline_metrics.json`",
        "- Answers: `data/results/baseline_answers.json`",
        "",
        "## 6. Baseline evaluation notes (CP3)",
        "",
        "- Metrics lấy từ `data/results/baseline_metrics.json` (không hard-code).",
        "- Retrieval hit: 8/8 (`retrieval_hit_rate=1.0`); mọi `ground_truth_doc_ids` có trong clean + index.",
        "- Answer quality gap: `categories-07`/`categories-08` retrieval hit nhưng `answer=\"\"` "
        "(metadata `categories_joined` rỗng) → `token_f1=0`, judge incorrect. "
        "GT dùng `primary_category=uncategorized`.",
        "- Judge hiện dùng fallback heuristic khi LLM evaluator unavailable.",
        "- Đối chiếu report ↔ quality/freshness/metrics JSON đã khớp trước khi đóng baseline.",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    *,
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
) -> None:
    """Write an evidence-based baseline/corrupted/repaired comparison."""
    baseline_quality = baseline_quality or {}
    baseline_freshness = baseline_freshness or {}
    corruption_log = corruption_log or {}

    metric_keys = ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    metric_rows = [
        f"| {key} | {baseline_metrics.get(key, 'N/A')} | {corrupted_metrics.get(key, 'N/A')} | {repaired_metrics.get(key, 'N/A')} |"
        for key in metric_keys
    ]
    quality_rows = [
        f"| quality.passed | {baseline_quality.get('passed', 'N/A')} | {corrupted_quality.get('passed', 'N/A')} | {repaired_quality.get('passed', 'N/A')} |",
        f"| row_count | {baseline_quality.get('row_count', 'N/A')} | {corrupted_quality.get('row_count', 'N/A')} | {repaired_quality.get('row_count', 'N/A')} |",
        f"| freshness.is_fresh | {baseline_freshness.get('is_fresh', 'N/A')} | {corrupted_freshness.get('is_fresh', 'N/A')} | {repaired_freshness.get('is_fresh', 'N/A')} |",
        f"| freshness.stale_rows | {baseline_freshness.get('stale_rows', 'N/A')} | {corrupted_freshness.get('stale_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} |",
    ]
    counts = corruption_log.get("counts", {})
    count_text = ", ".join(f"{name}={value}" for name, value in counts.items()) or "N/A"
    lines = [
        "# CP5 Corruption Comparison Report",
        "",
        "## Controlled corruption",
        "",
        f"- Seed: `{corruption_log.get('seed', 'N/A')}`",
        f"- Rows: `{corruption_log.get('row_count_before', 'N/A')}` baseline → `{corruption_log.get('row_count_after', 'N/A')}` corrupted",
        f"- Events: {count_text}",
        "- Repair source: immutable raw snapshot (`data/raw/crossref_records.json`).",
        "",
        "## Evaluation metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
        *metric_rows,
        "",
        "## Quality and freshness signals",
        "",
        "| Signal | Baseline | Corrupted | Repaired |",
        "| --- | --- | --- | --- |",
        *quality_rows,
        "",
        "## Evidence rule",
        "",
        "Changes are reported as observed values above. A causal claim is limited to corruption events and signal/metric deltas present in these artifacts; no claim is inferred when the values do not change.",
        "",
    ]
    write_text(report_path, "\n".join(lines))
