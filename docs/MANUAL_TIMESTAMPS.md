# Timestamp fase manual (keputusan pengguna 2026-09-25)

Bila `data/manual_timestamps/PXX_timestamps.csv` ada, `python -m eegpipe run PXX` memakai timestamp
peneliti sebagai waktu fase dan **melewati** tahap `ocr`, `pose`, `sync`, `phases` dan cek onset.
Video tidak dibutuhkan. Tahap `preprocess`, `erd`, `spectral`, `romberg`, `baseline` (bila Baseline.EDF ada),
`segmen`, serta `hypotheses-v2` berjalan **dengan model dan parameter yang sama** seperti jalur video.

## Label
| label | arti | kolom reps |
|---|---|---|
| `N` / `AKA` / `AKI` | mulai turun ngeed / agem kanan / agem kiri | `act_turun` (= `act_arm`, acuan PRA) |
| `T` | mulai menahan posisi | `act_tahan` |
| `N` (sesudah `T`) | mulai naik | `act_naik` |
| `B` | berdiri | `act_end` (acuan POST) |
| `TT` | mulai tutup mata | Romberg EC = TT … TT + 30 dtk |

Spasi di label diabaikan. Urutan yang menyimpang dicatat di `decisions/PXX.yaml → manual_timestamp_problems`
dan di laporan QC; repetisi tak lengkap = `compliance: incomplete`.

## Sinkronisasi
`t_EEG = t_timestamp + manual_timestamps.offset_sec` (baku 0). Tidak ada estimasi/alarm offset.

## Penomoran repetisi
Jeda > 60 dtk = ISTIRAHAT UTAMA. Blok 1 = rep 1–2, blok 2 = rep 3–4 per gerakan, sehingga blok yang
tidak ada (P31: NGEED blok 1) tidak menggeser nomor.

## Yang berbeda dari jalur video (tidak dapat dihindari tanpa video)
- **Acuan gabungan**: jalur video memilih 50% jendela 2 dtk paling diam menurut gerak tubuh di video.
  Tanpa video, **semua** jendela BERDIRI RILEKS (B + 2 dtk … maks. B + 8 dtk, berhenti 1 dtk sebelum
  repetisi berikut) + ISTIRAHAT UTAMA (B terakhir blok 1 + 8 dtk … 5 dtk sebelum blok 2) dipakai.
  Tidak dipilih dari EEG (sirkular). QC: `segmen_qc.json → reference_selection`.

Analisis sampel pertama dengan jalur ini (P08, P09, P31, P32) dan perbandingannya dengan jalur video/pose
dicatat terpisah di `analisis_timestamp_manual/`.
- **Latensi terhadap instruksi HUD** (`latency_hud`) tidak terukur (NaN).
- **Romberg EO** tidak ditandai. Turunan dari protokol (TT − 45 … TT − 15) dapat diaktifkan dengan
  `derive_eo: true`, tetapi baku `false` karena jarak B terakhir → TT pada data uji lebih pendek dari 45 dtk
  (lihat `analisis_timestamp_manual/README.md`). Perlu label EO sendiri bila EO dibutuhkan.

## Jalan
```bash
python scripts/ingest_manual_timestamps.py --all   # cek urutan label (tanpa EEG)
python -m eegpipe run P08                          # timestamp berubah → otomatis ulang mulai preprocess
```
