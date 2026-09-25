# Tahap 1 data cleaning: inventaris kualitas sinyal (P08, P09, P31, P32)

Tahap ini hanya memeriksa dan menandai; data tidak diubah. Skrip: `../skrip/tahap1_kualitas.py`.
Sinyal: EDF mentah (datar, clipping) + bandpass 1–35 Hz (tanpa ICA, tanpa interpolasi). Waktu fase dari
timestamp manual (offset 0). Setiap segmen dipotong per 1 dtk dan tiap jendela × kanal diberi label:
`datar` (≥ 10% sampel datar), `ekstrem` (> 150 µV peak-to-peak), `tinggi` (100–150 µV), `ok`.

## Jendela observasi
Sama persis dengan tahap `segmen` (`segments.phase_windows`). Timestamp manual, offset 0, dan tiap fase dimajukan
0,5 dtk sebelum timestamp onsetnya (keputusan pengguna 2026-09-25):
PRA [turun − 2,5, turun − 0,5]; TURUN [turun − 0,5, tahan]; TAHAN [tahan − 0,5, naik]; NAIK [naik − 0,5, B];
POST [B + 0,5, B + 2]. Batas fase tidak dipangkas.

## Ringkasan per fase (`ringkasan_per_fase.csv`; % jendela × kanal, rentang 4 partisipan)
| Fase | datar | > 150 µV | ok | ptp median (µV) |
|---|---|---|---|---|
| PRA | 19–31 | 6–25 | 29–58 | 37–83 |
| TURUN | 14–22 | 39–74 | 5–26 | 113–380 |
| TAHAN | 14–27 | 20–74 | 7–40 | 63–362 |
| NAIK | 16–37 | 39–65 | 10–24 | 93–270 |
| POST | 7–27 | 43–81 | 7–30 | 127–416 |
| ACUAN (berdiri/istirahat) | 9–26 | 8–22 | 43–63 | 38–95 |
| Romberg EC | 6–29 | 4–6 | 57–77 | 31–60 |

- Bila aturan tolak baku (> 150 µV) diterapkan, fase TURUN, NAIK dan POST tersisa 5–30% jendela × kanal.
- POST masih penuh artefak: gerak belum selesai 0,5–2 dtk sesudah B.
- Tidak ada clipping (±3000 µV).
- Power 1–4 Hz naik +2…+11 dB dan 20–34 Hz +2…+7 dB saat TURUN/NAIK dibanding acuan
  (`segmen_indeks_delta_emg.csv`) → campuran artefak gerak lambat dan otot.

## Temuan utama: artefak gerak mengikuti BELAHAN (elektroda referensi telinga)
Saat gerak (TURUN s.d. B), korelasi antar-kanal:

| | dalam belahan kiri (A1) | dalam belahan kanan (A2) | antar belahan |
|---|---|---|---|
| P08 | 0,67 | 0,41 | −0,11 |
| P09 | 0,74 | 0,63 | 0,06 |
| P31 | 0,54 | 0,66 | 0,04 |
| P32 | 0,49 | 0,66 | −0,05 |

Kanal satu belahan bergerak bersama, dua belahan tidak. Belahan yang lebih buruk berbeda per partisipan
(P08 kiri: ptp median 135 vs 75 µV; P31 kanan: 388 vs 107 µV). Pola ini sesuai dengan artefak pada elektroda
telinga A1/A2 (referensi ipsilateral), yang masuk ke semua kanal satu sisi. Sebagian besar artefak gerak
kemungkinan dapat dihapus dengan mengganti referensi, sebelum ICA/ASR (lihat pilihan Tahap 2).

## File
- `jendela_1dtk_label.csv`: label per jendela 1 dtk × kanal.
- `segmen_indeks_delta_emg.csv`: power 1–4 Hz dan 20–34 Hz per segmen × kanal (dB relatif acuan).
- `ringkasan_per_fase.csv`, `ringkasan_per_kanal.csv`.
- `PXX_peta_kualitas.png`: peta kanal × fase (% datar, % > 150 µV).
