"""Verify the Role 4 deliverables for checkpoint 3 without rebuilding baseline.

The script treats the clean JSON, embedding manifest, persisted Chroma
collection, and recorded agent trace as separate evidence sources.  It never
fetches Crossref or mutates the baseline collection.
"""

from __future__ import annotations

from pathlib import Path
import gc
import re
import shutil
import sys
from tempfile import TemporaryDirectory
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import load_settings  # noqa: E402
from core.utils import read_json, write_json  # noqa: E402
from retrieval.index import LocalEmbeddingIndex  # noqa: E402


SEMANTIC_CASES: tuple[dict[str, str], ...] = (
    {
        "query": "Which paper proposes a retrieval-augmented framework for oil and gas safety report generation?",
        "expected_paper_id": "10.2118/234689-pa",
    },
    {
        "query": "Which paper uses multimodal agentic retrieval for diagnostic support of jawbone lesions?",
        "expected_paper_id": "10.1007/s10278-026-02086-9",
    },
    {
        "query": "Which paper studies retrieval-augmented language models for cross-market equity time-series forecasting?",
        "expected_paper_id": "10.21203/rs.3.rs-10178277/v1",
    },
)


def _normalise(value: str) -> str:
    return " ".join(value.lower().split())


def _verify_agent_trace(
    trace: dict[str, Any], clean_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Confirm the recorded factual answer is grounded in its lookup output."""
    tool_calls = [str(call) for call in trace.get("tool_calls", [])]
    tool_outputs = trace.get("tool_outputs", [])
    if "lookup_paper" not in tool_calls or not tool_outputs:
        raise AssertionError("Agent trace has no auditable lookup_paper output.")

    cited_ids: set[str] = set()
    source_texts: list[str] = []
    for output in tool_outputs:
        content = str(output.get("content", ""))
        source_texts.append(content)
        cited_ids.update(re.findall(r"^paper_id:\s*(.+)$", content, flags=re.MULTILINE))

    if not cited_ids or not cited_ids.issubset(clean_by_id):
        raise AssertionError("Agent tool output contains a paper_id outside the clean corpus.")

    # This CP3 factual demo asks for authors.  Each claimed author must occur
    # in the corresponding source record returned by the retrieval tool.
    answer = _normalise(str(trace.get("answer", "")))
    source_authors = [str(clean_by_id[paper_id]["authors_joined"]) for paper_id in cited_ids]
    author_names = [
        name.strip()
        for authors in source_authors
        for name in authors.split(",")
        if name.strip()
    ]
    missing_authors = [name for name in author_names if _normalise(name) not in answer]
    if missing_authors:
        raise AssertionError(
            "Agent answer is not fully grounded in retrieved author metadata: "
            f"missing {missing_authors}."
        )

    return {
        "tool_calls": tool_calls,
        "tool_output_paper_ids": sorted(cited_ids),
        "tool_output_ids_in_clean_corpus": True,
        "factual_claim": "authors",
        "answer_authors_grounded_in_lookup_output": True,
    }


def main() -> int:
    settings = load_settings()
    clean_rows = read_json(settings.paths.clean_json)
    manifest = read_json(settings.paths.embeddings_json)
    demo = read_json(settings.paths.demo_answers)
    clean_by_id = {str(row["paper_id"]): row for row in clean_rows}
    manifest_by_id = {str(doc["paper_id"]): doc for doc in manifest["documents"]}

    if len(clean_by_id) != len(clean_rows):
        raise AssertionError("Clean dataset contains duplicate paper_id values.")
    if set(clean_by_id) != set(manifest_by_id):
        raise AssertionError("Clean dataset and embedding manifest have different paper_id sets.")
    if manifest["collection_name"] != settings.baseline_collection_name:
        raise AssertionError("Embedding manifest does not point to papers-baseline.")

    # Chroma may update its local files while opening a PersistentClient.  Run
    # all retrieval checks against a byte-for-byte temporary copy so CP3 never
    # changes the baseline persistence committed by the team.
    with TemporaryDirectory(prefix="role4-cp3-chroma-") as temporary_dir:
        copied_chroma_dir = Path(temporary_dir) / "chroma"
        shutil.copytree(settings.paths.chroma_dir, copied_chroma_dir)
        index = LocalEmbeddingIndex(
            settings=settings,
            collection_name=manifest["collection_name"],
            documents=manifest["documents"],
            persist_path=copied_chroma_dir,
        )
        if index.collection.count() != len(clean_rows):
            raise AssertionError("Persisted Chroma collection count does not match clean data.")

        exact_source = clean_rows[0]
        exact_by_id = index.lookup(str(exact_source["paper_id"]))
        exact_by_title = index.lookup(str(exact_source["title"]))
        if exact_by_id != exact_by_title or not exact_by_id:
            raise AssertionError("Exact lookup did not return the same document for paper_id and title.")

        semantic_results: list[dict[str, Any]] = []
        for case in SEMANTIC_CASES:
            results = index.search(case["query"], top_k=settings.top_k)
            if not results or results[0].paper_id != case["expected_paper_id"]:
                raise AssertionError(f"Semantic top-1 mismatch for: {case['query']}")
            semantic_results.append(
                {
                    **case,
                    "top_1_paper_id": results[0].paper_id,
                    "top_1_title": results[0].title,
                    "top_1_score": round(results[0].score, 6),
                }
            )

        chroma_collection_count = index.collection.count()
        # Chroma keeps Windows file handles open until its system is stopped.
        # Release them before TemporaryDirectory attempts cleanup.
        index.client._system.stop()
        del index
        gc.collect()

    output_path = settings.paths.project_dir / "data" / "results" / "role4_cp3_verification.json"
    payload = {
        "checkpoint": 3,
        "role": "RAG & agent",
        "status": "pass",
        "baseline_alignment": {
            "clean_rows": len(clean_rows),
            "clean_unique_paper_ids": len(clean_by_id),
            "manifest_documents": len(manifest_by_id),
            "collection_name": manifest["collection_name"],
            "chroma_collection_count": chroma_collection_count,
            "paper_id_sets_match": True,
        },
        "exact_lookup": {
            "paper_id": exact_source["paper_id"],
            "title": exact_source["title"],
            "by_paper_id_and_title_match": True,
        },
        "semantic_search": semantic_results,
        "agent_corpus_boundary": _verify_agent_trace(demo["agent"], clean_by_id),
        "agent_trace_source": str(settings.paths.demo_answers.relative_to(settings.paths.project_dir)),
    }
    write_json(output_path, payload)
    print(f"PASS: wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
