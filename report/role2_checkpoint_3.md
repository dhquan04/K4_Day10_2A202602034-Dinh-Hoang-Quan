# Checkpoint 3 Report - Role 2 (Raw Ingestion & Data Lineage)

## 🎯 Target Tasks for CP3
1. **Verify Raw Response / Records / Lineage**: Ensure raw API artifacts and parsed records remain 100% valid and traceable.
2. **Compare Raw vs Clean Record Count**: Compare dataset row counts before and after cleaning and explain any discrepancy.
3. **Prevent Unwanted API Fetches**: Guarantee that baseline execution reads from raw snapshot files without hitting external Crossref API endpoints.

## 📊 Raw vs. Clean Count Comparison
- **Raw Records Count (`data/raw/crossref_records.json`)**: `24` records
- **Clean Records Count (`data/clean/papers_clean.json`)**: `24` records
- **Count Discrepancy (Delta)**: `0` (Zero dropped records)

### Explanation of Discrepancy (Why 0 dropped?)
1. **DOI Validity**: All 24 records from Crossref API contained a valid, unique DOI string (`paper_id`).
2. **Title Integrity**: 100% of raw records contained non-empty title strings.
3. **Summary Availability**: 100% of raw records contained non-empty abstract text after HTML tag stripping.
4. **Data Quality**: The Crossref query parameters (`has-abstract:true`) ensured high-quality raw data upfront, resulting in a 100% retention rate during cleaning.

## 🛡️ Unwanted Fetch Prevention
- Verified that `fetch_source_records(settings)` checks `if not settings.refresh_source and settings.paths.raw_records_json.exists(): return load_raw_records(...)`.
- `refresh_source` is set to `False` by default in `Settings`, ensuring reproducible offline execution during Phase 1 baseline evaluation.

## ✅ Conclusion
Checkpoint 3 tasks for Role 2 are 100% complete. Raw lineage is verified, raw vs clean count comparison is documented, and API call freeze is enforced.
