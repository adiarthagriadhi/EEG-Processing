# Metode baru: EEG saat gerak berbasis timestamp manual

Analisis ini **berdiri sendiri** dan tidak memakai `eegpipe`. Analisis repo (`hasil_analisis/`, eegpipe v2 dengan
fase dari video/pose) hanya dipakai sebagai **pembanding**. Paket: `gerakeeg/`. Perintah:

```bash
.venv/bin/python analisis_baru/jalankan.py tahap1 P08 P09 P31 P32
.venv/bin/python -m pytest -q analisis_baru/tes
```

Masukan: `data/raw/PXX/PXX_Trial.EDF` dan `data/manual_timestamps/PXX_timestamps.csv`.

## Istilah
Setiap repetisi terdiri dari empat fase berurutan, ditambah dua segmen di luar repetisi.

| Fase | Label timestamp | Jendela observasi (detik EEG, offset 0) | Durasi fase |
|---|---|---|---|
| **Gerak**: Ngeed / Agem Kanan / Agem Kiri | `N` / `AKA` / `AKI` | Gerak − 0,5 … Tahan | Tahan − Gerak |
| **Tahan** | `T` | Tahan − 0,5 … Naik | Naik − Tahan |
| **Naik** | `N` (sesudah `T`) | Naik − 0,5 … Berdiri | Berdiri − Naik |
| **Berdiri** | `B` | Berdiri − 0,5 … Gerak berikutnya (maks. Berdiri + 8 dtk) | Gerak berikutnya − Berdiri |
| **Tutup Mata** | `TT` | TT − 0,5 … TT + 30 | 30 dtk |
| **Istirahat*** | (tidak ada) | Berdiri terakhir blok 1 + 8 … Gerak pertama blok 2 − 5 | ±170 dtk |

*Istirahat adalah turunan (jeda antar-blok, tanpa timestamp) dan hanya dipakai sebagai acuan.

- Setiap jendela dimulai 0,5 dtk sebelum timestamp onsetnya. Durasi fase tetap dihitung dari timestamp.
- Repetisi dinomori per gerakan menurut blok: blok 1 = rep 1–2, blok 2 = rep 3–4. P31 tidak punya Ngeed di
  blok 1, jadi Ngeed-nya rep 3–4.
- Buka mata (Romberg EO) tidak ditandai, sehingga belum dianalisis.
- Urutan label yang menyimpang dicatat di `hasil/tahap1_kualitas/masalah_timestamp.csv`. Pada keempat
  partisipan tidak ada.

## Rencana bertahap
| Tahap | Isi | Status |
|---|---|---|
| 1 | Inventaris kualitas sinyal per fase (tanpa mengubah data) | **Selesai** |
| 2 | Referensi: A rata-rata per belahan · B rata-rata 16 kanal · C bipolar tetangga · D telinga A1/A2 (asli) | Berikutnya |
| 3 | Kanal buruk & sinyal datar: A per rekaman · B per jendela · C interpolasi datar pendek | Menunggu |
| 4 | Lonjakan artefak gerak: A ASR (kalibrasi Istirahat) · B tolak per potongan, ambang per partisipan · C hanya ditandai | Menunggu |
| 5 | Mata & otot: A ICA + ICLabel · B BSS-CCA (otot) · C regresi kedipan Fp1/Fp2 | Menunggu |
| 6 | Aturan pakai jendela & uji sensitivitas | Menunggu |

Setiap tahap diukur ulang dengan inventaris Tahap 1. Tahap berikutnya dimulai setelah hasil disetujui.

---

## Tahap 1: kualitas sinyal per fase
Kode: `gerakeeg/kualitas.py`. Hasil: `hasil/tahap1_kualitas/`.

Sinyal EDF mentah dipakai untuk penanda **datar** (SD < 0,5 µV per 0,2 dtk; reset atau putus kanal KT88) dan
clipping. Sinyal bandpass 1–35 Hz, tanpa ICA dan tanpa interpolasi, dipakai untuk amplitudo dan spektrum.
Setiap jendela observasi dipotong per 1 dtk (geser 0,5 dtk). Tiap potongan × kanal diberi label:

- **ok**: ≤ 100 µV peak-to-peak
- **tinggi**: 100–150 µV
- **ekstrem**: > 150 µV
- **datar**: ≥ 10% sampel datar

### % potongan ok per fase
| Fase | P08 | P09 | P31 | P32 |
|---|---|---|---|---|
| Gerak (Ngeed/Agem) | 22 | 16 | 14 | 3 |
| Tahan | 42 | 22 | 22 | 9 |
| Naik | 23 | 16 | 12 | 10 |
| Berdiri | 44 | 27 | 26 | 15 |
| Tutup Mata | 58 | 78 | 68 | 64 |
| Istirahat* | 57 | 47 | 71 | 51 |

Rincian (`ringkasan_fase.csv`): % ekstrem saat Gerak 46–77, Tahan 19–70, Naik 42–66, Berdiri 27–56; % datar
12–33 di semua fase. Median peak-to-peak per potongan: Gerak 183–457 µV, Tutup Mata 41–71 µV. Tidak ada clipping.

![komposisi](hasil/tahap1_kualitas/komposisi_kualitas_per_fase.png)

