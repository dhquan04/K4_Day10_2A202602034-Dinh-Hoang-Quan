from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
import pandas as pd

from core.config import Settings
from core.utils import read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


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

# Optional metadata fields may be an empty string when Crossref does not
# supply them. They must still be scalar/non-null so Chroma can store them.
INDEX_NON_EMPTY_COLUMNS: tuple[str, ...] = (
    "paper_id",
    "title",
    "text_for_embedding",
    "published",
    "summary",
)


class IndexInputValidationError(ValueError):
    """Raised when cleaned data cannot safely be written to Chroma."""


def validate_index_input(df: pd.DataFrame) -> None:
    """Check the cleaned-data contract required by the retrieval layer.

    Cleaning owns the full schema validation. This smaller guard protects the
    index boundary: Chroma receives only the document content and scalar
    metadata listed in :data:`INDEX_REQUIRED_COLUMNS`.
    """
    missing_columns = [column for column in INDEX_REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise IndexInputValidationError(
            f"Cannot build retrieval index; missing required columns: {missing_columns}."
        )
    if df.empty:
        raise IndexInputValidationError("Cannot build retrieval index from an empty dataframe.")

    invalid_ids = df["paper_id"].isna() | df["paper_id"].astype(str).str.strip().eq("")
    if invalid_ids.any():
        raise IndexInputValidationError(
            f"Cannot build retrieval index; {int(invalid_ids.sum())} rows have an empty paper_id."
        )
    duplicate_ids = df["paper_id"].astype(str).str.strip().duplicated(keep=False)
    if duplicate_ids.any():
        examples = df.loc[duplicate_ids, "paper_id"].astype(str).head(3).tolist()
        raise IndexInputValidationError(
            "Cannot build retrieval index; paper_id must be unique "
            f"(duplicate examples: {examples})."
        )

    for column in INDEX_REQUIRED_COLUMNS:
        null_values = df[column].isna()
        if null_values.any():
            raise IndexInputValidationError(
                f"Cannot build retrieval index; {int(null_values.sum())} rows have null {column}."
            )

    for column in INDEX_NON_EMPTY_COLUMNS:
        missing_values = df[column].astype(str).str.strip().eq("")
        if missing_values.any():
            raise IndexInputValidationError(
                f"Cannot build retrieval index; {int(missing_values.sum())} rows have an empty {column}."
            )

    non_scalar_metadata = [
        column
        for column in INDEX_REQUIRED_COLUMNS
        if df[column].map(lambda value: isinstance(value, (dict, list, set, tuple))).any()
    ]
    if non_scalar_metadata:
        raise IndexInputValidationError(
            "Cannot build retrieval index; Chroma metadata must be scalar values, "
            f"but these columns contain collections: {non_scalar_metadata}."
        )


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = MiniLMEmbeddings(settings.embedding_model)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_collection(name=collection_name)
        self.documents_by_paper_id = {document["paper_id"].lower(): document for document in documents}
        self.documents_by_title = {document["title"].lower(): document for document in documents}

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        for index, row in enumerate(records):
            documents.append(
                {
                    "record_id": f"{row['paper_id']}::{index}",
                    "paper_id": row["paper_id"],
                    "title": row["title"],
                    "content": row["text_for_embedding"],
                    "metadata": {
                        "paper_id": row["paper_id"],
                        "title": row["title"],
                        "published": row["published"],
                        "authors_joined": row["authors_joined"],
                        "categories_joined": row["categories_joined"],
                        "summary": row["summary"],
                        "abs_url": row["abs_url"],
                        "pdf_url": row["pdf_url"],
                    },
                }
            )
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        validate_index_input(df)
        collection_name = cls._derive_collection_name(settings, embeddings_output_path)
        documents = cls._build_documents(df)
        persist_path = settings.paths.chroma_dir
        persist_path.mkdir(parents=True, exist_ok=True)

        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        client = chromadb.PersistentClient(path=str(persist_path))
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        collection = client.create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        collection.add(
            ids=[document["record_id"] for document in documents],
            embeddings=embeddings,
            documents=[document["content"] for document in documents],
            metadatas=[document["metadata"] for document in documents],
        )

        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        try:
            manifest_persist_path = str(persist_path.relative_to(settings.paths.project_dir))
        except ValueError:
            manifest_persist_path = str(persist_path)
        write_json(
            manifest_path,
            {
                "backend": "chroma",
                "embedding_model": settings.embedding_model,
                "persist_path": manifest_persist_path,
                "collection_name": collection_name,
                "documents": documents,
            },
        )
        return cls(
            settings=settings,
            collection_name=collection_name,
            documents=documents,
            persist_path=persist_path,
        )

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        payload = read_json(embeddings_path or settings.paths.embeddings_json)
        persist_path = Path(payload["persist_path"])
        if not persist_path.is_absolute():
            persist_path = settings.paths.project_dir / persist_path
        return cls(
            settings=settings,
            collection_name=payload["collection_name"],
            documents=payload["documents"],
            persist_path=persist_path,
        )

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k or self.settings.top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for record_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if not record_id or not metadata or not content:
                continue
            scored.append(
                SearchResult(
                    paper_id=str(metadata["paper_id"]),
                    title=str(metadata["title"]),
                    score=max(0.0, 1.0 - float(distance or 0.0)),
                    content=str(content),
                    metadata=dict(metadata),
                )
            )
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        needle = value.strip().lower()
        if needle in self.documents_by_paper_id:
            return self.documents_by_paper_id[needle]
        if needle in self.documents_by_title:
            return self.documents_by_title[needle]
        return None
