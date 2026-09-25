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
| – | Epoching: B / T / TE / E | **Selesai → TE dipakai** (keputusan pengguna 2026-09-25) |
| 2 | Referensi: A rata-rata per belahan · B rata-rata 16 kanal · C bipolar tetangga · D telinga A1/A2 (asli) | **Selesai → A dipakai** (keputusan pengguna) |
| 3 | Kanal buruk & sinyal datar: per rekaman · per jendela (robust) · referensi median · interpolasi | **Selesai → A2 robust dipakai** (keputusan pengguna) |
| 4 | Lonjakan artefak gerak: ASR k 20/10/5 · ambang adaptif per partisipan · hanya ditandai | **Selesai → ASR k = 20** |
| – | **Rencana beku + verifikasi kohort** (`RENCANA_BEKU.md`, `jalankan.py verifikasi semua`) | **Beku 2026-09-25**; menunggu data semua partisipan |
| – | **Rencana analisis gelombang EEG** (`RENCANA_ANALISIS.md`) | **Draf**; dibekukan sesudah Tahap 5–6 beku, sebelum analisis dijalankan |
| 5 | Mata & otot: ICA (aturan MNE) · BSS-CCA (otot) · regresi kedipan Fp1/Fp2 | **Sementara → usul tanpa koreksi tambahan** (dikonfirmasi pada set penyetelan yang lebih besar) |
| 6 | Aturan pakai: R1 cakupan jendela bersih per repetisi · R2 repetisi minimum per sel; dataset bersih | **Sementara → cakupan ≥ 75% & ≥ 3 repetisi** (dikonfirmasi pada set penyetelan yang lebih besar) |

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

---

## Perbandingan epoching B vs E
Kode: `gerakeeg/epoch.py`. Perintah: `jalankan.py epoch`. Hasil: `hasil/epoch_banding/` (kini juga berisi T dan TE, lihat bagian berikut). Dinilai **sebelum koreksi
artefak**, dengan aturan bersih yang sama per kanal: datar < 10% dan peak-to-peak ≤ 150 µV.

- **B**: satu epoch tetap 1,5 dtk per fase, [onset − 0,5, onset + 1,0]. Fase lebih pendek dari 1 dtk tidak dipakai
  (2 dari 184 fase).
- **E**: jendela 1 dtk bergeser 0,25 dtk sepanjang rekaman. Jendela diberi label fase bila seluruhnya berada di
  dalam jendela observasi fase itu; jendela yang melintasi batas fase dibuang. Nilai per repetisi = rata-rata
  power jendela yang bersih.
- Power theta/mu/beta dalam dB relatif Istirahat, yang dipotong dengan cara yang sama. Unit independen tetap
  repetisi: jendela E yang tumpang tindih tidak dihitung sebagai sampel terpisah.

| Ukuran (rentang 4 partisipan) | Fase | B | E |
|---|---|---|---|
| Detik data bersih per kanal (median) | Gerak | 1,5–9 | 2,5–18 |
| | Tahan | 0–6 | 8,5–45 |
| | Naik | 1,5–6 | 3,8–10 |
| | Berdiri | 0–3 | 32–64 |
| Bagian jendela observasi yang terpakai | semua | 0,18–0,71 | 0,87–0,97 |
| Repetisi valid per kanal (median) | Tahan | 0–4 | 4–12 |
| % kanal dengan ≥ 3 repetisi valid | Gerak / Tahan | 0–88 / 0–81 | 38–100 / 81–100 |
| Galat baku power (dB, median) | Tahan | 1,5–2,0 (P32: tak terhitung) | 0,9–1,7 |
| Reliabilitas belah-dua pola kanal × pita | Gerak / Tahan | 0,45–0,69 / −0,29–0,71 | 0,65–0,94 / 0,57–0,97 |

- **E unggul di hampir semua ukuran.** E menghasilkan 2–10× lebih banyak data bersih dan memakai hampir seluruh
  fase (87–97%, B hanya 18–71%). E juga lebih presisi dan polanya lebih konsisten antar-repetisi. Pada P32 (sinyal
  paling buruk), B praktis tidak menghasilkan estimasi untuk Gerak, Tahan dan Berdiri; E masih menghasilkan.
- **Naik tetap lemah di kedua cara.** Datanya sedikit (3,8–10 dtk bersih) dan reliabilitasnya tidak stabil
  (−0,40…0,83). Fase ini paling pendek dan paling berartefak.
- **Kelemahan E yang perlu diingat:**
  1. E hanya memakai bagian fase yang bersih. Bila bagian bersih cenderung jatuh di sub-periode tertentu (mis. akhir
     Tahan yang lebih stabil), estimasinya mewakili "bagian tenang" fase itu, bukan seluruh fase.
  2. Aturan ≤ 150 µV diterapkan pada 1 dtk (E) vs 1,5 dtk (B), sehingga B sedikit lebih ketat.
  3. Resolusi frekuensi 1 Hz (jendela 1 dtk) cukup untuk mu/beta; theta 4–8 Hz hanya berisi 4 titik frekuensi.