### Temuan
1. **Fase gerak hampir tidak bisa dipakai tanpa koreksi.** Saat Gerak dan Naik hanya 3–23% potongan yang ok. Kalau
   aturan tolak konvensional dipakai (jendela utuh ≤ 150 µV dan tidak datar), yang lolos hanya 0–15% jendela ×
   kanal. Artefak perlu dikoreksi (Tahap 2–5), bukan hanya dibuang.
2. **Berdiri belum tenang.** Ok 15–44% dengan 27–56% ekstrem. Gerak belum selesai sesudah B, dan jendelanya
   dimulai 0,5 dtk sebelum B. Berdiri tidak cocok menjadi acuan diam; Istirahat lebih baik (ok 47–71%).
3. **Tutup Mata dan Istirahat relatif bersih** (ok 47–78%). Tutup Mata P09 hanya 14% terekam dan P08 47%, karena EDF
   berhenti sebelum 30 dtk.
4. **Agem lebih buruk daripada Ngeed** (`ringkasan_gerakan_fase.csv`). Ok saat Gerak: Ngeed 3–32%, Agem Kanan 2–16%,
   Agem Kiri 3–22%; saat Tahan: Ngeed 10–56%, Agem 5–46%. Mengangkat lengan kemungkinan menarik kabel elektroda.
5. **Artefak gerak mengikuti belahan kiri/kanan** (elektroda telinga A1/A2). Korelasi antar-kanal saat Gerak:

   | | dalam kiri (A1) | dalam kanan (A2) | antar belahan |
   |---|---|---|---|
   | P08 | 0,69 | 0,36 | −0,13 |
   | P09 | 0,69 | 0,46 | 0,13 |
   | P31 | 0,46 | 0,69 | 0,04 |
   | P32 | 0,51 | 0,54 | −0,02 |

   Belahan yang lebih buruk berbeda per orang. Pada peta kanal (`peta_kanal_pct_ok.png`) saat Gerak/Tahan/Naik:
   P31 belahan kanan 0–14% ok vs kiri 3–53%; P08 sebaliknya, kiri 6–57% vs kanan 21–57% (kiri lebih rendah di
   hampir semua kanal); P32 kedua belahan rendah (0–25%). Ini mendukung Tahap 2 (referensi) dikerjakan lebih dulu.
6. Power 1–4 Hz saat Gerak naik +5…+13 dB dan 20–34 Hz +3…+10 dB dibanding Istirahat → campuran artefak gerak
   lambat dan otot.

![peta kanal](hasil/tahap1_kualitas/peta_kanal_pct_ok.png)

### Pembanding: analisis repo
Jendela analisis repo: fase dari video/pose, offset sinkronisasi repo (P08 0,95; P09 1,70; P31/P32 0,85 dtk),
batas dipangkas 0,25 dtk. Pemetaannya: TURUN ↔ Gerak, TAHAN ↔ Tahan, NAIK ↔ Naik. Repo tidak punya fase Berdiri.

| % ok | P08 repo / baru | P09 | P31 | P32 |
|---|---|---|---|---|
| Gerak | 16 / 22 | 13 / 16 | 13 / 14 | 3 / 3 |
| Tahan | 49 / 42 | 39 / 22 | 23 / 22 | 14 / 9 |
| Naik | 16 / 22 | 16 / 16 | 28 / 12 | 12 / 10 |

- Kualitas di kedua metode setara rendahnya. Perbedaan kualitas bukan alasan memilih salah satu.
- Jendela repo jauh lebih pendek. Median panjang Gerak 0,7–1,3 dtk (repo) vs 2,4–3,7 dtk (baru); Naik 0,5–2,8 vs
  2,1–3,2 dtk. Karena itu aturan "jendela utuh ≤ 150 µV" tampak lebih longgar di repo.
- **Onset Gerak manual 1,2–2,7 dtk lebih awal** daripada onset turun batang tubuh di repo (median per partisipan,
  dalam detik EEG; `pembanding_selisih_onset.csv`). Onset Tahan −0,8…0,0 dtk dan Berdiri −0,1…+0,8 dtk lebih dekat.
  Timestamp manual menandai awal gerak lebih dini, kemungkinan termasuk gerak lengan/persiapan yang tidak
  dianggap "turun" oleh pelacak pose.

![pembanding](hasil/tahap1_kualitas/pembanding_repo_vs_baru.png)

### File
- `repetisi.csv`: onset dan durasi tiap fase per repetisi. `jendela_observasi.csv`: jendela per fase.
- `potongan_1dtk.csv`: label per potongan 1 dtk × kanal.
- `jendela_kanal.csv`: per jendela × kanal: % datar, peak-to-peak, layak_ketat, power 1–4 Hz dan 20–34 Hz (dB
  relatif Istirahat). Berisi juga baris `sumber = repo_video`.
- `jendela.csv`: per jendela: cakupan EDF dan korelasi antar-kanal dalam/antar belahan.
- `ringkasan_fase.csv` (baru + repo), `ringkasan_gerakan_fase.csv`, `ringkasan_kanal_pct_ok.csv`.
- `pembanding_repo_vs_baru.csv`, `pembanding_selisih_onset.csv`, `masalah_timestamp.csv`.
