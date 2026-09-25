# Tahap 1 data cleaning: inventaris kualitas sinyal (P08, P09, P31, P32)

Tahap ini hanya memeriksa dan menandai; data tidak diubah. Skrip: `../skrip/tahap1_kualitas.py`.
Sinyal: EDF mentah (datar, clipping) + bandpass 1–35 Hz (tanpa ICA, tanpa interpolasi). Waktu fase dari
timestamp manual (offset 0). Setiap segmen dipotong per 1 dtk dan tiap jendela × kanal diberi label:
`datar` (≥ 10% sampel datar), `ekstrem` (> 150 µV peak-to-peak), `tinggi` (100–150 µV), `ok`.

## Ringkasan per fase (`ringkasan_per_fase.csv`; % jendela × kanal)
| Fase | datar | > 150 µV | ok | ptp median (µV) |
|---|---|---|---|---|
| PRA (2 dtk sebelum turun) | 19–32 | 7–28 | 28–54 | 38–83 |
| TURUN | 12–19 | 53–80 | 0–16 | 180–402 |
| TAHAN | 16–27 | 18–65 | 10–43 | 61–235 |
| NAIK | 14–33 | 44–68 | 8–17 | 132–280 |
| POST (B + 0,5…2 dtk) | 7–27 | 43–81 | 7–30 | 127–416 |
| ACUAN (berdiri/istirahat) | 9–26 | 9–22 | 43–63 | 38–95 |
| Romberg EC | 6–29 | 4–6 | 57–77 | 31–60 |

- Bila aturan tolak baku (> 150 µV) diterapkan, fase TURUN, NAIK dan POST hampir habis (ok 0–30%). TAHAN
  tersisa 10–43%.
- POST masih penuh artefak: gerak belum selesai 0,5–2 dtk sesudah B.
- Tidak ada clipping (±3000 µV).
- Power 1–4 Hz naik +2…+11 dB dan 20–34 Hz +2…+8 dB saat TURUN/NAIK dibanding acuan
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