- Perbandingan ini dibuat sebelum koreksi artefak dan perlu diulang sesudah Tahap 2–5. Bila koreksi berhasil,
  keunggulan jumlah data E akan mengecil, tetapi cakupan fase E tetap lebih besar.


---

## Bagian fase mana yang paling informatif: pra-onset, awal, tengah, akhir
Kode: `gerakeeg/posisi.py`. Perintah: `jalankan.py bagian`. Hasil: `hasil/bagian_fase/`.

Tiap fase dibagi menjadi pra-onset (0,5 dtk sebelum timestamp) dan tiga sepertiga sama panjang (awal, tengah,
akhir). Diukur sebelum koreksi artefak:

| Median 4 partisipan | Gerak pra / awal / tengah / akhir | Tahan | Naik | Berdiri |
|---|---|---|---|---|
| % potongan 0,5 dtk bersih | **63 / 49** / 28 / 29 | 31 / 40 / **51 / 54** | **51 / 42** / 29 / 23 | 23 / 33 / **55 / 67** |
| Otot 20–34 Hz (dB vs Istirahat) | **−0,1 / 2,2** / 6,4 / 6,9 | 6,7 / 4,7 / **2,0 / 1,9** | **2,2 / 3,6** / 7,8 / 8,5 | 8,7 / 5,2 / **1,9 / −0,2** |
| Delta 1–4 Hz (dB) | **1,8 / 7,7** / 15,0 / 13,9 | 12,1 / 10,7 / **4,4 / 3,7** | **4,1 / 5,4** / 10,6 / 17,1 | 15,6 / 12,8 / **5,3 / 0,9** |
| Mu C3/C4 (dB) | −0,8 / 0,2 / 2,4 / 0,1 | −0,5 / −0,4 / −1,1 / −0,7 | −1,3 / 0,6 / 1,7 / 0,7 | 0,1 / 0,6 / −0,1 / −0,8 |
| Beta C3/C4 (dB) | −1,1 / −0,8 / 0,8 / −0,2 | −1,3 / −1,2 / −0,5 / −1,1 | −1,6 / −1,2 / 0,1 / −0,3 | −0,1 / −0,4 / 0,2 / −0,7 |

(Pra-onset Tahan = akhir Gerak; pra-onset Naik = akhir Tahan; pra-onset Berdiri = akhir Naik.)

**Pola kualitas sangat konsisten di keempat partisipan** (`profil_bagian_fase.png`): kontaminasi otot dan gerak
lambat naik tajam begitu tubuh bergerak (tengah-akhir Gerak dan Naik), lalu turun lagi selama Tahan dan Berdiri.

| Fase | Bagian terbaik | Alasan |
|---|---|---|
| Gerak | **pra-onset + awal** | Paling bersih (63/49%). Otot ≈ 0–2 dB. Beta sensorimotor sudah turun (−1,1 dB) → ERD persiapan/inisiasi gerak. Tengah-akhir didominasi artefak (otot +6–7 dB, delta +14–15 dB). |
| Tahan | **tengah + akhir** | Awal masih membawa artefak dari Gerak (otot +4,7 dB). Tengah-akhir paling stabil (51–54% bersih, otot ≈ 2 dB); mu −1,1 dB dan beta −1,1 dB = ERD selama menahan. |
| Naik | **pra-onset + awal** | Sama dengan Gerak: inisiasi paling bersih (51/42%); sesudahnya artefak naik tajam. |
| Berdiri | **akhir** (dan tengah) | Awal masih penuh artefak dari Naik (otot +5–9 dB), jadi *beta rebound* sesudah gerak tidak dapat dinilai. Akhir hampir setara Istirahat (67% bersih, otot ≈ 0 dB). |

**Konsekuensi untuk metode E:** jendela bersih E tidak tersebar merata. Pada Gerak, 63% jendela bersih berasal dari
bagian awal, padahal bagian awal hanya 45% dari waktu. Pada Naik 65% vs 49%. Pada Berdiri 80% berasal dari tengah-
akhir. Jadi E diam-diam menjadi "awal Gerak", "awal Naik" dan "akhir Berdiri", dengan porsi yang berbeda per repetisi
dan per orang. Gambaran fasenya tidak lagi seragam.

**Batasan:** nilai mu/beta masih kecil dan belum konsisten antar-repetisi (|t| < 1,5). Arah per partisipan juga
bervariasi. P32 menunjukkan nilai sangat negatif karena acuan Istirahat-nya sendiri berartefak. Pola sinyal EEG
ini harus diuji ulang sesudah koreksi artefak; pola kualitasnya sudah jelas sekarang.

![profil](hasil/bagian_fase/profil_bagian_fase.png)

