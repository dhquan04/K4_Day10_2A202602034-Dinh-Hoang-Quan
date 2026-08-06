from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from core.utils import first_sentence, read_json, write_json

MIN_DOCUMENTS = 4
QUESTIONS_PER_TYPE = 2
QUESTION_TYPES = ("summary", "authors", "date", "categories")


def _is_usable_row(row: pd.Series) -> bool:
    title = str(row.get("title", "")).strip()
    summary = str(row.get("summary", "")).strip()
    paper_id = str(row.get("paper_id", "")).strip()
    published = str(row.get("published", "")).strip()
    return bool(paper_id and title and summary and published and len(summary) >= 40)


def _select_candidate_papers(df: pd.DataFrame) -> pd.DataFrame:
    usable = df[df.apply(_is_usable_row, axis=1)].copy()
    if usable.empty:
        raise ValueError("No usable papers found for evaluation set construction.")

    usable["summary_chars"] = usable["summary"].astype(str).str.len()
    usable["authors_joined"] = usable["authors_joined"].fillna("").astype(str)
    usable = usable.sort_values(
        by=["summary_chars", "authors_joined", "paper_id"],
        ascending=[False, False, True],
    )
    return usable


def _question_for_type(question_type: str, title: str) -> str:
    if question_type == "summary":
        return f"What is the main contribution of the paper titled '{title}'?"
    if question_type == "authors":
        return f"Who authored the paper titled '{title}'?"
    if question_type == "date":
        return f"When was the paper titled '{title}' published?"
    if question_type == "categories":
        return f"What categories apply to the paper titled '{title}'?"
    raise ValueError(f"Unsupported question_type: {question_type}")


def _ground_truth_for_type(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(str(row["summary"]))
    if question_type == "authors":
        authors = str(row.get("authors_joined", "")).strip()
        return authors or "unknown"
    if question_type == "date":
        return str(row["published"]).strip()
    if question_type == "categories":
        categories = str(row.get("categories_joined", "")).strip()
        if categories:
            return categories
        return str(row.get("primary_category", "uncategorized")).strip() or "uncategorized"
    raise ValueError(f"Unsupported question_type: {question_type}")


def _build_question(row: pd.Series, question_type: str, index: int) -> dict[str, Any]:
    title = str(row["title"]).strip()
    paper_id = str(row["paper_id"]).strip()
    return {
        "id": f"{question_type}-{index:02d}",
        "question_type": question_type,
        "question": _question_for_type(question_type, title),
        "ground_truth": _ground_truth_for_type(row, question_type),
        "ground_truth_doc_ids": [paper_id],
    }


def validate_test_set_against_index(
    test_set: list[dict[str, Any]],
    indexed_paper_ids: Iterable[str],
) -> list[str]:
    """Return question ids whose ground_truth_doc_ids are missing from the index."""
    indexed = {str(paper_id).strip() for paper_id in indexed_paper_ids if str(paper_id).strip()}
    missing: list[str] = []
    for item in test_set:
        doc_ids = [str(doc_id).strip() for doc_id in item.get("ground_truth_doc_ids", [])]
        if not doc_ids or any(doc_id not in indexed for doc_id in doc_ids):
            missing.append(str(item.get("id", "<unknown>")))
    return missing


def load_indexed_paper_ids(embeddings_manifest_path) -> set[str]:
    """Load paper_id values from an embedding manifest produced by Role RAG."""
    path = Path(embeddings_manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Embedding manifest not found: {path}")
    payload = read_json(path)
    documents = payload.get("documents") or []
    return {str(doc.get("paper_id", "")).strip() for doc in documents if doc.get("paper_id")}


def preview_test_set(test_set: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    """Return a short preview of fixed test-set rows before evaluation."""
    preview: list[dict[str, Any]] = []
    for item in test_set[:limit]:
        preview.append(
            {
                "id": item.get("id"),
                "question_type": item.get("question_type"),
                "question": item.get("question"),
                "ground_truth": item.get("ground_truth"),
                "ground_truth_doc_ids": item.get("ground_truth_doc_ids"),
            }
        )
    return preview


def build_test_set(
    df: pd.DataFrame,
    output_path,
    indexed_paper_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Build a fixed evaluation set from the cleaned dataframe.

    When ``indexed_paper_ids`` is provided (typically from the embedding
    manifest), every ``ground_truth_doc_ids`` entry must exist in that index.
    """
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} cleaned documents, got {len(df)}.")

    candidates = _select_candidate_papers(df)
    clean_ids = set(df["paper_id"].astype(str).str.strip())
    if indexed_paper_ids is not None:
        indexed = {str(paper_id).strip() for paper_id in indexed_paper_ids if str(paper_id).strip()}
        candidates = candidates[candidates["paper_id"].astype(str).str.strip().isin(indexed)]
        if candidates.empty:
            raise ValueError("No cleaned papers overlap with indexed paper_id values.")

    needed_papers = QUESTIONS_PER_TYPE * len(QUESTION_TYPES)
    if len(candidates) < needed_papers:
        raise ValueError(
            f"Need at least {needed_papers} usable papers for the evaluation set, got {len(candidates)}."
        )

    selected_rows = candidates.drop_duplicates(subset=["paper_id"]).head(needed_papers)
    test_set: list[dict[str, Any]] = []
    question_index = 1

    for question_type in QUESTION_TYPES:
        type_index = list(QUESTION_TYPES).index(question_type)
        type_rows = selected_rows.iloc[
            (type_index * QUESTIONS_PER_TYPE) : ((type_index + 1) * QUESTIONS_PER_TYPE)
        ]
        for _, row in type_rows.iterrows():
            test_set.append(_build_question(row, question_type, question_index))
            question_index += 1

    missing_in_clean = [
        item["id"]
        for item in test_set
        if any(doc_id not in clean_ids for doc_id in item["ground_truth_doc_ids"])
    ]
    if missing_in_clean:
        raise ValueError(f"Test set references paper_id values missing from clean data: {missing_in_clean}")

    if indexed_paper_ids is not None:
        missing_in_index = validate_test_set_against_index(test_set, indexed_paper_ids)
        if missing_in_index:
            raise ValueError(
                f"Test set references paper_id values missing from the index: {missing_in_index}"
            )

    write_json(output_path, test_set)
    return test_set
