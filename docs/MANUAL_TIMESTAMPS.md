# Timestamp video manual (P08, P09)

OCR HUD menghasilkan offset yang berbeda per sampel. P08 dan P09 memakai
tanda manual di video sebagai `timeline` + `reps`.

## Sinkron
`waktu_EEG = waktu_video` (offset 0 s). RMS EEG tinggi di blok gerak,
rendah di jeda 110–270 s.

## Paket
NTNB→NGEED, AKA TNB→AGEM KANAN, AKI TNB→AGEM KIRI, TT→BERDIRI MATA TERTUTUP.

Overlap window EEG: 1,0 s sebelum TURUN/TAHAN; 0,5 s sebelum NAIK.
Onset durasi tetap di kolom `act_*`.

## Jalan
```bash
python scripts/ingest_manual_timestamps.py P08
python scripts/ingest_manual_timestamps.py P09
python -m eegpipe run P08 --force preprocess
```
Jangan `--force ocr|pose|sync|phases` setelah ingest.