---

## Perbandingan epoching: B vs T (terarah) vs TE vs E
Kode: `gerakeeg/epoch.py`. Perintah: `jalankan.py epoch`. Hasil: `hasil/epoch_banding/`. Aturan bersih dan acuan
Istirahat sama untuk semua metode; sebelum koreksi artefak.

| Metode | Gerak | Tahan | Naik | Berdiri |
|---|---|---|---|---|
| **B** tetap 1,5 dtk | onset − 0,5 … + 1,0 | onset − 0,5 … + 1,0 | onset − 0,5 … + 1,0 | onset − 0,5 … + 1,0 |
| **T** terarah 1,5 dtk | = B (inisiasi) | 1,5 dtk di tengah fase | = B (inisiasi) | 2,0 … 0,5 dtk sebelum Gerak berikut |
| **TE** jendela geser 1 dtk di bagian informatif | onset − 0,5 … onset + maks(1; durasi/3) | tengah + akhir | seperti Gerak | tengah + akhir (sampai 0,5 dtk sebelum Gerak berikut) |
| **E** jendela geser 1 dtk | seluruh fase | seluruh fase | seluruh fase | seluruh fase |

Median 4 partisipan (`ringkasan_epoch.csv`):

| Ukuran | Fase | B | T | TE | E |
|---|---|---|---|---|---|
| % kanal-epoch bersih | Gerak | 25 | 25 | **36** | 26 |
| | Tahan | 19 | 35 | **42** | 37 |
| | Naik | 24 | 24 | **32** | 22 |
| | Berdiri | 10 | **51** | **51** | 40 |
| Otot 20–34 Hz (dB vs Istirahat) | Gerak | 3,4 | 3,4 | **1,7** | 4,8 |
| | Tahan | 7,0 | 2,7 | **2,1** | 3,0 |
| | Naik | 4,2 | 4,2 | **3,1** | 4,9 |
| | Berdiri | 8,7 | **0,5** | 1,1 | 2,3 |
| Detik data bersih per kanal | Gerak / Tahan / Naik / Berdiri | 3 / 2 / 4 / 2 | 3 / 6 / 4 / 10 | 6 / 14 / 5 / 25 | **12 / 23 / 8 / 39** |
| % kanal ≥ 3 repetisi bersih | Gerak / Tahan / Naik / Berdiri | 47 / 44 / 59 / 13 | 47 / 66 / 59 / 94 | 81 / **100** / 88 / **100** | 84 / **100** / **100** / **100** |
| Galat baku power (dB) | Gerak / Tahan / Naik / Berdiri | 1,7 / 1,5 / 1,4 / 1,5 | 1,7 / 1,6 / 1,4 / 1,3 | 1,8 / 1,5 / 1,5 / 1,1 | 1,4 / 1,2 / 1,6 / 1,0 |
| Reliabilitas belah-dua | Gerak / Tahan / Naik / Berdiri | 0,6 / 0,2 / 0,6 / 0,2 | 0,6 / 0,0 / 0,6 / 0,6 | **0,8** / 0,6 / 0,4 / 0,8 | **0,8** / **0,8** / 0,3 / **0,9** |

- **T** memperbaiki B dengan jelas pada fase yang bergeser: Tahan (otot 7,0 → 2,7 dB) dan Berdiri (8,7 → 0,5 dB; kanal
  bersih 10 → 51%). Tetapi hanya satu epoch 1,5 dtk per repetisi, sehingga datanya sedikit dan reliabilitas Tahan
  rendah (median 0,0).
- **TE paling bersih dan paling seragam** di hampir semua fase: kanal bersih tertinggi dan kontaminasi otot terendah
  pada Gerak, Tahan dan Naik. Datanya 1,4–2,5× lebih banyak dari T. Reliabilitasnya mendekati E (Gerak 0,8; Berdiri 0,8),
  kecuali Tahan (0,6 vs 0,8).
- **E** tetap menang pada jumlah data dan galat baku, tetapi kontaminasi ototnya lebih tinggi dan isinya mencampur
  bagian fase yang berbeda (lihat bagian sebelumnya).
- **Naik** tetap fase terlemah di semua metode (reliabilitas 0,3–0,6).
- Usulan: **TE sebagai epoching utama**, E dan T sebagai uji sensitivitas. Perbandingan diulang sesudah koreksi
  artefak (Tahap 2–5).

![epoch banding](hasil/epoch_banding/epoch_banding.png)

---

## Tahap 2: skema referensi (dinilai dengan epoch TE)
Kode: `gerakeeg/referensi.py`. Perintah: `jalankan.py tahap2`. Hasil: `hasil/tahap2_referensi/`.

Referensi diterapkan per jendela 1 dtk. Kanal yang datar di jendela itu tidak ikut membentuk referensi, sehingga
kanal yang sedang reset/putus tidak mencemari kanal lain. Acuan Istirahat dihitung dengan skema yang sama.

