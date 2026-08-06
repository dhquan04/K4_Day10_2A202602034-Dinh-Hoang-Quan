# Checkpoint 2 Report - Role 2 (Raw Ingestion & Lineage Owner)

## 🎯 Target Tasks
1. **Trace single `paper_id` lineage**: Inspect end-to-end flow across `raw` -> `clean` -> `index`.
2. **Provide source evidence**: Ensure data integrity and audit trail availability for RAG evaluation.
3. **Freeze raw source**: Ensure `refresh_source=False` during baseline evaluation to prevent snapshot mutation.

## 📊 Lineage Verification Results

### Tested Paper ID: `10.47576/2949-1894.2026.7.7.023`
- **Raw Stage (`data/raw/crossref_records.json`)**: `PRESENT`
- **Clean Stage (`data/clean/papers_clean.json`)**: `PRESENT`
- **Index Stage (`data/embeddings/papers_embeddings.json`)**: `PRESENT`
- **Lineage Intact**: `TRUE (100% matched)`

### Field Matching Summary
| Field | Raw Value | Clean Value | Index Value | Match Status |
|---|---|---|---|---|
| `paper_id` | `10.47576/2949-1894.2026.7.7.023` | `10.47576/2949-1894.2026.7.7.023` | `10.47576/2949-1894.2026.7.7.023` | ✅ Matched |
| `title` | Russian RAG paper title | Russian RAG paper title | Russian RAG paper title | ✅ Matched |
| `authors` | `И.В. Ермаков, В.В. Филатов` | `И.В. Ермаков, В.В. Филатов` | `И.В. Ермаков, В.В. Филатов` | ✅ Matched |

## 🛠️ Code Artifacts Added
- Implemented `trace_paper_lineage(paper_id: str, settings: Settings)` in [`src/ingestion/crossref.py`](file:///e:/lab1/K4_Day10_Nhom-ChickenFarmer/src/ingestion/crossref.py).
- Verified snapshot freeze mode in `Settings` (`refresh_source=False`).

## ✅ Conclusion
Checkpoint 2 verification for Role 2 is complete. Lineage is intact across raw data, cleaned dataset, and ChromaDB baseline collection.
