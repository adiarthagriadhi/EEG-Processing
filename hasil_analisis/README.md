# Hasil analisis (turunan, tanpa data mentah)

Salinan hasil pipeline `eegpipe` per 2026-09-24 agar dapat diakses sesi berikutnya.
**Tidak berisi data mentah** (EDF, video) maupun sinyal/pose turunan (`*.fif`, `*.npz`) —
itu tetap di `data/` (tidak di-commit). Kode partisipan PXX; tidak ada identitas.

- `participants.csv` — grup/timepoint (usia & lama menari BELUM diisi).
- `PXX_*.csv` — keluaran pipeline per partisipan: `erd_ers`, `spectral` (specparam),
  `li`, `romberg_features`, `baseline_features`, `erd_sensitivity`.
- `hypothesis_endpoints.csv`, `hypothesis_tests.csv` — uji H1–H5 (7 penari vs 4 non-penari).
- `SIMULATED_group_endpoints.csv` — DATA SIMULASI (is_simulated=True), bukan data riil.
- `ocr_timelines_semua.csv` — timeline instruksi (OCR) 14 partisipan, detik video.
- `per_partisipan/PXX/` — `timeline.csv` (OCR), `ocr_samples.csv`, `reps.csv` (fase gerak
  aktual dari pose, detik video), `sync.json` (sinkronisasi), `keputusan.yaml` (kanal buruk,
  ICA, offset final).
- `audit_*.csv` — keluaran uji cepat `scripts/audit_segmen/` (pendekatan baru: offset tetap
  0,85 dtk, semua segmen, acuan gabungan). Angka EKSPLORATIF.

Catatan status: P33–P35 berhenti di sinkronisasi (hanya OCR/pose/sync tersedia); ERD dkk. di
`PXX_erd_ers.csv` masih memakai metode LAMA (offset per partisipan, acuan per repetisi) —
akan diganti setelah pendekatan baru diimplementasikan. Lihat CLAUDE.md.