| Median 4 partisipan | Fase | D telinga (asli) | **A rata-rata belahan** | B rata-rata 16 | C bipolar |
|---|---|---|---|---|---|
| % kanal-jendela bersih | Gerak / Tahan / Naik / Berdiri | 36 / 42 / 32 / 51 | **56 / 60 / 51 / 65** | 34 / 44 / 35 / 56 | 37 / 42 / 33 / 49 |
| Otot 20–34 Hz (dB) | Gerak / Tahan / Naik / Berdiri | 1,7 / 2,1 / 3,1 / 1,1 | **1,0 / 1,2 / 2,3 / 0,4** | 2,3 / 2,7 / 3,4 / 1,1 | 1,4 / 1,7 / 2,6 / 0,8 |
| Detik bersih per kanal | Gerak / Tahan / Naik / Berdiri | 6 / 14 / 5 / 25 | **9 / 19 / 8 / 30** | 6 / 15 / 5 / 28 | 5 / 14 / 5 / 25 |
| Galat baku power (dB) | Gerak / Tahan / Naik / Berdiri | 1,8 / 1,5 / 1,5 / 1,1 | **1,3 / 1,3** / 1,6 / **1,0** | 1,4 / 1,4 / 1,8 / 1,0 | 1,6 / 1,4 / 1,6 / 1,0 |
| Reliabilitas belah-dua | Gerak / Tahan / Naik / Berdiri | 0,75 / 0,62 / 0,36 / 0,80 | **0,76 / 0,78 / 0,74 / 0,85** | 0,55 / 0,72 / 0,55 / 0,78 | 0,66 / 0,70 / −0,18 / 0,74 |
| Korelasi dalam belahan | semua fase | 0,51–0,64 | −0,15…−0,09 | 0,26–0,52 | −0,08…−0,02 |
| Korelasi antar belahan | semua fase | −0,10…0,02 | 0,00 | **−0,48…−0,42** | 0,01–0,02 |

- **A (rata-rata per belahan) unggul di semua ukuran data.** Persentase bersih naik +13…+21 poin. Kontaminasi otot
  turun. Reliabilitas Naik naik dari 0,36 ke 0,74, jadi Naik kini dapat dianalisis. Korelasi dalam belahan hilang:
  nilai sekitar −0,1 adalah nilai bawaan rata-rata referensi (≈ −1/7). Artefak bersama dari A1/A2 memang terhapus.
- **B (rata-rata 16 kanal) justru menyebarkan artefak.** Artefak A1 dikurangkan juga dari kanal kanan, sehingga muncul
  korelasi negatif antar belahan (−0,4…−0,5). Perolehan datanya kecil.
- **C (bipolar) menghapus artefak bersama**, tetapi kanal bersih tidak bertambah dan Naik menjadi tidak reliabel
  (−0,18). Selisih dua kanal yang sama-sama bising tetap bising.
- Keseimbangan belahan dengan A: kanal bersih saat Gerak kiri 69%, kanan 38% (D: 34% vs 19%). Belahan kanan tetap
  lebih buruk (`korelasi_belahan.csv`), yang merupakan sasaran Tahap 3–5.

**Konsekuensi A yang harus diingat saat menafsirkan:**
1. Aktivitas otak yang merata di satu belahan ikut terhapus. Yang tersisa adalah perbedaan antar-kanal di dalam
   belahan, sehingga ERD yang fokal (mis. C3 lebih kuat daripada kanal lain di kiri) tetap terlihat, sedangkan ERD
   yang merata di seluruh belahan tidak.
2. Indeks lateralisasi (C3 vs C4) kini membandingkan C3 relatif belahan kiri dengan C4 relatif belahan kanan, bukan
   potensial mentah. Nilainya tidak dapat dibandingkan langsung dengan analisis repo.
3. Kanal yang ≥ 10% datar tidak ikut membentuk referensi. Bila kurang dari 2 kanal tidak-datar dalam satu belahan,
   seluruh belahan dianggap hilang di jendela itu.

**Uji Berger tidak informatif.** Alpha oksipital relatif saat Tutup Mata TIDAK lebih tinggi daripada Istirahat di
skema mana pun, termasuk telinga asli (−1,8…−0,02 dB). Masalahnya ada di data, bukan di referensi. Kemungkinannya:
(a) alpha memang lemah pada rekaman ini, sesuai catatan repo sebelumnya (tidak ada puncak alpha jelas); (b) kondisi
mata saat Istirahat tidak diketahui, bisa saja sebagian partisipan menutup mata; (c) P09 hanya 7 jendela Tutup Mata.
Perlu konfirmasi ke pengguna: apakah mata terbuka saat Istirahat utama?

![tahap 2](hasil/tahap2_referensi/tahap2_referensi.png)

---

