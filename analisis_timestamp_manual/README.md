# Analisis timestamp fase manual: P08, P09, P31, P32 (2026-09-25)

> Folder ini = model repo (eegpipe v2) yang dijalankan dengan timestamp manual. **Metode baru yang berdiri
> sendiri (istilah Gerak/Tahan/Naik/Berdiri/Tutup Mata, data cleaning bertahap) ada di `analisis_baru/`.**

Catatan dan hasil analisis sesi ini, **terpisah** dari catatan utama repo (CLAUDE.md, `hasil_analisis/`).
Hasil di sini tidak menggantikan `hasil_analisis/v2/`.

## Data dan cara
- Masukan: `PXX_Trial.EDF` + timestamp manual peneliti (`data/manual_timestamps/PXX_timestamps.csv`).
  Label N/AKA/AKI → T → N (naik) → B; TT = mulai tutup mata. Offset EEG 0 dtk (keputusan pengguna).
- Pipeline: `python -m eegpipe run PXX` (jalur timestamp manual, lihat `docs/MANUAL_TIMESTAMPS.md`).
  Preprocessing, deteksi sinyal datar, tahap `segmen` dan `hypotheses-v2` memakai model dan parameter yang sama
  dengan jalur video.
- Jendela observasi (keputusan pengguna 2026-09-25): tiap fase dimulai 0,5 dtk SEBELUM timestamp onsetnya
  dan berakhir di timestamp fase berikut, tanpa pemangkasan (`manual_timestamps.pre_onset_sec`, `trim_sec`).
  PRA = [turun − 2,5, turun − 0,5]; POST = [B + 0,5, B + 2]. Durasi fase tetap dihitung dari timestamp.
- Baseline.EDF dan video tidak diunggah → tahap `baseline` dilewati.
- Keputusan per partisipan (kanal buruk, ICA, offset) di `per_partisipan/PXX/keputusan.yaml`.

## Beda dengan jalur video (tidak dapat dihindari tanpa video)
- Acuan gabungan: semua jendela BERDIRI RILEKS + ISTIRAHAT UTAMA (jalur video: 50% paling diam menurut gerak
  tubuh di video).
- `latency_hud` NaN.
- Romberg EO tidak dianalisis: jarak B terakhir → TT hanya ±42–43 dtk pada keempat partisipan, lebih pendek dari
  EO 30 dtk + istirahat 15 dtk menurut protokol, sehingga EO tidak dapat diturunkan dari TT.

## Hasil
| | P08 | P09 | P31 | P32 |
|---|---|---|---|---|
| Grup | penari | penari | non-penari | non-penari |
| Repetisi lengkap | 12/12 | 12/12 | 10/10 (tanpa NGEED blok 1) | 12/12 |
| Kanal×waktu datar (median) | 21,5% | 12,4% | 15,8% | 11,4% |
| Cakupan Romberg EC | 46% | 9% | 100% | 100% |
| Batas ketelitian | 1,8 dB | 0,9 dB | 2,1 dB | 1,8 dB |

Sinyal datar dan cakupan EC sama dengan hasil jalur video sebelumnya → EDF dan model yang dipakai sama.

### Kesesuaian durasi fase manual vs pose (40 repetisi; `perbandingan_durasi_per_repetisi.csv`)
| Fase | Manual − pose (median, IQR) | r |
|---|---|---|
| TURUN | +0,95 dtk (0,51…1,90) | −0,03 |
| TAHAN | +0,34 dtk (−0,32…2,38) | 0,49 |
| NAIK | +0,68 dtk (−0,76…1,14) | 0,15 |

Definisi awal/akhir fase manual berbeda sistematis dari definisi pose.

### Dampak pada H1–H13 (`perbandingan_H1-H13.csv`)
38 partisipan dengan model v2; hanya P08, P09, P31, P32 diganti ke timestamp manual (jendela −0,5 dtk):
- H3 durasi tahan agem: g 1,53 → 0,98 (p_FDR < 0,001 → 0,014)
- H6 durasi TURUN: g 1,07 → 0,62 (p_FDR 0,008 → 0,106)
- H7 CV TAHAN: g −0,98 → −1,04 (bertahan); H12: g −1,24 → −1,03 (bertahan)
- Lainnya berubah kecil; tidak ada yang berubah arah secara bermakna. Memajukan jendela 0,5 dtk hampir tidak
  mengubah endpoint EEG dibanding jendela tanpa pemajuan.

**Kesimpulan:** jangan mencampur sumber fase (manual vs pose) dalam satu uji grup. Pilihan: timestamp manual untuk
seluruh 38 partisipan, atau timestamp manual hanya sebagai validasi pelacak pose.

## Isi folder
- `PXX_segments.csv`, `PXX_area_map.csv`, `PXX_durasi.csv`, `PXX_romberg_area.csv`: format sama dengan
  `hasil_analisis/v2/`.
- `per_partisipan/PXX/`: `timeline.csv`, `reps.csv`, `segmen_qc.json`, `keputusan.yaml`.
- `perbandingan_endpoint_video_vs_manual.csv`, `perbandingan_durasi_per_repetisi.csv`, `perbandingan_H1-H13.csv`.
- `hypothesis_v2_endpoints_38_dgn_4_manual.csv`, `hypothesis_v2_tests_38_dgn_4_manual.csv`.

## Data cleaning bertahap
Rencana dan status: `RENCANA_CLEANING.md`.
- Tahap 1, inventaris kualitas sinyal (tanpa mengubah data): `tahap1_kualitas/README.md`.
