"""Verify the Role 4 CP5 retrieval delta without rebuilding any collection."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import load_settings  # noqa: E402
from core.utils import read_json, write_json  # noqa: E402
from retrieval.index import LocalEmbeddingIndex, SearchResult  # noqa: E402


def _fingerprint(index: LocalEmbeddingIndex) -> str:
    """Fingerprint collection documents and metadata, not mutable DB bytes."""
    payload = index.collection.get(include=["documents", "metadatas"])
    rows = [
        {"id": item_id, "document": document, "metadata": metadata}
        for item_id, document, metadata in zip(
            payload.get("ids", []),
            payload.get("documents", []),
            payload.get("metadatas", []),
            strict=True,
        )
    ]
    serialised = json.dumps(sorted(rows, key=lambda row: row["id"]), sort_keys=True)
    return sha256(serialised.encode("utf-8")).hexdigest()


def _serialise_results(results: list[SearchResult]) -> list[dict[str, Any]]:
    return [
        {"paper_id": result.paper_id, "title": result.title, "score": round(result.score, 6)}
        for result in results
    ]


def _expected_rank(results: list[SearchResult], expected_id: str) -> int | None:
    return next((rank for rank, item in enumerate(results, 1) if item.paper_id == expected_id), None)


def main() -> int:
    settings = load_settings()
    required = {
        "baseline manifest": settings.paths.embeddings_json,
        "corrupted manifest": settings.paths.corrupted_embeddings_json,
        "CP3 frozen-query evidence": settings.paths.project_dir / "data" / "results" / "role4_cp3_verification.json",
    }
    missing = [f"{label}: {path}" for label, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError("Cannot verify Role 4 CP5; missing " + "; ".join(missing))

    query_lock = read_json(required["CP3 frozen-query evidence"])
    baseline_manifest = read_json(settings.paths.embeddings_json)
    corrupted_manifest = read_json(settings.paths.corrupted_embeddings_json)
    baseline = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    corrupted = LocalEmbeddingIndex.load(settings, settings.paths.corrupted_embeddings_json)

    baseline_count_before = baseline.collection.count()
    baseline_fingerprint_before = _fingerprint(baseline)
    if baseline.collection_name != settings.baseline_collection_name or baseline_count_before != len(baseline_manifest["documents"]):
        raise AssertionError("Baseline collection does not match its manifest.")
    if corrupted.collection_name != settings.corrupted_collection_name or corrupted.collection.count() != len(corrupted_manifest["documents"]):
        raise AssertionError("Corrupted collection does not match its manifest.")

    query_deltas: list[dict[str, Any]] = []
    for locked_query in query_lock["semantic_search"]:
        query = locked_query["query"]
        expected_id = locked_query["expected_paper_id"]
        baseline_results = baseline.search(query, top_k=settings.top_k)
        corrupted_results = corrupted.search(query, top_k=settings.top_k)
        baseline_rank = _expected_rank(baseline_results, expected_id)
        corrupted_rank = _expected_rank(corrupted_results, expected_id)
        query_deltas.append(
            {
                "query": query,
                "expected_paper_id": expected_id,
                "baseline_results": _serialise_results(baseline_results),
                "corrupted_results": _serialise_results(corrupted_results),
                "delta": {
                    "baseline_expected_rank": baseline_rank,
                    "corrupted_expected_rank": corrupted_rank,
                    "expected_top_1_lost": baseline_rank == 1 and corrupted_rank != 1,
                    "top_1_changed": baseline_results[0].paper_id != corrupted_results[0].paper_id,
                },
            }
        )

    baseline_after = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    baseline_count_after = baseline_after.collection.count()
    baseline_fingerprint_after = _fingerprint(baseline_after)
    if baseline_count_before != baseline_count_after or baseline_fingerprint_before != baseline_fingerprint_after:
        raise AssertionError("papers-baseline logical content changed during CP5 verification.")

    output_path = settings.paths.project_dir / "data" / "results" / "role4_cp5_verification.json"
    write_json(
        output_path,
        {
            "checkpoint": 5,
            "role": "RAG & agent",
            "status": "pass",
            "corrupted_collection": {
                "name": corrupted.collection_name,
                "documents": corrupted.collection.count(),
                "manifest": str(settings.paths.corrupted_embeddings_json.relative_to(settings.paths.project_dir)),
            },
            "frozen_query_deltas": query_deltas,
            "baseline_integrity": {
                "collection": baseline.collection_name,
                "documents_before": baseline_count_before,
                "documents_after": baseline_count_after,
                "fingerprint_before": baseline_fingerprint_before,
                "fingerprint_after": baseline_fingerprint_after,
                "logical_content_unchanged": True,
            },
        },
    )
    print(f"Role 4 CP5 verification PASS: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