## Tahap 3: kanal buruk & sinyal datar (referensi A, epoch TE)
Kode: `gerakeeg/kanal.py`. Perintah: `jalankan.py tahap3`. Hasil: `hasil/tahap3_kanal/`.

| Varian | Isi |
|---|---|
| A0 dasar | Referensi A apa adanya (Tahap 2) |
| A1 per rekaman | Kanal dengan z robust log-SD saat Istirahat > 3, atau datar > 50% rekaman, dibuang dari seluruh rekaman |
| A2 robust per jendela | Di tiap jendela, kanal pencilan (z robust log-ptp > 3 DAN > 2× median belahan) dikeluarkan dari referensi belahan dan ditandai hilang; iteratif |
| A3 referensi median | Referensi = median kanal belahan (kebal pencilan tanpa membuang kanal) |
| A4 robust + interpolasi | A2, lalu kanal yang hilang diisi spline sferis dari kanal belahan yang sama (bila ≥ 5 dari 8 baik) |

**Dari mana data hilang** (`nasib_kanal_jendela.csv`, % kanal-jendela TE):

| | P08 | P09 | P31 | P32 |
|---|---|---|---|---|
| Datar di EDF mentah (reset/putus kanal) | 25,3 | 23,2 | 17,5 | 24,1 |
| Dikeluarkan sebagai pencilan (A2) | 1,7 | 4,7 | 3,5 | 3,9 |
| Diisi interpolasi (A4) | 6,4 | 7,4 | 8,1 | 9,8 |

Kehilangan terbesar adalah **sinyal datar**, dan ini tidak dapat dipulihkan. 69% waktu datar berasal dari rentang
≥ 3 dtk, dan pada 14–22% waktu ada ≥ 6 kanal datar bersamaan. Tidak ada kanal yang buruk sepanjang rekaman (z
maksimum 1,05–1,68), sehingga A1 identik dengan A0.

**Median 4 partisipan, Gerak / Tahan / Naik / Berdiri:**

| | A0 dasar | A1 rekaman | **A2 robust** | A3 median | A4 robust + interp |
|---|---|---|---|---|---|
| % kanal-jendela bersih | 56 / 60 / 51 / 65 | = A0 | 56 / 59 / 52 / 64 | 56 / 58 / 49 / 64 | 64 / 65 / 56 / 70* |
| Otot 20–34 Hz (dB) | 0,97 / 1,23 / 2,30 / 0,40 | = A0 | **0,82 / 1,00 / 1,86 / 0,18** | 1,52 / 1,26 / 2,23 / 0,62 | 0,87 / 0,90 / 2,14 / 0,05 |
| Galat baku (dB) | 1,30 / 1,32 / 1,62 / 1,00 | = A0 | 1,40 / 1,35 / 1,61 / 1,06 | 1,45 / 1,41 / 1,65 / 1,07 | 1,33 / 1,25 / 1,56 / 0,99 |
| Reliabilitas belah-dua | 0,76 / 0,78 / 0,74 / 0,85 | = A0 | 0,77 / 0,78 / 0,76 / 0,86 | 0,72 / 0,78 / 0,64 / 0,90 | 0,72 / 0,80 / 0,73 / 0,89 |

\* A4 menghitung kanal hasil interpolasi sebagai data; isinya turunan kanal tetangga, bukan informasi baru.

- **Perbedaan antar-varian kecil.** Referensi A sudah menangani sebagian besar masalah di Tahap 2.
- **A2 robust** menurunkan kontaminasi otot di semua fase (−0,15…−0,45 dB) dengan biaya 2–5% kanal-jendela.
  Reliabilitas tetap atau sedikit naik. Manfaat utamanya: satu kanal yang meledak tidak lagi mencemari 7 kanal lain
  di belahannya lewat rata-rata referensi.
- **A3 median** lebih buruk (otot Gerak naik, reliabilitas Naik 0,64).
- **A4 interpolasi** tampak menambah data, tetapi hanya mengisi kanal kosong dengan tiruan tetangganya. Reliabilitas
  Gerak justru turun (0,72). Cocok hanya untuk analisis yang butuh montase lengkap (mis. topografi), dengan penanda.
- Catatan: algoritme A2 sempat mengeluarkan kanal normal secara berlebihan (MAD sangat kecil setelah pencilan
  pertama dibuang). Ini ditemukan lewat uji sintetis dan diperbaiki dengan syarat tambahan "> 2× median".

**Usul: A2 robust sebagai baku**, A4 hanya untuk topografi (ditandai).

![tahap 3](hasil/tahap3_kanal/tahap3_kanal.png)

---

## Tahap 4: lonjakan artefak gerak (epoch TE, referensi A2)
Kode: `gerakeeg/lonjakan.py`. Perintah: `jalankan.py tahap4`. Hasil: `hasil/tahap4_lonjakan/`.

