# Hasil analisis (turunan, tanpa data mentah)

Dibuat oleh `python scripts/ekspor_hasil.py` dari keluaran pipeline `eegpipe`. **Tidak berisi data mentah**
(EDF, video) maupun turunan sinyal/pose (`*.fif`, `*.npz`) — itu tetap di `data/` (tidak di-commit).
Kode partisipan PXX; tidak ada identitas. Lihat CLAUDE.md untuk konteks & keputusan metode.

## `v2/` — PENDEKATAN UTAMA (2026-09-24)
Waktu fase dari video; offset tetap 0,85 dtk (P01 manual +3,25); semua segmen dipakai; batas fase dipangkas;
acuan gabungan paling diam; specparam; kanal×waktu DATAR (reset amplifier) = data hilang.
- `PXX_segments.csv` — satu baris per segmen × kanal: power dB relatif acuan (theta/mu/beta/broad),
  `flat_frac`, `valid` (False = kanal datar > 10% → nilai NaN), durasi fase & jendela, sumber fase.
- `PXX_area_map.csv` — specparam gabungan: `pool` (SEMUA = 12 segmen; atau per gerakan, 4 segmen),
  `phase` (PRA/TURUN/TAHAN/NAIK/POST), `level` (kanal/area/belahan): `offset_change` (garis latar, dB),
  `exponent_change`, `theta/mu/beta_periodic_db`, `*_relative_db` (kanal − median belahan), `n_valid`,
  `few_segments`, `noise_floor_db` (batas ketelitian partisipan).
- `PXX_durasi.csv` — durasi TURUN/TAHAN/NAIK per repetisi dari video (dtk), latensi thd instruksi.
- `PXX_romberg_area.csv` — Romberg EO/EC per area (specparam; cakupan EEG; jumlah jendela bersih).
- `hypothesis_v2_endpoints.csv`, `hypothesis_v2_tests.csv` — H6–H13 (semua = EKSPLORATIF; konfirmatori =
  partisipan di luar set pembentuk hipotesis).
- `mixed_segments_v2.csv` — model campuran tingkat segmen (grup + gerakan, intersep acak partisipan).
- `dose_response_v2.csv` — regresi durasi menari + usia (menunggu data `dance_years`, `age`).

## `metode_lama/` — hanya untuk perbandingan/riwayat
ERD power total dengan acuan per repetisi (`PXX_erd_ers.csv`), `PXX_spectral.csv`, `PXX_li.csv`, Romberg &
Baseline.EDF lama, hipotesis H1–H5, `SIMULATED_*` (DATA SIMULASI, bukan data riil).

## `per_partisipan/PXX/`
`timeline.csv` (OCR instruksi, detik video), `ocr_samples.csv`, `reps.csv` (fase aktual dari pose),
`sync.json` (estimasi data, kini hanya alarm), `segmen_qc.json` (acuan, % datar, batas ketelitian),
`keputusan.yaml` (offset dipakai + dasar, kanal buruk, ICA).

## Peringatan tafsir
- **Grup tercampur dengan hari rekaman** (penari 9 Sep; non-penari 14 Sep kecuali P10) dan kualitas sinyal
  berbeda per hari (% datar 0–13% vs 6–36%). Beda grup EEG dapat berasal dari kondisi perangkat.
- n = 7 vs 7; seluruh uji bersifat eksploratif.

## Perbaikan 2026-09-24 (pelacak pose + penyelamatan sinyal datar)
- `v2/` = hasil SESUDAH perbaikan (baku saat ini); `v2_sebelum_perbaikan/` = hasil sebelumnya (disimpan untuk
  perbandingan). Ringkasan perubahan: `v2/perbandingan_perbaikan_v2.csv` (per partisipan) dan
  `v2/perbandingan_perbaikan_H_v2.csv` (H1–H13). Metode: EEG_PROCESSING.md, bagian "Perbaikan metode 2026-09-24".
