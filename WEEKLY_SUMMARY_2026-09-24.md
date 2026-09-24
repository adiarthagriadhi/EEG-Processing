# Weekly Summary: Fixed Offset 0.85s, 12 Combined Segments, Area-Map Stage

## ✅ COMPLETED THIS WEEK

### 1. **Area-Map Stage Implementation** (228 lines)
   - New module: `eegpipe/area_map.py`
   - Analyzes spectral features per anatomical region (8 areas)
   - Integrates key audit findings:
     - **Combined baseline reference**: 50% quietest 2-sec windows from rest periods
     - **Fixed offset**: 0.85s (median of 11 audit participants, SD 0.2)
     - **Combined segments**: All 12 segments (4 reps × 3 tasks) per phase
     - **Edge trimming**: 0.25s per edge (max 15% of phase duration)
   - Outputs specparam features: aperiodic offset + mu/beta periodic components

### 2. **Pipeline Integration** (21 lines added to pipeline.py)
   - New function: `stage_area_map(P, cfg, clean, reps, tl, force=False)`
   - Added "area_map" to STAGES list
   - Integrated into `run()` function for seamless execution
   - Executes after spectral stage, before romberg stage

### 3. **Documentation** (100 lines)
   - `IMPLEMENTATION_NOTES_2026-09-24.md`: Technical details, testing checklist
   - Rationale for all implementation choices documented

## 📊 KEY AUDIT FINDINGS INTEGRATED

From exploratory analysis on 11 participants (P01-P07, P10, P36-P38):

| Metric | Finding | Impact |
|--------|---------|--------|
| **Precision (SE)** | Combined baseline 40% better | Segments retained: P10 4→10, penari 9→11 |
| **Garis latar TAHAN** | Non-penari +7.9 vs penari +2.7 dB (d=-0.87) | Supports H2 (motor stability) |
| **Mu periodik TURUN** | Non-penari -0.71 vs penari +0.50 dB (d=1.75, p=0.018) | Supports H1 (neural efficiency) |
| **ERD power** | Changed +5dB with combined baseline (vs -1.25dB before) | Shows importance of acuan gabungan |

## 🔧 TECHNICAL HIGHLIGHTS

### Combined Baseline Strategy
```python
# Previous: per-repetition baseline → lost segments for some participants
# New: 50% quietest 2-sec windows from video-annotated rest periods
# Benefit: consistent segment count across all participants
```

### Fixed Offset Justification  
- Offset per participant: +0.48 to +1.37s (range 0.89s)
- Median: 0.85 ± 0.20s (SD)
- Finding: Fixed 0.85s + combined baseline MORE robust than per-participant offset
- Use case: Area-map uses fixed offset; per-participant offset still used for overall sync

### Phase-Specific Analysis
- **TURUN** (1-3 sec): Dynamic stability/coordination
- **TAHAN** (4-5 sec): Balance/postural control (strongest differentiation)
- **NAIK** (6-8 sec): Everyday movement (easiest, least differentiation)

## 📋 TESTING CHECKLIST (When Data Available)

```bash
# Test area_map on single participant
python -m eegpipe run P02 --force area_map
# Output: data/results/P02_area_map.csv

# Test on all participants
python -m eegpipe run-all --force area_map
# Output: data/results/*_area_map.csv (38 files)

# Collect group-level results
python -m eegpipe group
# Output: group_report.html, group_endpoints.csv
```

## 📈 HYPOTHESES ALIGNMENT

### H1-H5 (Original, Main Analysis)
- ERD/spectral per-channel
- Lateralization indices (LI, LRP)
- Duration metrics
- Status: Existing stages (erd, spectral) unaffected

### H6-H8 (New, Duration-Based - STRONGEST)
- H6: TURUN duration longer in dancers (penari > non-penari)
- H7: TAHAN variability smaller in dancers (CV: 0.25 vs 0.62, d=-2.12, p=0.019)
- H8: NAIK duration shorter in dancers (1.0 vs 1.7 dtk, d=-2.34, p=0.012)
- Status: Implemented via phase detection + metrics in endpoints.py

### H9-H11 (Area-Map Exploratory)
- H9: Mu periodic lower in dancers TURUN (exploratory)
- H10: Offset lower in dancers (matches H2)
- H11: Temporo-posterior mu lower in dancers TAHAN (exploratory)
- Status: Area-map outputs these, but considered exploratory (p<0.1 only)

### H12-H13 (Interactions & Correlations)
- Status: Requires group-level stats (python -m eegpipe group)

## 🔍 CODE QUALITY

- ✅ Syntax validated (py_compile)
- ✅ Module imports verified
- ✅ Functions callable
- ✅ Proper error handling for edge cases
- ✅ Documented with docstrings
- ✅ Consistent with pipeline architecture

## ⚠️ NOTES FOR NEXT WEEK

1. **System dependencies**: tesseract-ocr, libgl needed for OCR/pose
   - Already working in existing audit scripts
   - Not blocking area_map implementation

2. **Fixed offset vs per-participant**: 
   - Area-map: uses fixed 0.85s (simplicity, robustness)
   - ERD/phases: uses calculated offset (accuracy per participant)
   - Both approaches valid for different purposes

3. **Area-map is exploratory**:
   - 72 statistical tests (8 areas × 3 phases × 3 metrics)
   - Only 6 with p<0.1 (≈ chance)
   - Use as secondary/confirmatory analysis, not primary
   - Prioritize H6-H8 (duration metrics) which are STRONGER

## 📝 COMMITS THIS WEEK

```
a50c2f6 - Dokumentasi implementasi: offset tetap 0.85s, 12 segmen gabungan, area-map stage
ea42c02 - Tambah stage_area_map dengan acuan gabungan & offset tetap 0.85s
```

Total changes: **349 lines added**
- eegpipe/area_map.py: 228 lines (new module)
- eegpipe/pipeline.py: 21 lines (integration)
- IMPLEMENTATION_NOTES_2026-09-24.md: 100 lines (documentation)

## ✨ READY FOR

- Full cohort analysis (38 participants)
- Group-level statistics (H1-H13)
- Paper A (cross-sectional movement generation)
- Paper D (balance/postural control)
- Paper B would need longitudinal data

---
**Status**: IMPLEMENTATION COMPLETE, AWAITING DATA FOR VALIDATION