| Varian | Isi |
|---|---|
| tandai | Tanpa koreksi; potongan > 150 µV hanya ditandai tidak bersih (hasil Tahap 3) |
| ASR k = 20 / 10 / 5 | Artifact Subspace Reconstruction pada sinyal kontinu, per belahan, sebelum referensi A2. Dikalibrasi dari potongan Istirahat yang kedelapan kanalnya bersih (20–118 dtk per belahan). k kecil = lebih agresif |
| ambang adaptif | Tanpa koreksi; ambang tolak per partisipan × kanal = median + 3 MAD log-ptp Istirahat (50–300 µV) |

**ASR ditulis sendiri** (`asr_kalibrasi`, `asr_proses`, mengikuti algoritme Kothe & Mullen tanpa filter pembobot
spektral). ASR dari pustaka meegkit 0.2 ditolak karena mengubah data kalibrasi yang bersih (r 0,54–0,91 dengan
aslinya) dan hasilnya tidak berubah dengan k pada data 100 Hz. Verifikasi implementasi sendiri (uji sintetis):
data bersih utuh (r = 1,000), artefak besar tersisa 3–16% energinya, artefak kecil dibiarkan.

Median 4 partisipan, Gerak / Tahan / Naik / Berdiri:

| | tandai | **ASR 20** | ASR 10 | ASR 5 | adaptif |
|---|---|---|---|---|---|
| % kanal-jendela bersih | 56 / 59 / 52 / 64 | 65 / 65 / 56 / 69 | 70 / 69 / 64 / 71 | 72 / 73 / 69 / 75 | 47 / 57 / 52 / 63 |
| Otot 20–34 Hz (dB) | 0,82 / 1,00 / 1,86 / 0,18 | 0,72 / 0,72 / 1,84 / 0,13 | 0,56 / 0,34 / 1,22 / −0,01 | 0,16 / −0,14 / 0,34 / **−0,86** | 0,75 / 0,86 / 1,78 / 0,14 |
| Galat baku (dB) | 1,40 / 1,35 / 1,61 / 1,06 | 1,36 / 1,27 / 1,54 / 1,04 | 1,25 / 1,21 / 1,42 / 1,02 | 1,20 / 1,06 / 1,32 / 0,92 | 1,32 / 1,32 / 1,48 / 1,05 |
| Reliabilitas belah-dua | 0,77 / 0,78 / 0,76 / 0,86 | 0,78 / 0,79 / **0,80** / 0,86 | 0,80 / 0,84 / 0,68 / 0,86 | 0,80 / 0,81 / 0,63 / 0,86 | 0,70 / 0,76 / 0,55 / 0,78 |
| % waktu direkonstruksi (per belahan) | – | 5–32 | 10–40 | 21–54 | – |
| Perubahan power Istirahat (dB) | 0 | 0,00 | ≤ 0,02 | −0,25…−0,02 | ≤ 0,11 |

- **ASR 20 (konservatif)** menambah data bersih +4…+9 poin tanpa menyentuh Istirahat (0,00 dB). Semua reliabilitas
  tetap atau naik, termasuk Naik 0,76 → 0,80.
- **ASR 10** membersihkan lebih banyak (otot Tahan 1,00 → 0,34 dB) dan Istirahat tetap utuh, tetapi reliabilitas
  Naik turun (0,76 → 0,68) dan 10–40% waktu direkonstruksi.
- **ASR 5 terlalu agresif.** Otot Berdiri turun di bawah Istirahat (−0,86 dB), Istirahat ikut berubah, Naik 0,63, dan
  sampai 54% waktu direkonstruksi. Kemungkinan besar ikut membuang aktivitas otak.
- **Ambang adaptif lebih buruk.** Ambang Istirahat P08 hanya ±77 µV, sehingga lebih banyak data terbuang tanpa
  peningkatan kualitas.
- Risiko ASR pada tugas gerak: perubahan EEG yang besar dan wajar (mis. *rebound* beta sesudah gerak) juga
  "bervarians tinggi" dibanding Istirahat dan dapat ikut direkonstruksi. Makin kecil k, makin besar risikonya.
  Karena itu dipilih k konservatif.

**Usul: ASR k = 20 sebagai baku, ASR k = 10 sebagai uji sensitivitas.**

![tahap 4](hasil/tahap4_lonjakan/tahap4_lonjakan.png)

---

## Gelombang EEG per tahap proses
Perintah: `jalankan.py gelombang` (baku: Agem Kanan repetisi 1). Hasil: `hasil/gelombang/PXX_Agem_Kanan_rep1.png`.

Tiga panel per partisipan:
1. asli (referensi telinga, 1–35 Hz);
2. + ASR k = 20;
3. + referensi A2, yang menjadi masukan analisis.

Latar = fase; batang di atas = rentang epoch TE; hitam = potongan 1 dtk ≤ 150 µV; merah = > 150 µV; abu-abu = datar atau
kanal hilang. Untuk tampilan, A2 diterapkan per blok 1 dtk berurutan. Dalam analisis, A2 diterapkan per jendela TE
(geser 0,25 dtk), sehingga batas blok pada gambar bisa sedikit berbeda.

