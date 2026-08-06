"""Build and verify the Role 4 baseline RAG artifacts for checkpoint 2.

The script intentionally uses the clean JSON artifact so embedded newlines and
list fields retain the canonical clean-layer representation on every OS.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd  # noqa: E402

from core.config import load_settings  # noqa: E402
from core.utils import read_json, write_json  # noqa: E402
from retrieval.agent import build_agent, run_agent_with_trace  # noqa: E402
from retrieval.index import LocalEmbeddingIndex  # noqa: E402
from retrieval.qa import answer_question  # noqa: E402


SEMANTIC_SMOKE_CASES: tuple[dict[str, str], ...] = (
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


def _semantic_checks(
    index: LocalEmbeddingIndex,
    clean_rows: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    clean_ids = {str(row["paper_id"]) for row in clean_rows}
    for case in SEMANTIC_SMOKE_CASES:
        query = case["query"]
        expected_paper_id = case["expected_paper_id"]
        if expected_paper_id not in clean_ids:
            raise AssertionError(f"Semantic smoke-test source is absent from clean data: {expected_paper_id}")
        results = index.search(query, top_k=top_k)
        retrieved_ids = [result.paper_id for result in results]
        if expected_paper_id not in retrieved_ids:
            raise AssertionError(
                f"Semantic search missed {expected_paper_id} for query: {query}"
            )
        checks.append(
            {
                "query": query,
                "expected_paper_id": expected_paper_id,
                "retrieved": [
                    {
                        "paper_id": result.paper_id,
                        "title": result.title,
                        "score": round(result.score, 6),
                    }
                    for result in results
                ],
            }
        )
    return checks


def main() -> int:
    settings = load_settings()
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(
            f"Missing clean artifact: {settings.paths.clean_json}. Complete CP1 first."
        )

    clean_rows = read_json(settings.paths.clean_json)
    clean_df = pd.DataFrame(clean_rows)
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    manifest = read_json(settings.paths.embeddings_json)
    document_count = len(manifest["documents"])
    collection_count = index.collection.count()
    if document_count != len(clean_df) or collection_count != len(clean_df):
        raise AssertionError(
            "Index count mismatch: "
            f"clean={len(clean_df)}, manifest={document_count}, chroma={collection_count}"
        )
    if manifest["collection_name"] != settings.baseline_collection_name:
        raise AssertionError(
            f"Expected collection {settings.baseline_collection_name}, "
            f"got {manifest['collection_name']}"
        )

    target = clean_rows[0]
    by_id = index.lookup(target["paper_id"])
    by_title = index.lookup(target["title"])
    if not by_id or not by_title or by_id["paper_id"] != target["paper_id"]:
        raise AssertionError("Exact lookup by paper_id/title did not return the source document.")

    semantic_checks = _semantic_checks(index, clean_rows, settings.top_k)
    factual_question = f"Who authored '{target['title']}'?"
    qa_result = answer_question(factual_question, settings=settings, index=index)
    if qa_result.answer != target["authors_joined"]:
        raise AssertionError("Deterministic QA answer does not match clean source authors.")

    agent = build_agent(settings=settings, index=index)
    agent_question = factual_question + " Use the lookup tool and answer only from the indexed corpus."
    agent_result = run_agent_with_trace(
        agent,
        agent_question,
    )
    if not agent_result.tool_calls or not agent_result.tool_outputs:
        raise AssertionError("Agent returned without auditable retrieval tool usage.")

    payload = {
        "checkpoint": 2,
        "role": "RAG & agent",
        "status": "pass",
        "clean_artifact": "data/clean/papers_clean.json",
        "clean_rows": len(clean_df),
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.model_name,
        "collection_name": index.collection_name,
        "collection_count": collection_count,
        "embedding_manifest": "data/embeddings/papers_embeddings.json",
        "exact_lookup": {
            "paper_id": target["paper_id"],
            "title": target["title"],
            "by_id_passed": True,
            "by_title_passed": True,
        },
        "semantic_searches": semantic_checks,
        "deterministic_qa": {
            "question": factual_question,
            "answer": qa_result.answer,
            "source_paper_id": target["paper_id"],
            "retrieved_doc_ids": qa_result.retrieved_doc_ids,
        },
        "agent": {
            "question": agent_question,
            "answer": agent_result.answer,
            "tool_calls": agent_result.tool_calls,
            "tool_outputs": agent_result.tool_outputs,
        },
    }
    write_json(settings.paths.demo_answers, payload)

    print(f"collection: {index.collection_name}")
    print(f"documents: {collection_count}")
    print(f"exact lookup: PASS ({target['paper_id']})")
    print(f"semantic searches: PASS ({len(semantic_checks)})")
    print(f"agent tools: PASS ({', '.join(agent_result.tool_calls)})")
    print(f"manifest: {settings.paths.embeddings_json}")
    print(f"evidence: {settings.paths.demo_answers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
