# Checkpoint 4 Report - Role 2 (Raw Ingestion & Recovery Point)

## 🎯 Target Tasks for CP4
1. **Rest & Baseline Freeze**: Lock baseline raw artifacts before Phase 2 corruption experiments.
2. **Raw Source as Recovery Point**: Ensure raw snapshot files (`data/raw/crossref_records.json` and `data/raw/crossref_response.json`) serve as the immutable single-source-of-truth for data restoration in CP6.

## 🔒 Raw Source Integrity Status
- **Raw API Response (`data/raw/crossref_response.json`)**: `245 KB` (Locked & Immutable)
- **Raw Parsed Records (`data/raw/crossref_records.json`)**: `24 records` (Locked & Immutable)
- **Recovery Point Helper (`restore_from_raw_snapshot`)**: Tested & Verified (`24/24` records ready for restoration).

## 🛠️ Code Artifacts Added
- Implemented `restore_from_raw_snapshot(settings: Settings)` in [`src/ingestion/crossref.py`](file:///e:/lab1/K4_Day10_Nhom-ChickenFarmer/src/ingestion/crossref.py).

## ✅ Conclusion
Checkpoint 4 for Role 2 is 100% complete. Raw data sources are frozen and verified as the recovery point for Phase 2 data repair.
