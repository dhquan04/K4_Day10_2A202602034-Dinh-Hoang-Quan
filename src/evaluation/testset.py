from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

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


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a fixed evaluation set from the cleaned dataframe."""
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} cleaned documents, got {len(df)}.")

    candidates = _select_candidate_papers(df)
    needed_papers = QUESTIONS_PER_TYPE * len(QUESTION_TYPES)
    if len(candidates) < needed_papers:
        raise ValueError(
            f"Need at least {needed_papers} usable papers for the evaluation set, got {len(candidates)}."
        )

    selected_rows = candidates.drop_duplicates(subset=["paper_id"]).head(needed_papers)
    test_set: list[dict[str, Any]] = []
    question_index = 1

    for question_type in QUESTION_TYPES:
        type_rows = selected_rows.iloc[
            (list(QUESTION_TYPES).index(question_type) * QUESTIONS_PER_TYPE) : (
                (list(QUESTION_TYPES).index(question_type) + 1) * QUESTIONS_PER_TYPE
            )
        ]
        for _, row in type_rows.iterrows():
            test_set.append(_build_question(row, question_type, question_index))
            question_index += 1

    write_json(output_path, test_set)
    return test_set