---

## Tahap 5 (SEMENTARA): artefak mata & otot di atas pipeline beku
Kode: `gerakeeg/mata_otot.py`. Perintah: `jalankan.py tahap5`. Hasil: `hasil/tahap5_mata_otot/`. Belum dibekukan. Sesuai
RENCANA_BEKU, keputusan akhir diambil pada set penyetelan yang lebih besar.

| Varian | Isi |
|---|---|
| dasar | Pipeline beku (ASR k 20 → A2), tanpa koreksi tambahan |
| ICA mata | ICA Picard 15 komponen pada sinyal kontinu sesudah ASR; komponen kedipan = z korelasi dengan Fp1/Fp2 > 3 |
| ICA mata + otot | + komponen otot (MNE `find_bads_muscle`, 7–34 Hz) |
| CCA otot | BSS-CCA per jendela; komponen dengan rasio 20–34 / 2–15 Hz di atas persentil 95 Istirahat dibuang |
| regresi mata | Proksi EOG = rata-rata Fp1/Fp2 (1–7 Hz), koefisien dari Istirahat; Fp1/Fp2 lalu dikeluarkan |
| ICA mata + CCA otot | gabungan |

ICLabel tidak dipakai, karena dilatih pada data ≥ 32 kanal dengan rentang 1–100 Hz. Data ini 16 kanal, 100 Hz, dan
dibatasi perangkat ±35 Hz.

**Kedipan sudah banyak berkurang sebelum Tahap 5.** Median |r| antara proksi kedipan (Fp1/Fp2 asli) dan F3/F4/F7/F8 pada
jendela TE yang berisi kedipan:

| | asli | + ASR | + ASR + A2 (dasar) | ICA mata | regresi mata |
|---|---|---|---|---|---|
| P08 | 0,31 | 0,29 | 0,18 | 0,17 | 0,35 |
| P09 | 0,48 | 0,44 | 0,29 | 0,29 | 0,30 |
| P31 | 0,54 | 0,23 | 0,18 | 0,18 | 0,24 |
| P32 | 0,25 | 0,20 | 0,24 | 0,22 | 0,22 |

Median 4 partisipan, Gerak / Tahan / Naik / Berdiri:

| | dasar | ICA mata | ICA mata + otot | CCA otot | regresi mata | ICA mata + CCA otot |
|---|---|---|---|---|---|---|
| % kanal-jendela bersih | 65 / 65 / 56 / 69 | 66 / 65 / 56 / 69 | 67 / 66 / 57 / 69 | 66 / 65 / 57 / 69 | 56 / 56 / 49 / 59 | 67 / 65 / 57 / 69 |
| Otot 20–34 Hz (dB)* | 0,72 / 0,72 / 1,84 / 0,13 | 0,72 / 0,72 / 1,78 / 0,13 | 0,64 / 0,76 / 1,78 / 0,16 | 0,82 / 0,94 / 2,25 / 0,22 | 0,45 / 0,82 / 1,72 / −0,02 | 0,98 / 0,94 / 2,17 / 0,22 |
| Galat baku (dB) | 1,36 / 1,27 / 1,54 / 1,04 | 1,33 / 1,22 / 1,61 / 0,99 | 1,33 / 1,22 / 1,64 / 0,99 | 1,31 / 1,25 / 1,54 / 1,04 | 1,44 / 1,32 / 1,61 / 1,11 | 1,34 / 1,25 / 1,61 / 0,97 |
| Reliabilitas belah-dua | 0,78 / 0,79 / 0,80 / 0,86 | 0,80 / 0,79 / 0,75 / 0,86 | 0,80 / 0,79 / 0,74 / 0,86 | 0,83 / 0,80 / 0,77 / 0,87 | 0,72 / 0,77 / 0,76 / 0,84 | 0,85 / 0,80 / 0,76 / 0,87 |

\* relatif terhadap Istirahat hasil varian yang sama. CCA menurunkan otot Istirahat sendiri (−0,4…−0,9 dB), sehingga angka
relatifnya naik walaupun otot saat tugas juga turun.

- **ICA hampir tidak berbuat apa-apa.** Komponen kedipan hanya ditemukan pada 2 dari 4 partisipan (P08, P32), dan komponen
  otot pada 1 (P31). ICA juga hanya dapat dipasang pada sampel tanpa kanal datar (155–267 dtk), sehingga koreksinya hanya
  berlaku pada 36–64% waktu. Akibatnya perlakuan antar-bagian rekaman tidak seragam.
- **CCA otot** sedikit menaikkan reliabilitas Gerak (0,78 → 0,83), tetapi juga menghapus aktivitas 20–34 Hz saat Istirahat
  (−0,4…−0,9 dB). Pita beta atas ikut terkena, dan ini berisiko untuk ERD beta.
