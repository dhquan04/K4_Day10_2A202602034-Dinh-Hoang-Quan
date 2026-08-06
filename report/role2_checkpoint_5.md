# Checkpoint 5 Report - Role 2 (Raw Ingestion & Controlled Corruption Lineage)

## 🎯 Target Tasks for CP5
1. **Raw Source Integrity Verification**: Confirm that original raw source artifacts (`data/raw/crossref_records.json` and `data/raw/crossref_response.json`) remain 100% intact and unmutated during corruption experiments.
2. **Corrupted Lineage Tracing**: Provide traceability between corrupted records in Phase 2 and their corresponding original raw records.
3. **No Unwanted API Refetches**: Ensure `refresh_source=False` is maintained so that new API fetches do not distort the comparison baseline.

## 📊 Raw Integrity & Corruption Lineage Status

### 1. Raw Source Integrity Audit
- **Raw API Response (`data/raw/crossref_response.json`)**: `245 KB` (100% Intact, Unmutated)
- **Raw Parsed Records (`data/raw/crossref_records.json`)**: `24 records` (100% Intact, Unmutated)

### 2. Corruption Lineage Tracing Helper
- Implemented `trace_corrupted_lineage(paper_id: str, settings: Settings)` in [`src/ingestion/crossref.py`](file:///e:/lab1/K4_Day10_Nhom-ChickenFarmer/src/ingestion/crossref.py#L330-L375).
- Maps corrupted items in `papers_clean_corrupted.csv/json` directly back to the original raw `PaperRecord` entries in `data/raw/crossref_records.json`.

## ✅ Conclusion
Checkpoint 5 tasks for Role 2 are 100% complete. Raw source integrity is preserved, corrupted lineage traceability is enabled, and API call freeze is maintained.
