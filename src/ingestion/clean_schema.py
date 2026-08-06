"""Clean-layer contract for the Crossref RAG pipeline.

Single source of truth for:

- the column list, dtypes and null policy of ``data/clean/papers_clean.{csv,json}``
- normalization rules for title, summary, authors, categories and dates
- the derived fields ``age_days`` and ``text_for_embedding``
- the raw -> clean validation used by ``script/validate_clean.py``

``src/ingestion/cleaning.py`` builds its dataframe from these helpers so that the
index, test set and quality owners can rely on one contract instead of guessing
column names. Changing a rule here means changing it for the whole pipeline.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import html
import math
import re
from typing import Any, Iterable, Sequence

from core.utils import normalize_whitespace

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

#: Column order of the clean artifacts. CSV and JSON must use this exact order.
CLEAN_COLUMNS: tuple[str, ...] = (
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
)

#: Logical type of every clean column.
COLUMN_TYPES: dict[str, str] = {
    "paper_id": "str",
    "title": "str",
    "summary": "str",
    "authors": "list[str]",
    "categories": "list[str]",
    "primary_category": "str",
    "published": "str (ISO date, YYYY-MM-DD)",
    "updated": "str (ISO date, YYYY-MM-DD)",
    "abs_url": "str",
    "pdf_url": "str",
    "comment": "str",
    "authors_joined": "str",
    "categories_joined": "str",
    "summary_chars": "int",
    "age_days": "int",
    "text_for_embedding": "str",
}

#: Columns that must never be empty in a clean row. A raw record that cannot
#: produce them is dropped and logged instead of being written with a null.
REQUIRED_NON_EMPTY: tuple[str, ...] = (
    "paper_id",
    "title",
    "summary",
    "published",
    "text_for_embedding",
)

#: Columns consumed by ``LocalEmbeddingIndex._build_documents``.
INDEX_REQUIRED_COLUMNS: tuple[str, ...] = (
    "paper_id",
    "title",
    "text_for_embedding",
    "published",
    "authors_joined",
    "categories_joined",
    "summary",
    "abs_url",
    "pdf_url",
)

#: Columns that may legitimately be an empty string (never NaN).
OPTIONAL_TEXT_COLUMNS: tuple[str, ...] = (
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
)

MIN_TITLE_CHARS = 10
MIN_SUMMARY_CHARS = 40
MAX_SUMMARY_CHARS = 2000
MAX_AUTHORS = 25
MIN_CLEAN_ROWS = 10
DEFAULT_PRIMARY_CATEGORY = "uncategorized"

#: Every reason a raw record can be removed. Cleaning logs a count per reason so
#: raw_count == clean_count + sum(drop_counts) is auditable.
DROP_REASONS: tuple[str, ...] = (
    "missing_paper_id",
    "missing_title",
    "short_title",
    "missing_summary",
    "short_summary",
    "missing_published",
    "unparsable_published",
    "duplicate_paper_id",
)

TEXT_FOR_EMBEDDING_TEMPLATE = (
    "Title: {title}\n"
    "Authors: {authors_joined}\n"
    "Categories: {categories_joined}\n"
    "Published: {published}\n"
    "Summary: {summary}"
)

_TAG_PATTERN = re.compile(r"<[^>]+>")
_ABSTRACT_LABEL_PATTERN = re.compile(r"^\s*abstract[:.\s-]+", re.IGNORECASE)
_DOI_PREFIX_PATTERN = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _as_text(value: Any) -> str:
    """Coerce any raw value to a stripped string. None/NaN become ""."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def strip_markup(value: Any) -> str:
    """Remove JATS/HTML tags and entities that Crossref returns in abstracts."""
    text = _as_text(value)
    if not text:
        return ""
    text = _TAG_PATTERN.sub(" ", text)
    text = html.unescape(text)
    return normalize_whitespace(text)


def normalize_paper_id(value: Any) -> str:
    """Stable document identity: the bare DOI, lowercased.

    The same DOI must map to the same ``paper_id`` in raw, clean, index metadata
    and test set ground truth, so URL prefixes and casing are stripped.
    """
    text = normalize_whitespace(_as_text(value))
    text = _DOI_PREFIX_PATTERN.sub("", text)
    return text.strip().lower()


def normalize_title(value: Any) -> str:
    return strip_markup(value)


def normalize_summary(value: Any) -> str:
    """Clean an abstract and cap it at ``MAX_SUMMARY_CHARS``."""
    text = _ABSTRACT_LABEL_PATTERN.sub("", strip_markup(value))
    text = normalize_whitespace(text)
    if len(text) > MAX_SUMMARY_CHARS:
        text = text[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0].rstrip(",;:-") + " ..."
    return text


