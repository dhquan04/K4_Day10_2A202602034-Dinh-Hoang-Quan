from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import time
from typing import Any

import requests

_src_dir = str(Path(__file__).resolve().parents[1])
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from core.config import Settings, load_settings
from core.utils import normalize_whitespace, read_json, write_json



@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw_abstract: str) -> str:
    if not raw_abstract:
        return ""
    # Strip XML/HTML tags (e.g., <jats:p>, </jats:p>, <p>, etc.)
    text = re.sub(r"<[^>]+>", "", raw_abstract)
    return normalize_whitespace(text)


def _format_date(date_dict: dict[str, Any] | None) -> str:
    if not date_dict or not isinstance(date_dict, dict):
        return ""
    date_parts = date_dict.get("date-parts")
    if date_parts and isinstance(date_parts, list) and len(date_parts) > 0:
        parts = date_parts[0]
        if parts and len(parts) >= 1:
            year = parts[0]
            month = parts[1] if len(parts) >= 2 else 1
            day = parts[2] if len(parts) >= 3 else 1
            return f"{year:04d}-{month:02d}-{day:02d}"
    date_time = date_dict.get("date-time")
    if date_time:
        return str(date_time).split("T")[0]
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord objects.

    Uses DOI as the stable paper_id.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = str(item.get("DOI", "")).strip()
        if not doi:
            # Fallback to URL or skip if missing
            url = str(item.get("URL", "")).strip()
            if url:
                paper_id = url
            else:
                continue
        else:
            paper_id = doi

        # Title
        titles = item.get("title", [])
        title = normalize_whitespace(titles[0]) if titles and len(titles) > 0 else ""
        if not title:
            continue

        # Summary / Abstract
        summary = _clean_abstract(item.get("abstract", ""))

        # Authors
        authors: list[str] = []
        raw_authors = item.get("author", [])
        if isinstance(raw_authors, list):
            for auth in raw_authors:
                if not isinstance(auth, dict):
                    continue
                given = auth.get("given", "").strip()
                family = auth.get("family", "").strip()
                name = auth.get("name", "").strip()
                if given and family:
                    authors.append(normalize_whitespace(f"{given} {family}"))
                elif family:
                    authors.append(normalize_whitespace(family))
                elif given:
                    authors.append(normalize_whitespace(given))
                elif name:
                    authors.append(normalize_whitespace(name))

        # Categories
        categories: list[str] = []
        subjects = item.get("subject", [])
        if isinstance(subjects, list):
            categories = [normalize_whitespace(str(s)) for s in subjects if s]
        primary_category = categories[0] if categories else ""

        # Dates
        pub_online = _format_date(item.get("published-online"))
        pub_print = _format_date(item.get("published-print"))
        issued = _format_date(item.get("issued"))
        created = _format_date(item.get("created"))

        published = pub_online or pub_print or issued or created or ""
        updated = created or published or ""

        # URLs
        abs_url = str(item.get("URL", "")).strip() or f"https://doi.org/{paper_id}"

        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict):
                    content_type = str(link.get("content-type", "")).lower()
                    url_val = str(link.get("URL", "")).strip()
                    if "pdf" in content_type or url_val.lower().endswith(".pdf"):
                        pdf_url = url_val
                        break

        comment = f"publisher: {item.get('publisher', '')}" if item.get("publisher") else ""

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref source API with retry logic, save raw response, and parse records."""
    if not settings.refresh_source and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    endpoint = (
        settings.source_api
        if settings.source_api.startswith("http")
        else "https://api.crossref.org/works"
    )
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    headers = {
        "User-Agent": "DataPipelineLab/1.0 (mailto:student@lab.org)"
    }

    max_retries = 5
    payload: dict[str, Any] | None = None

    for attempt in range(max_retries):
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                payload = response.json()
                break
            elif response.status_code in {429, 500, 502, 503, 504}:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait_sec = int(retry_after)
                else:
                    wait_sec = (2 ** attempt) + 0.5
                time.sleep(wait_sec)
            else:
                response.raise_for_status()
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to fetch Crossref data after {max_retries} attempts: {e}") from e
            time.sleep((2 ** attempt) + 0.5)

    if payload is None:
        raise RuntimeError("Failed to fetch payload from Crossref API.")

    # Save raw API response before parse
    write_json(settings.paths.raw_api_response, payload)

    # Parse payload
    records = parse_crossref_payload(payload)

    # Save parsed records to raw_records_json
    raw_dicts = [dataclasses.asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, raw_dicts)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map into list[PaperRecord]."""
    data = read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}, got {type(data)}")
    
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=str(item["paper_id"]),
                title=str(item["title"]),
                summary=str(item["summary"]),
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=str(item.get("primary_category", "")),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records