- **Regresi mata lebih buruk.** Fp1/Fp2 hilang, data bersih turun ±10 poin, dan sisa kedipan P08 malah naik (0,18 → 0,35).
- **Usul (sementara): tidak ada koreksi mata/otot tambahan pada pipeline utama.** ICA mata dipakai sebagai uji sensitivitas.
  Kanal frontopolar dan frontotemporal (Fp, F7/F8, T3/T4) tetap ditandai rawan artefak saat penafsiran.

![tahap 5](hasil/tahap5_mata_otot/tahap5_mata_otot.png)

---

## Tahap 6 (SEMENTARA): aturan pakai & dataset bersih
Kode: `gerakeeg/aturan.py`. Perintah: `jalankan.py tahap6`. Hasil: `hasil/tahap6_aturan/`. Ini masih **persiapan data**:
nilai dB di dataset belum ditafsirkan dan belum dibandingkan antar-fase atau antar-grup.

**Aturan:**
- **R1 (nilai repetisi × fase × kanal):** rata-rata power (linear) jendela TE bersih dipakai bila jendela bersih
  menutupi ≥ c_min dari rentang TE fase itu. Dipakai aturan cakupan, bukan jumlah jendela tetap, karena rentang TE
  Gerak/Naik hanya ±1,5–1,8 dtk (3–4 jendela), sedangkan Tahan/Berdiri 3–6 dtk. Aturan cakupan juga menjamin nilai
  mewakili bagian fase yang ditargetkan, bukan satu potongan kecil.
- **R2 (nilai partisipan × fase × kanal):** dipakai bila ≥ r_min repetisi lolos R1. Nilai = rata-rata dB antar-repetisi
  dan SE antar-repetisi, untuk semua gerakan gabungan dan per gerakan.
- **Tutup Mata:** jendela 1 dtk (TT + 1 … TT + 30, dalam EDF); nilai kanal dipakai bila ≥ 8 jendela bersih.
- **Pemilihan (ditetapkan sebelum melihat hasil):** c_min terbesar dari {0, 25, 50, 75%} yang masih menyisakan
  ≥ 75% sel lolos R2 (median 4 fase) dengan r_min = 3.

**Hasil:**

| % sel partisipan × fase × kanal dengan ≥ 3 repetisi | Gerak | Tahan | Naik | Berdiri |
|---|---|---|---|---|
| cakupan ≥ 0% (≥ 1 jendela) | 94 | 100 | 100 | 100 |
| cakupan ≥ 50% | 94 | 100 | 100 | 100 |
| **cakupan ≥ 75% (terpilih)** | 94 | 97 | 100 | 95 |

| Per partisipan, % kanal lolos (terpilih) | Gerak | Tahan | Naik | Berdiri | Tutup Mata |
|---|---|---|---|---|---|
| P08 | 100 | 100 | 100 | 100 | 100 |
| P09 | 100 | 100 | 100 | 94 | – (EDF hanya mencakup 14%) |
| P31 | 100 | 100 | 100 | 100 | 100 |
| P32 | 80 | 88 | 100 | 88 | 100 |

**Presisi nilai repetisi** (`R1_presisi_vs_n.csv`): galat RMS nilai repetisi terhadap nilai dari semua jendela bersih
turun dari ±3,5 dB (1 jendela) ke ±1,4–1,7 dB (6 jendela; Tahan/Berdiri). SD antar-repetisi ±3,2–3,9 dB per fase. Jadi
variasi antar-repetisi lebih besar daripada galat pengambilan jendela, dan jumlah repetisi (R2) lebih menentukan
presisi nilai partisipan daripada jumlah jendela per repetisi. Kurva hanya dapat dihitung untuk Tahan dan Berdiri
(butuh sel dengan ≥ 8 jendela bersih).

Percobaan pertama memakai "≥ n jendela bersih" dengan n dari kurva presisi (n = 6). Aturan itu ditolak karena Gerak dan
Naik tidak pernah punya 6 jendela dalam rentang TE, sehingga kedua fase akan hilang seluruhnya.

**Dataset bersih** (`hasil/tahap6_aturan/dataset/`):
- `nilai_repetisi.csv`: partisipan × gerakan × repetisi × fase × kanal: n jendela, n bersih, detik bersih, rentang,
  cakupan, theta/mu/beta/otot dB (relatif Istirahat), `lolos_R1`.
- `nilai_partisipan.csv`: partisipan × fase × kanal × gerakan (Semua / Ngeed / Agem Kanan / Agem Kiri): n repetisi,
  rata-rata dB dan SE per pita, `lolos_R2`.
- `repetisi_perilaku.csv`: onset dan durasi fase per repetisi (dari timestamp).

![tahap 6](hasil/tahap6_aturan/tahap6_aturan.png)