def normalize_authors(values: Any) -> list[str]:
    """Trim, drop empties, de-duplicate case-insensitively, cap at MAX_AUTHORS."""
    return _normalize_string_list(values, limit=MAX_AUTHORS)


def normalize_categories(values: Any) -> list[str]:
    return _normalize_string_list(values, limit=None)


def _normalize_string_list(values: Any, limit: int | None) -> list[str]:
    if values is None or isinstance(values, str):
        items: Iterable[Any] = [values] if values else []
    else:
        items = values
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items:
        text = strip_markup(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    if limit is not None:
        cleaned = cleaned[:limit]
    return cleaned


def parse_date(value: Any) -> date | None:
    """Parse the date shapes Crossref emits: date, ISO datetime, YYYY-MM, YYYY."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = normalize_whitespace(_as_text(value))
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for pattern, fmt in (
        (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
        (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),
        (r"^\d{4}-\d{2}$", "%Y-%m"),
        (r"^\d{4}$", "%Y"),
    ):
        if re.match(pattern, text):
            return datetime.strptime(text, fmt).date()
    return None


def format_date(value: date | None) -> str:
    return value.isoformat() if value else ""


def compute_age_days(published: Any, run_date: datetime) -> int:
    """Days between ``published`` and the pipeline run date.

    Freshness must come from the data, never from "today" as a fallback: a row
    without a parsable date is dropped upstream, not aged to 0. A future date
    (Crossref does publish them) is clamped to 0 and reported as a warning.
    """
    published_date = parse_date(published)
    if published_date is None:
        raise ValueError("age_days requires a parsable published date")
    reference = run_date.astimezone(timezone.utc).date() if run_date.tzinfo else run_date.date()
    return max(0, (reference - published_date).days)


def build_text_for_embedding(
    title: str,
    summary: str,
    authors_joined: str,
    categories_joined: str,
    published: str,
) -> str:
    """Text that MiniLM embeds.

    Metadata is inlined on purpose: the evaluation set asks author, date and
    category questions, so those tokens have to be inside the embedded document
    or retrieval can never hit them. Field labels stay fixed so a corrupted
    dataset can be diffed against baseline text line by line.
    """
    return TEXT_FOR_EMBEDDING_TEMPLATE.format(
        title=normalize_whitespace(title),
        authors_joined=authors_joined or "unknown",
        categories_joined=categories_joined or DEFAULT_PRIMARY_CATEGORY,
        published=published,
        summary=normalize_whitespace(summary),
    )


def drop_reason(record: dict[str, Any]) -> str | None:
    """Return the drop reason for a *normalized* record, or None if it is kept.

    ``record`` uses the normalized field names (``paper_id``, ``title``,
    ``summary``, ``published``). Duplicate detection is not done here because it
    needs the whole batch: see :func:`dedupe_records`.
    """
    if not record.get("paper_id"):
        return "missing_paper_id"
    title = record.get("title") or ""
    if not title:
        return "missing_title"
    if len(title) < MIN_TITLE_CHARS:
        return "short_title"
    summary = record.get("summary") or ""
    if not summary:
        return "missing_summary"
    if len(summary) < MIN_SUMMARY_CHARS:
        return "short_summary"
    published_raw = record.get("published")
    if not published_raw:
        return "missing_published"
    if parse_date(published_raw) is None:
        return "unparsable_published"
    return None


def dedupe_records(records: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Keep one row per ``paper_id``.

    Winner is the most recently updated record; ties break on the longest
    summary so a truncated duplicate never wins over the full one. Returns the
    kept records and the number dropped.
    """
    best: dict[str, dict[str, Any]] = {}
    dropped = 0
    for record in records:
        key = record["paper_id"]
        current = best.get(key)
        if current is None:
            best[key] = record
            continue
        dropped += 1
        if _dedupe_rank(record) > _dedupe_rank(current):
            best[key] = record
    return list(best.values()), dropped


def _dedupe_rank(record: dict[str, Any]) -> tuple[str, int]:
    return (_as_text(record.get("updated")), len(_as_text(record.get("summary"))))


def empty_drop_log() -> dict[str, int]:
    return {reason: 0 for reason in DROP_REASONS}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _check(name: str, ok: bool, detail: str, severity: str = "fail") -> dict[str, Any]:
    return {
        "check": name,
        "status": "pass" if ok else severity,
        "detail": detail,
    }


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def validate_clean_dataframe(
    df: Any,
    run_date: datetime,
    raw_count: int | None = None,
    drop_log: dict[str, int] | None = None,
    freshness_threshold_days: int | None = None,
) -> dict[str, Any]:
    """Validate a clean dataframe against this contract.

    Returns a report ``{"passed": bool, "row_count": int, "checks": [...]}``
    where every check is ``{"check", "status", "detail"}`` and status is one of
    ``pass`` / ``fail`` / ``warn``. Only ``fail`` flips ``passed``.
    """
    checks: list[dict[str, Any]] = []

    missing_columns = [column for column in CLEAN_COLUMNS if column not in df.columns]
    checks.append(
        _check(
            "columns_present",
            not missing_columns,
            "all contract columns present" if not missing_columns else f"missing: {missing_columns}",
        )
    )
    if missing_columns:
        return {"passed": False, "row_count": int(len(df)), "checks": checks}

    extra_columns = [column for column in df.columns if column not in CLEAN_COLUMNS]
    checks.append(
        _check(
            "no_undeclared_columns",
            not extra_columns,
            "no extra columns" if not extra_columns else f"undeclared: {extra_columns}",
            severity="warn",
        )
    )
    checks.append(
        _check(
            "column_order",
            list(df.columns)[: len(CLEAN_COLUMNS)] == list(CLEAN_COLUMNS),
            "column order matches CLEAN_COLUMNS",
            severity="warn",
        )
    )

    row_count = int(len(df))
    checks.append(_check("row_count_positive", row_count > 0, f"{row_count} clean rows"))
    checks.append(
        _check(
            "row_count_minimum",
            row_count >= MIN_CLEAN_ROWS,
            f"{row_count} rows (test set needs >= {MIN_CLEAN_ROWS})",
            severity="warn",
        )
    )
    if row_count == 0:
        return {"passed": False, "row_count": 0, "checks": checks}

    rows: list[dict[str, Any]] = df.to_dict(orient="records")

    duplicated = row_count - len({_as_text(row["paper_id"]) for row in rows})
    checks.append(_check("paper_id_unique", duplicated == 0, f"{duplicated} duplicate paper_id"))

    for column in REQUIRED_NON_EMPTY:
        bad = [row["paper_id"] for row in rows if not _as_text(row[column]).strip()]
        checks.append(
            _check(f"non_empty::{column}", not bad, f"{len(bad)} empty rows{_sample(bad)}")
        )

    null_columns = [
        column for column in CLEAN_COLUMNS if any(_is_missing(row[column]) for row in rows)
    ]
    checks.append(
        _check(
            "no_nulls",
            not null_columns,
            "no NaN/None in clean output" if not null_columns else f"nulls in: {null_columns}",
        )
    )

    list_type_bad = [
        row["paper_id"]
        for row in rows
        if not isinstance(row["authors"], list) or not isinstance(row["categories"], list)
    ]
    checks.append(
        _check(
            "list_columns_typed",
            not list_type_bad,
            f"{len(list_type_bad)} rows where authors/categories are not lists{_sample(list_type_bad)}",
        )
    )

    int_bad = [
        row["paper_id"]
        for row in rows
        if not _is_intlike(row["summary_chars"]) or not _is_intlike(row["age_days"])
    ]
    checks.append(
        _check(
            "int_columns_typed",
            not int_bad,
            f"{len(int_bad)} rows where summary_chars/age_days are not integers{_sample(int_bad)}",
        )
    )

    date_bad = [
        row["paper_id"]
        for row in rows
        if not _ISO_DATE_PATTERN.match(_as_text(row["published"]))
        or not _ISO_DATE_PATTERN.match(_as_text(row["updated"]))
    ]
    checks.append(
        _check(
            "dates_iso_format",
            not date_bad,
            f"{len(date_bad)} rows with non YYYY-MM-DD published/updated{_sample(date_bad)}",
        )
    )

    title_bad = [row["paper_id"] for row in rows if len(_as_text(row["title"])) < MIN_TITLE_CHARS]
    checks.append(
        _check(
            "title_min_length",
            not title_bad,
            f"{len(title_bad)} titles shorter than {MIN_TITLE_CHARS} chars{_sample(title_bad)}",
        )
    )

    summary_bad = [
        row["paper_id"] for row in rows if len(_as_text(row["summary"])) < MIN_SUMMARY_CHARS
    ]
    checks.append(
        _check(
            "summary_min_length",
            not summary_bad,
            f"{len(summary_bad)} summaries shorter than {MIN_SUMMARY_CHARS} chars{_sample(summary_bad)}",
        )
    )

    chars_bad = [
        row["paper_id"] for row in rows if int(row["summary_chars"]) != len(_as_text(row["summary"]))
    ]
    checks.append(
        _check(
            "summary_chars_consistent",
            not chars_bad,
            f"{len(chars_bad)} rows where summary_chars != len(summary){_sample(chars_bad)}",
        )
    )

    joined_bad = [
        row["paper_id"]
        for row in rows
        if _as_text(row["authors_joined"]) != ", ".join(row["authors"])
        or _as_text(row["categories_joined"]) != ", ".join(row["categories"])
    ]
    checks.append(
        _check(
            "joined_columns_consistent",
            not joined_bad,
            f"{len(joined_bad)} rows where *_joined does not match its list{_sample(joined_bad)}",
        )
    )

    age_bad: list[str] = []
    for row in rows:
        try:
            expected = compute_age_days(row["published"], run_date)
        except ValueError:
            age_bad.append(row["paper_id"])
            continue
        if int(row["age_days"]) != expected:
            age_bad.append(row["paper_id"])
    checks.append(
        _check(
            "age_days_consistent",
            not age_bad,
            f"{len(age_bad)} rows where age_days != run_date - published{_sample(age_bad)}",
        )
    )

    text_bad = [
        row["paper_id"]
        for row in rows
        if _as_text(row["text_for_embedding"])
        != build_text_for_embedding(
            title=_as_text(row["title"]),
            summary=_as_text(row["summary"]),
            authors_joined=_as_text(row["authors_joined"]),
            categories_joined=_as_text(row["categories_joined"]),
            published=_as_text(row["published"]),
        )
    ]
    checks.append(
        _check(
            "text_for_embedding_matches_template",
            not text_bad,
            f"{len(text_bad)} rows not rebuildable from the template{_sample(text_bad)}",
        )
    )

    primary_bad = [
        row["paper_id"]
        for row in rows
        if row["categories"] and _as_text(row["primary_category"]) not in row["categories"]
    ]
    checks.append(
        _check(
            "primary_category_in_categories",
            not primary_bad,
            f"{len(primary_bad)} rows where primary_category is not in categories{_sample(primary_bad)}",
            severity="warn",
        )
    )

    no_authors = [row["paper_id"] for row in rows if not row["authors"]]
    checks.append(
        _check(
            "authors_present",
            not no_authors,
            f"{len(no_authors)} rows without authors (author questions cannot use them){_sample(no_authors)}",
            severity="warn",
        )
    )

    if freshness_threshold_days is not None:
        stale = [row["paper_id"] for row in rows if int(row["age_days"]) > freshness_threshold_days]
        checks.append(
            _check(
                "freshness",
                not stale,
                f"{len(stale)}/{row_count} rows older than {freshness_threshold_days} days{_sample(stale)}",
                severity="warn",
            )
        )

    if raw_count is not None:
        dropped_total = sum((drop_log or {}).values())
        reconciled = raw_count == row_count + dropped_total
        checks.append(
            _check(
                "row_reconciliation",
                reconciled,
                f"raw={raw_count} clean={row_count} dropped={dropped_total} "
                f"({'balanced' if reconciled else 'records lost without a logged reason'})",
            )
        )
        unknown_reasons = [reason for reason in (drop_log or {}) if reason not in DROP_REASONS]
        checks.append(
            _check(
                "drop_reasons_declared",
                not unknown_reasons,
                "all drop reasons declared" if not unknown_reasons else f"undeclared: {unknown_reasons}",
                severity="warn",
            )
        )

    passed = all(check["status"] != "fail" for check in checks)
    return {"passed": passed, "row_count": row_count, "checks": checks}


def _is_intlike(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return not math.isnan(value) and float(value).is_integer()
    return False


def _sample(ids: Sequence[str], limit: int = 3) -> str:
    if not ids:
        return ""
    shown = list(ids)[:limit]
    suffix = ", ..." if len(ids) > limit else ""
    return f" e.g. {shown}{suffix}"


def format_validation_report(report: dict[str, Any]) -> str:
    """Render a validation report as plain text for the console or a log file."""
    lines = [f"clean rows: {report['row_count']}"]
    for check in report["checks"]:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[check["status"]]
        lines.append(f"[{marker}] {check['check']}: {check['detail']}")
    lines.append("RESULT: " + ("PASS" if report["passed"] else "FAIL"))
    return "\n".join(lines)