def inspect_raw_lineage(records: list[PaperRecord]) -> dict[str, Any]:
    """Inspect and audit raw record snapshot for CP1 lineage and handoff."""
    total = len(records)
    unique_ids = len(set(r.paper_id for r in records))
    missing_summary = sum(1 for r in records if not r.summary.strip())
    missing_title = sum(1 for r in records if not r.title.strip())
    missing_published = sum(1 for r in records if not r.published.strip())
    missing_authors = sum(1 for r in records if not r.authors)

    return {
        "total_records": total,
        "unique_ids": unique_ids,
        "has_duplicates": total != unique_ids,
        "missing_summary_count": missing_summary,
        "missing_title_count": missing_title,
        "missing_published_count": missing_published,
        "missing_authors_count": missing_authors,
        "sample_paper_id": records[0].paper_id if records else None,
        "sample_title": records[0].title if records else None,
        "sample_authors": records[0].authors if records else [],
        "sample_published": records[0].published if records else None,
    }


def trace_paper_lineage(paper_id: str, settings: Settings) -> dict[str, Any]:
    """Trace a single paper_id across raw -> clean -> index stages for CP2 verification."""
    target_id = paper_id.strip().lower()

    # 1. Raw stage
    raw_record = None
    if settings.paths.raw_records_json.exists():
        raw_list = read_json(settings.paths.raw_records_json)
        for item in raw_list:
            if str(item.get("paper_id", "")).strip().lower() == target_id:
                raw_record = item
                break

    # 2. Clean stage
    clean_record = None
    if settings.paths.clean_json.exists():
        clean_list = read_json(settings.paths.clean_json)
        for item in clean_list:
            if str(item.get("paper_id", "")).strip().lower() == target_id:
                clean_record = item
                break

    # 3. Index stage
    index_record = None
    if settings.paths.embeddings_json.exists():
        emb_manifest = read_json(settings.paths.embeddings_json)
        docs = emb_manifest.get("documents", [])
        for doc in docs:
            if str(doc.get("paper_id", "")).strip().lower() == target_id:
                index_record = doc
                break

    in_raw = raw_record is not None
    in_clean = clean_record is not None
    in_index = index_record is not None

    return {
        "paper_id": paper_id,
        "in_raw": in_raw,
        "in_clean": in_clean,
        "in_index": in_index,
        "lineage_intact": (in_raw and in_clean and in_index),
        "raw_title": raw_record.get("title") if raw_record else None,
        "clean_title": clean_record.get("title") if clean_record else None,
        "index_title": index_record.get("title") if index_record else None,
        "raw_authors": raw_record.get("authors") if raw_record else None,
        "clean_authors": clean_record.get("authors") if clean_record else None,
    }


if __name__ == "__main__":
    import json
    s = load_settings()
    if s.paths.raw_records_json.exists():
        recs = load_raw_records(s.paths.raw_records_json)
        audit = inspect_raw_lineage(recs)
        print(f"[OK] Loaded {len(recs)} raw records successfully.")
        print("[AUDIT] Lineage Summary:")
        print(json.dumps(audit, indent=2, ensure_ascii=True))
        
        sample_id = recs[0].paper_id
        trace = trace_paper_lineage(sample_id, s)
        print(f"\n[TRACE] Single Paper Lineage ({sample_id}):")
        print(json.dumps(trace, indent=2, ensure_ascii=True))
    else:
        print("[WARN] raw_records_json does not exist. Run fetch_source_records(settings) first.")






