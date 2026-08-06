from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
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

