# Pipeline EEG–Video: Movement Generation Process pada Penari vs Non-Penari

## Konteks Ilmiah
Studi ini membandingkan proses pembangkitan gerakan kortikal (*movement generation
process*) pada penari Bali ahli (n=24) vs non-penari (n=14, sebagian menjalani
intervensi latihan tari 6 minggu). Task: standing stork test, gerakan ngeed/agem
kanan/agem kiri (4 repetisi, EEG direkam), dan tes Romberg (mata terbuka/tertutup,
EEG masih terpasang). Kerangka analisis utama untuk segmen gerakan (ngeed/agem):
**ERD/ERS** (event-related desynchronization/synchronization) pada pita mu
(8–13 Hz) dan beta (13–30 Hz) di proksi sensorimotor (C3/C4), dengan tambahan
P3/P4 dan O1/O2 untuk komponen kontrol akurasi visuospasial/posterior. Detail
konsep ada di bawah pada bagian "Kerangka ERD/ERS".

**Ruang lingkup data dua jalur (dikonfirmasi pengguna):**
1. **Jalur EEG+video** (dicakup pipeline ini): resting baseline + gerakan
   ngeed/agem kanan/agem kiri + Romberg (mata terbuka/tertutup) — semua dalam
   satu sesi rekaman `PXX_Trial.EDF` + video pendamping.
2. **Jalur Standing Stork Test** (di luar cakupan pipeline EEG ini): **direkam
   terpisah, TIDAK dalam sesi EEG**. Datanya (kemungkinan skor waktu
   keseimbangan) akan digabung/dikorelasikan dengan hasil analisis EEG segmen
   Romberg sebagai analisis tersendiri — bukan bagian dari epoching/ERD-ERS
   Tahap 4–5 di bawah. Pipeline ini perlu menyediakan output Romberg dalam
   bentuk yang siap digabung dengan dataset stork test itu nanti (lihat
   Pertanyaan Terbuka).

## Fakta Data Terverifikasi (dari sampel P01 & P02 — `Archive_3.zip`, `Archive_4.zip`)

**Konvensi penamaan file** (per partisipan, kode `PXX`):
- `PXX_Baseline.EDF` — rekaman EEG resting-state singkat (P01: 61 detik)
- `PXX_Trial.EDF` — rekaman EEG selama seluruh sesi task (P01: 462 detik / 7:42)
- `motor_PXX_Trial_<ISO-timestamp>.webm` — video sesi Trial (P01: ~1280x720, vp9,
  ~29.4 fps, ~13.245 frame, durasi ~450 detik). Baseline tampaknya **tidak** punya
  video pendamping (task diam, tidak perlu identifikasi gerakan).

**Format EDF:**
- 18 channel: 16 EEG standar KT88 (`Fp1-A1, Fp2-A2, F3-A1, F4-A2, C3-A1, C4-A2,
  P3-A1, P4-A2, O1-A1, O2-A2, F7-A1, F8-A2, T3-A1, T4-A2, T5-A1, T6-A2`) + 2 channel
  tambahan (`Add_lead1`, `Add_lead2`) — **sinyal analog kontinu, bukan channel
  trigger/marker digital**. Perlu dikonfirmasi ke pengguna: apakah ini EOG, EMG,
  atau referensi lain?
- Sampling rate: 100 Hz, semua channel.
- ⚠️ **Header EDF `startdate` tidak valid** (menunjukkan `2013-04-01 11:12:13`,
  identik persis di P01 & P02 — konfirmasi ini tanggal default device, bukan waktu
  rekaman sebenarnya). **Tidak boleh dipakai untuk sinkronisasi wall-clock dengan
  video.**

**Variasi antar-partisipan (P01 vs P02) — konfirmasi pola, bukan kebetulan:**
| | P01 | P02 |
|---|---|---|
| Durasi EDF Trial | 462 dtk | 416 dtk |
| Estimasi durasi video Trial | ~450 dtk | ~433–450 dtk |
| Selisih EDF − video | **+12 dtk** (EDF lebih panjang) | **−17 s.d. −34 dtk** (EDF lebih pendek) |

Arah selisihnya **berbeda tanda** antar partisipan (bukan cuma beda besaran) —
ini mengonfirmasi bahwa **tidak ada formula offset tetap** yang bisa
digeneralisasi ke semua partisipan. Kalibrasi Tahap 2 (lihat di bawah) wajib
dilakukan per file, bukan sekali untuk semua data.

**Format Video:**
- Merupakan rekaman **screen + webcam gabungan** dari aplikasi task browser:
  panel HUD instruksi berada di kanan frame (kira-kira kotak `x:960–1280,
  y:250–480` pada resolusi 1280x720 — **verifikasi ulang per file**, karena bisa
  beda posisi/ukuran window per rekaman).
- HUD menampilkan **label task + sub-fase + countdown timer** secara presisi
  (digenerate software, teks tajam → ideal untuk OCR). Posisi & ukuran panel HUD
  **konsisten identik** antara P01 dan P02 (kotak kanan frame) — kemungkinan besar
  aman diasumsikan sama untuk seluruh dataset, tapi tetap validasi sampel di
  awal Tahap 1.
- Label yang teramati (gabungan P01 + P02):
  - `AGEM KANAN` / `AGEM KIRI` — sub-fase: `TURUN` (turun), `NAIK` (naik), `TAHAN`
    (tahan/hold). Jadi satu siklus gerakan tampaknya melalui 3 sub-fase berurutan
    (turun→tahan→naik atau sejenis) — **perlu dikonfirmasi urutan pastinya ke
    pengguna**, karena sampling frame belum menangkap satu siklus penuh berurutan.
  - `ISTIRAHAT UTAMA` — rest dengan countdown menit:detik, durasi jauh lebih
    panjang (teramati sampai >2 menit) dibanding sub-fase gerakan.
  - `BERDIRI RILEKS` — muncul **berulang kali** dengan countdown pendek (5, 3, 1
    detik) **di antara blok-blok gerakan agem**. **Dikonfirmasi BUKAN Standing
    Stork Test** (stork test direkam terpisah, di luar sesi EEG) — kemungkinan
    besar ini posisi reset/transisi antar-trial. Perlakukan sebagai segmen
    "netral" antar-blok, bukan task analisis utama, kecuali pengguna menyatakan
    sebaliknya.
  - `Berdiri Fokus Mata Terbuka (30 Detik)` dan `Berdiri Mata Tertutup (30 Detik)`
    — **dikonfirmasi ini adalah tes Romberg** (segmen terakhir dari sesi EEG),
    konsisten muncul di P01 & P02. Hasil analisis EEG segmen ini akan digabung
    dengan skor Standing Stork Test (dari luar sesi EEG) sebagai analisis
    terpisah/tersendiri — lihat catatan ruang lingkup di atas.
  - **Label "NGEED" belum teramati di P01 maupun P02** — tolong konfirmasi apakah
    tersimpan dengan nama HUD lain, atau ada di segmen video yang belum
    tersampling dalam pengecekan ini.

## ⚠️ Masalah Kritis: Sinkronisasi EEG ↔ Video
Karena EDF dan video direkam oleh dua sistem independen tanpa marker digital
bersama, dan durasi EDF Trial (462 dtk) vs estimasi durasi video (~450 dtk) **tidak
identik**, sinkronisasi wall-clock langsung tidak bisa diasumsikan akurat. Sebelum
membangun epoching, WAJIB tanyakan ke pengguna:
1. Apakah kedua rekaman (EEG & video) dipicu oleh tombol/software yang sama
   (sehingga onset keduanya idealnya start bersamaan, dan selisih murni delay
   inisialisasi software)?
2. Apakah ada event fisik yang terlihat di kedua rekaman untuk dipakai sebagai
   anchor (mis. gerakan tangan pertama peneliti menekan tombol start, atau clap)?

**Strategi default jika tidak ada marker eksplisit:** gunakan transisi task
pertama yang paling jelas termanifestasi di kedua sinyal (mis. onset gerakan agem
pertama — terlihat di video HUD/gerakan tubuh, dan termanifestasi sebagai artefak
motorik/otot pada channel frontal EEG) sebagai **anchor point tunggal per
partisipan**, lalu asumsikan clock kedua device stabil (tidak drift) untuk
sisa sesi. Simpan offset ini secara eksplisit per partisipan di file metadata
(jangan hardcode), karena besar kemungkinan **beda-beda tiap partisipan/sesi**.

## Rencana Pipeline (tahapan, bukan urutan pengerjaan kode yang kaku)

### Tahap 0 — Inventarisasi & Metadata
- Scan folder data, buat manifest CSV: `participant_id, group (penari/non-penari),
  timepoint (pre/post — untuk non-penari), age, path_baseline_edf, path_trial_edf,
  path_video, sync_offset_sec (kosong dulu, diisi Tahap 2)`.

### Tahap 1 — Ekstraksi Timeline Task dari Video (OCR)
- Crop region panel HUD per frame (kalibrasi ulang koordinat box per file, karena
  posisi bisa geser).
- OCR (Tesseract) pada region label utama (abaikan digit countdown yang berubah
  tiap detik) → deteksi **perubahan teks label/sub-fase** sebagai event boundary.
- Output: `PXX_task_timeline.csv` dengan kolom
  `label, subphase, start_frame, end_frame, start_time_video_sec, end_time_video_sec`.
- Validasi manual pada subsample (10–15%) untuk cek akurasi OCR sebelum dipakai massal.

### Tahap 2 — Kalibrasi Sinkronisasi EEG↔Video (per partisipan)
- Cari anchor point (lihat bagian "Masalah Kritis" di atas).
- Hitung `sync_offset_sec` = waktu anchor di EEG − waktu anchor di video.
- Simpan ke manifest. **Jangan lanjut ke Tahap 3 sebelum offset ini divalidasi
  untuk setiap partisipan** — ini titik rawan kesalahan sistemik yang akan
  merusak seluruh hasil epoching kalau meleset.

### Tahap 3 — Preprocessing EEG (MNE-Python disarankan)
- Load EDF, set montage manual (10-20, tanpa midline — definisikan proxy: rata-rata
  C3+C4 sebagai pengganti Cz bila diperlukan).
- Bandpass filter (mis. 1–40 Hz), notch filter 50 Hz (standar listrik Indonesia).
- Deteksi/reject artefak (mis. ICA untuk artefak kedipan mata dari Fp1/Fp2; hati-hati
  jangan buang komponen yang justru merepresentasikan artefak gerak motorik yang
  ingin diukur — pisahkan artefak mata vs sinyal motorik yang relevan).
- Re-referencing sesuai kebutuhan analisis (skema referensi linked-ear A1/A2 sudah
  built-in dari nama channel `-A1/-A2`; evaluasi apakah perlu re-reference average).

### Tahap 4 — Epoching berbasis Timeline Tersinkronisasi
- Gunakan `task_timeline.csv` (Tahap 1) + `sync_offset_sec` (Tahap 2) untuk memotong
  EEG per repetisi gerakan (4 repetisi × {ngeed, agem kanan, agem kiri}), dengan
  window beberapa detik sebelum & sesudah onset (sesuai rencana Anda).
- Opsional refinement: dalam window yang sudah dibatasi OCR, gunakan motion
  detection (optical flow/pose estimation) pada video untuk mempertajam onset
  gerakan aktual (karena onset instruksi HUD ≠ onset gerakan tubuh riil — ada
  reaction time).

### Tahap 5 — Kuantifikasi ERD/ERS (segmen gerakan: ngeed/agem kanan/agem kiri)
- Hitung %ERD/ERS per band (mu, beta) per channel (fokus C3/C4, P3/P4, O1/O2) per
  repetisi, relatif ke baseline (window rest sebelum onset atau rekaman
  `PXX_Baseline.EDF`).
- Time-frequency representation (mis. Morlet wavelet via MNE) untuk visualisasi
  ERD/ERS map per grup.

### Tahap 5b — Analisis Segmen Romberg (jalur terpisah dari ERD/ERS gerakan)
- Segmen Romberg (mata terbuka 30 dtk, mata tertutup 30 dtk) **bukan task
  gerakan** — jangan dipaksakan ke kerangka ERD/ERS motorik yang sama.
- **Fitur EEG yang akan dikorelasikan dengan waktu Standing Stork Test (data
  eksternal, satu angka waktu per partisipan):**
  - **Tier 1 (prioritas utama):**
    - Power alpha oksipital (O1/O2, 8–13 Hz) saat mata tertutup
    - Rasio reaktivitas alpha EC/EO — "Romberg quotient" versi EEG (O1/O2, dan
      opsional P3/P4)
    - Power mu/alpha sensorimotor (C3/C4, 8–13 Hz), EC dan EO
    - Power theta frontal saat mata tertutup (proxy F3/F4 atau F7/F8, karena
      tidak ada Fz) — indikator kompensasi kognitif, relevan untuk rentang usia
      lebar (remaja–102 tahun)
  - **Tier 2 (sekunder/eksploratif):** Individual Alpha Frequency (IAF) di
    O1/O2 & P3/P4; power beta sensorimotor (C3/C4); power alpha parietal (P3/P4)
  - **Tier 3 (lanjutan/opsional):** ukuran kompleksitas sinyal (sample entropy/
    Lempel-Ziv) EC vs EO; koherensi fronto-parietal (interpretasi hati-hati,
    channel terbatas)
- Output per partisipan (mis. `PXX_romberg_features.csv`) disiapkan dalam format
  yang mudah di-join dengan dataset skor Standing Stork Test eksternal (kolom
  kunci: `participant_id`; stork test tersedia sebagai **waktu per partisipan
  saja**, tanpa timepoint/kondisi tambahan) untuk analisis gabungan tersendiri —
  **di luar pipeline ERD/ERS ini**.

### Tahap 6 — Analisis Statistik
- **Untuk ERD/ERS gerakan:** linear mixed model (subjek sebagai random effect),
  grup & jenis gerakan sebagai fixed effect, usia sebagai kovariat (rentang usia
  sangat lebar: remaja–102 tahun). Untuk studi intervensi (non-penari, pre/post):
  tambahkan timepoint sebagai fixed effect + interaksi grup×timepoint.
- **Untuk Romberg + Stork Test:** korelasi Pearson/Spearman (pilih sesuai
  distribusi data) antara tiap fitur EEG Tier 1 dengan waktu stork test,
  **dikontrol usia** (korelasi parsial atau sebagai kovariat regresi, mengingat
  rentang usia remaja–102 tahun). Tier 1 sebagai hipotesis utama; Tier 2/3
  eksploratif, dilaporkan terpisah. Jika menguji banyak fitur sekaligus, koreksi
  multiple comparison (Benjamini-Hochberg disarankan dibanding Bonferroni untuk
  konteks eksploratif ini).

## Metode Tambahan Diadopsi dari Draft Naskah (Paper A/B/C)

Pengguna sudah menyusun 3 draft naskah terkait studi ini (Paper A cross-sectional,
Paper B longitudinal-pilot 6 minggu, Paper C data descriptor). Beberapa pilihan
metodologis di dalamnya **layak diadopsi ke pipeline ini** — dicatat di sini
supaya Tahap 5/6 di atas konsisten dengan rencana naskah:

**Dari Paper A (montase 16-channel, revisi terbaru):**
- **Lateralized Readiness Potential (LRP)** sebagai pengganti Readiness Potential
  klasik (yang butuh Cz) — dihitung dari **selisih C4−C3, metode
  double-subtraction (Coles, 1989)**, amplitudo pada jendela **−200 hingga 0 ms
  pra-onset gerak**, dibandingkan antar grup (trial tangan kanan vs kiri). Domain
  waktu (low-pass filter), BUKAN dekomposisi pita frekuensi — proses terpisah
  dari pipeline ERD/ERS di Tahap 5.
- **Indeks Lateralisasi (LI)** = (ERD kontralateral − ERD ipsilateral) /
  (ERD kontralateral + ERD ipsilateral), dihitung dari pasangan C3–C4, dibandingkan
  antar grup.
- **Topografi ERD beta** (peta skalp 16-channel, tanpa interpolasi area garis
  tengah) untuk kondisi gerak tangan kanan & kiri terpisah — pelengkap visual
  untuk Tahap 5.
- Uji statistik grup: **Welch's t-test** (bukan Student's t biasa, karena varians
  antar grup penari/non-penari kemungkinan tidak sama) untuk 5 indeks konvensional
  (ERD Beta Agem, Theta Frontal Agem, Alpha Oksipital Romberg-EC, rasio
  Theta/Alpha Romberg, durasi Stork Test) + regresi linear usia×kelompok.
- ⚠️ Regresi usia×kelompok di draft memakai asumsi linear sederhana — dengan
  rentang usia riil (remaja–102 tahun) dan kemungkinan cuma 1–2 partisipan di
  ekor ekstrem, WAJIB tambahkan **uji sensitivitas (dengan/tanpa outlier usia
  ekstrem)** sebelum melaporkan hasil regresi ini sebagai temuan utama.

**Dari Paper B (longitudinal pre-post 6 minggu, desain tanpa kontrol eksternal):**
- **Reliable Change Index (RCI)**: `RCI = (Post−Pre)/S_diff`, dengan
  `S_diff = SD_pre × √(2×(1−rxx))`, ambang `|RCI|≥1.96` = perubahan individual
  nyata. ⚠️ **rxx harus dihitung dari data riil** (test-retest atau split-half
  pada segmen baseline/rest) — draft masih pakai placeholder (0.70–0.85), belum
  boleh dipakai apa adanya.
- **Nonequivalent Dependent Variable (NDV)**: Peak Alpha Frequency saat istirahat
  mata tertutup sebagai metrik kontrol teoretis (dianggap tidak terkait latihan
  tari) — uji-t berpasangan terpisah dari 5 indeks target, untuk menyingkirkan
  efek uji-ulang/familiaritas umum.
- **Gap Closure (%)** = (Post−Pre)/(Rata-rata Penari−Pre)×100 per individu,
  memakai rata-rata kelompok penari **dari Paper A** sebagai benchmark. ⚠️
  **Dependency**: Paper A harus final dulu (nilai rata-rata penari sudah pasti)
  sebelum Gap Closure Paper B bisa dihitung — perhatikan urutan pengerjaan.
- Seluruh hasil di draft eksplisit diberi label **"[SIMULATED RESULTS]"** —
  praktik yang baik, pertahankan pola ini di kode (mis. flag jelas
  `is_simulated=True` di output) sampai data riil terpasang.

## ⚠️ Isu yang Harus Diperbaiki di Draft Naskah Sebelum Dipakai Sebagai Rujukan Final
Ditemukan saat meninjau ketiga draft — **belum diperbaiki oleh pengguna**, dicatat
di sini supaya tidak tercampur dengan bagian "Metode Tambahan" di atas yang sudah
disetujui untuk diadopsi:
- Ketiga draft masih mendeskripsikan **N=25 penari/15 non-penari, usia 17–55
  tahun** — TIDAK sesuai kohort aktual (**N=24/14, usia remaja–102 tahun**).
  Bagian Metode, Abstrak, dan judul ketiga naskah perlu ditulis ulang.
- **Paper C masih mendeskripsikan montase 19-channel dengan Cz** — kontradiksi
  langsung dengan Paper A yang sudah dikoreksi ke 16-channel tanpa elektroda
  garis tengah. Harus disinkronkan sebelum Paper C dianggap akurat.
- Bagian "Data Processing" Paper C (Differential Entropy + Relative Difference
  baseline reduction, dari Wirawan dkk. 2024) belum sinkron dengan metode ERD/LRP
  yang benar-benar dipakai di Paper A/B — perlu diklarifikasi/ditulis ulang.
- Tidak ada koreksi multiple comparison disebutkan di Paper A untuk 5 indeks +
  LI + LRP + interaksi usia yang diuji sekaligus.

## Strategi Publikasi: 4 Naskah (A/B/C/D)

Berdasarkan diskusi evaluasi draft, dataset ini direncanakan menghasilkan **4
naskah**, bukan 3 — supaya analisis kontrol postural (Romberg + Stork Test) tidak
"terselip" sebagai 1 dari 5 indeks di Paper A/B, mengingat kerangka Tier 1–3 di
Tahap 5b cukup dalam untuk jadi kontribusi tersendiri.

| Paper | Fokus | Desain | Sampel |
|---|---|---|---|
| **A** | *Movement generation* (ngeed/agem): ERD/ERS, LRP, LI, topografi | Cross-sectional | Penari vs non-penari, 1 timepoint |
| **B** | Neuroplastisitas jangka pendek (RCI/NDV/Gap Closure) | Longitudinal pre-post 6 minggu | Non-penari saja (n=14) |
| **C** | Data descriptor — dokumentasi dataset mentah, tanpa klaim analitik | — | Seluruh data (gerakan + Romberg + Stork) |
| **D (baru)** | Kontrol postural/keseimbangan: EEG Romberg (Tahap 5b) × Stork Test | **Cross-sectional saja** (BUKAN gabungan pre-post) | Seluruh 38 partisipan, 1 timepoint (untuk non-penari peserta pelatihan: pakai data pre-training, sama seperti Paper A) |

**Rancangan Paper D (ringkas, disepakati):**
- **Analisis utama:** Welch's t-test antar grup (penari vs non-penari) untuk tiap
  fitur EEG Tier 1 dari Tahap 5b (alpha oksipital EC, rasio reaktivitas alpha
  EC/EO, alpha sensorimotor C3/C4, theta frontal EC) + durasi Stork Test.
- **Analisis sekunder:** korelasi Pearson/Spearman antara fitur EEG Tier 1 dan
  durasi Stork Test di **seluruh sampel gabungan** (bukan per grup), dikontrol
  usia (korelasi parsial/kovariat regresi) — ini yang membedakan Paper D dari
  sekadar mengulang perbandingan grup Paper A dengan metrik berbeda.
- **Tidak memakai** RCI/NDV/Gap Closure (khusus desain pre-post Paper B) — jauh
  lebih sederhana untuk ditulis & direview dibanding opsi gabungan yang sempat
  dipertimbangkan.
- **Tidak ada dependency ke Paper A** (tidak butuh benchmark rata-rata penari
  seperti Gap Closure Paper B) — bisa dikerjakan paralel dengan Paper A.

**Syarat supaya tidak dianggap *salami slicing*:** kalau Paper D dibuat, tabel
5-indeks di Paper A & B sebaiknya **tidak lagi menonjolkan** indeks Romberg
(Alpha Oksipital Romberg-EC, rasio Theta/Alpha Romberg) sebagai temuan utama —
cukup dirujuk singkat ke Paper D untuk detail, supaya tidak ada klaim substantif
yang dilaporkan dua kali. Prinsipnya: A = eksekusi motorik dinamis, D = kontrol
postural statis — dua pertanyaan riset yang berbeda dari dataset yang sama.

## Hasil Tersimpan untuk Sesi Berikutnya
Salinan hasil turunan (tanpa data mentah) ada di `hasil_analisis/` (lihat README di dalamnya). Data mentah
(EDF, video) dan fif/npz TIDAK ada di repo — sesi baru perlu mengunggah ulang data mentah bila
pipeline harus dijalankan ulang.

## ✅ Pendekatan v2 DIIMPLEMENTASIKAN (2026-09-24) — status terkini, menggantikan catatan lama bila bertentangan
- **Sinkronisasi:** `sync.mode: fixed`, offset 0,85 dtk (dibekukan). Estimasi xcorr hanya ALARM, yang harus
  dikonfirmasi cek onset-ke-onset. P34: alarm xcorr +33 dtk DIBANTAH (onset pada 0,85 = −0,15 dtk, n 4) →
  0,85. P01: alarm terkonfirmasi → keputusan MANUAL +3,25 dtk (onset −0,12 dtk, n 8) — **perlu konfirmasi
  pengguna**. P35: xcorr tanpa kopling (r 0,01) → 0,85 tanpa verifikasi (ditandai). Semua 14 lolos.
- **Tahap `segmen`** (`eegpipe/segments.py`): fase dari video, pangkas batas, semua segmen, acuan gabungan
  paling diam, specparam kanal/area/belahan (SEMUA + per gerakan), batas ketelitian, durasi, Romberg/area.
- **TEMUAN KUALITAS DATA KRITIS: sinyal DATAR (≈0 µV, SD < 0,5 µV/0,2 dtk) = reset amplifier KT88 / sinyal
  hilang.** Median % kanal×waktu datar: penari P01–P07 0–13%; non-penari P33–P38 6–36% (P36 36%, P33 32%);
  P10 0%. Lebih sering saat TAHAN/NAIK (terkait gerak/tegangan kabel). Kini ditandai per kanal×waktu dari EDF
  mentah; kanal-segmen datar > 10% = data hilang. Nilai ekstrem (−30…−300 dB) di analisis sebelumnya berasal
  dari sini → **hasil uji cepat 2026-09-23 (garis latar d −0,9, mu TURUN d +1,75) TIDAK bertahan**.
- **Konfound hari rekaman:** penari semua 9 Sep; non-penari 14 Sep (kecuali P10). Kualitas sinyal berbeda per
  hari → beda grup EEG bisa artefak perangkat/sesi. **Rekomendasi: selang-seling grup per hari rekaman,
  catat impedansi & kondisi kabel, cek sinyal datar langsung saat perekaman.**
- **Hasil v2 (7 penari vs 7 non-penari, SEMUA eksploratif; `python -m eegpipe hypotheses-v2`):**
  perilaku: CV durasi TAHAN 0,25 vs 0,48 (g −1,10, p 0,026), durasi NAIK 1,00 vs 1,39 dtk (g −0,93,
  p 0,047), TURUN sama (p 0,44); EEG: mu periodik posterior TAHAN 0,33 vs 1,57 dB (g −0,94, p 0,044);
  garis latar sentral TURUN/TAHAN, mu sentral TURUN, H12 ≈ 0 (g −0,2…0,1); H13 rho 0,34 (p 0,12).
  Tidak ada yang lolos FDR (p_FDR ≥ 0,14). Model campuran segmen: tidak ada beda grup (p ≥ 0,24).
  Set konfirmatori (P33–P35) hanya non-penari → belum dapat diuji.
- Hasil lengkap: `hasil_analisis/v2/` (lihat README); ekspor ulang: `python scripts/ekspor_hasil.py`.

## 🔀 Penggabungan sesi `claude/funny-johnson-5skifb` (2026-09-24) — keputusan pengguna: PROSEDUR SESI INI UNTUK SEMUA SAMPEL
- Prosedur baku = pendekatan v2 sesi ini (offset tetap di SEMUA tahap, acuan paling diam dari VIDEO,
  deteksi sinyal datar, tahap `segmen`, H6–H13). `eegpipe/area_map.py` sesi lain DIHAPUS (acuan dipilih dari
  EEG paling tenang = sirkular; tanpa deteksi datar; offset tetap hanya di satu tahap). Dokumen sesi lain
  dipindah ke `docs/sesi_funny_johnson/` (riwayat).
- Diambil dari sesi lain: **offset per blok** (`sync.offset_blocks` = [[mulai_video_dtk, offset], …], batas =
  awal ISTIRAHAT UTAMA; `sync.to_eeg()`), keputusan pengguna untuk P08/P11. Dalam mode tetap, drift
  signifikan (|drift| > 0,3 dtk, p < 0,05) kini memicu ALARM → isi manual, mis.
  `sync: {method: manual, offset_blocks: [[0, 1.28], [<awal ISTIRAHAT UTAMA>, 0.65]], basis: "…"}` (P11) dan
  P08 +1,20 → +0,95.
- **Hasil P08, P09, P11, P30–P32 dan meta-analisis 10 vs 7 di bagian "Temuan P08…" di bawah dihitung dengan
  prosedur LAMA (skrip audit, tanpa deteksi datar) → HARUS dihitung ulang** dengan prosedur ini. Data mentah
  keenamnya belum ada di mesin sesi ini (perlu diunggah ulang).

## ✅ Kohort 20 partisipan dengan prosedur v2 seragam (2026-09-24)
- Ditambahkan P08, P09, P11 (penari, direkam 10 Sep) & P30–P32 (non-penari, 14 Sep). Total 10 vs 10.
- Sinkronisasi: P09/P30/P31/P32 offset tetap 0,85. **P11**: alarm drift → offset per blok MANUAL [0 dtk: +1,28;
  93,8 dtk: +0,65] (cek onset per blok −0,18/−0,07). **P08**: alarm drift → per blok MANUAL [+1,20; 93,2 dtk:
  +0,95] (keputusan pengguna) tetapi **KONFLIK dengan cek onset (−1,4 dtk per blok) → tinjau video**.
  Aturan baru: alarm drift TIDAK dapat dibantah median onset keseluruhan.
- Sinyal datar: P08 21,5%, P09 12,4%, P11 12,9% (penari 10 Sep, lebih tinggi dari penari 9 Sep); P30 37,8%,
  P31 15,8%, P32 11,4%. Batas ketelitian NaN pada P30/P38 (< 5 jendela acuan tanpa kanal datar).
- **Hasil H6–H13 (10 vs 10; `hasil_analisis/v2/hypothesis_v2_tests.csv`):**
  - Seluruh sampel (eksploratif): CV TAHAN 0,27 vs 0,46 (g −0,98, p 0,017, p_FDR 0,075); durasi NAIK 0,98 vs
    1,61 dtk (g −0,82, p 0,042, p_FDR 0,095); mu periodik posterior TAHAN 0,39 vs 1,50 dB (g −0,90, p 0,025,
    p_FDR 0,075); H13 garis latar TAHAN ~ CV TAHAN rho 0,45 (p 0,023, p_FDR 0,075). H6, H9, H10, H12 ≈ 0.
  - **Konfirmatori (3 penari vs 6 non-penari, partisipan baru): tidak ada yang signifikan.** Arah sesuai
    untuk H7 (g −0,21), H8 (g −0,57), H11 (g −0,47); H9 mu sentral TURUN g +1,21 (p 0,056); H13 rho 0,63
    (p 0,034, p_FDR 0,25). Daya uji sangat rendah (n = 3 penari).
  - Model campuran tingkat segmen (20 partisipan): tidak ada beda grup di fase mana pun (p ≥ 0,33).
- **H1–H5 dihitung ulang dengan prosedur v2 (2026-09-24)** (endpoint dari keluaran segmen; di config
  `hypotheses_v2`). Seluruh 20: H1 g −0,02, H2 g −0,06, H3 durasi tahan agem 3,09 vs 2,43 dtk (g +0,66,
  p 0,071), H4 g −0,04, H5 g −0,02. Konfirmatori H1–H5 (18 partisipan tanpa P02/P10 pembentuknya): semua
  n.s. (H3 g +0,53, p 0,13). → **H1, H2, H4, H5 tidak didukung**; H3 searah tetapi lemah. Hasil awal P02 vs
  P10 tidak bereplikasi. File: `hypothesis_v2_H1-H5_konfirmatori.csv`.
- **Mode eksploratif (keputusan pengguna 2026-09-24):** semua uji pada seluruh sampel sekaligus
  (`analysis_mode: eksploratif`). H1–H13 (20 partisipan, FDR atas 14 uji): H7 g −0,98 (p 0,017), H11 g −0,90
  (p 0,025), H13 rho 0,45 (p 0,023), H8 g −0,82 (p 0,042), H3 g +0,66 (p 0,071); p_FDR ≥ 0,12; lainnya ≈ 0.
  **Peta eksploratif lengkap** (`exploratory_map_v2.csv`; 8 area × 5 fase × 5 ukuran + durasi = 208 uji):
  14 dengan p < 0,05 (≈ 10 diharapkan kebetulan), tidak ada yang lolos FDR. Terkuat: frontotemporal (theta/mu
  periodik lebih tinggi pada non-penari saat PRA/TURUN/TAHAN, g −1,2…−1,4 — area rawan artefak otot);
  **POST (beta rebound) lebih besar pada penari: temporo-posterior g +1,36 (p 0,006), oksipital g +1,08
  (p 0,021)**; beta frontal PRA g +0,98; durasi TAHAN median g +1,11; CV TURUN g −1,03.
- **Uji sensitivitas pembersihan artefak (`scripts/sensitivitas_pembersihan.py`, 2026-09-24):** A baku; B tepi
  sinyal datar diperlebar 1,6 dtk (ekor filter HP 1 Hz); C gabungan spektrum MEDIAN antar-segmen; D = B+C.
  Perilaku (H3, H6–H8) tidak berubah. **Tidak ada varian yang memunculkan efek EEG grup baru** → hasil nol EEG
  bukan akibat pilihan pembersihan. H11 tahan thd B (g −0,94) tetapi melemah dengan median (−0,48/−0,66);
  H13 tahan thd B (rho 0,45) tetapi turun dengan median (0,16/0,22) → keduanya sebagian ditarik segmen
  ekstrem (kemungkinan ledakan artefak gerak/kabel pada penahan yang tidak stabil). H1/H4/H5 berganti tanda
  antar varian = derau. Ringkasan: `hasil_analisis/sensitivitas/ringkasan_H1-H13.csv`.
- Konfound hari rekaman tetap: penari 9–10 Sep, non-penari 14 Sep (kecuali P10).

## ✅ Kohort 28 partisipan, 2026-09-24 — ⚠️ grup di bagian ini USANG (P29/P30/P34 = penari); lihat bagian Demografi di bawah
- Ditambahkan P12–P15 (penari, 10 Sep) & P26–P28 (non-penari, 12 Sep), P29 (non-penari, 14 Sep). P15 punya 2 file
  baseline → dipakai `P15_Baseline.EDF` (19% datar vs 32%); `Baseline2` dipindah ke `data/raw/P15/_tidak_dipakai/`.
- **KALIBRASI cek onset:** pada offset tetap, artefak EEG mendahului onset lengan video median −0,89 dtk (IQR −1,50…
  −0,24; 23 partisipan) → acuan `expected_lag_sec: -0.89` (bukan 0). Alarm onset: |lag − acuan| > 1,5 dtk; alarm xcorr
  dibantah bila onset terkalibrasi cocok (≤ 0,5) atau berlawanan arah. Akibatnya: **P01 manual direvisi +3,25 → +4,10 dtk**
  (xcorr +4,52 & onset terkalibrasi +4,0–4,1 sepakat; cek onset pada 4,10 = −0,94) — perlu konfirmasi pengguna;
  P14 (xcorr +2,70 vs onset berlawanan arah) & P26 (xcorr +0,45) → offset tetap; P29 xcorr +60 dtk tanpa kopling (r 0,10)
  → offset tetap tanpa verifikasi.
- **Hasil H1–H13 (28; FDR atas 14):** **H7 CV TAHAN 0,26 vs 0,45 (g −1,01, p 0,005, p_FDR 0,037)**; **H13 garis latar TAHAN ~
  CV TAHAN rho 0,48 (p 0,005, p_FDR 0,037)**; H8 NAIK 0,99 vs 1,62 dtk (g −0,91, p_FDR 0,058); H3 tahan agem 3,14 vs 2,46 dtk
  (g +0,72, p_FDR 0,092); H11 mu posterior TAHAN (g −0,71, p_FDR 0,092); H10b garis latar sentral TAHAN 3,0 vs 6,3 dB
  (g −0,53, p 0,08); H9 g +0,50 (p 0,09); H1, H4, H5, H6, H12 ≈ 0.
- Peta eksploratif (208 uji): **29 dengan p < 0,05 (≈ 10 diharapkan kebetulan)**; 1 lolos p_FDR < 0,10: theta periodik
  frontotemporal PRA lebih tinggi pada non-penari (g −1,57; area rawan artefak otot). Frontotemporal konsisten lebih
  tinggi pada non-penari (theta/mu/eksponen, PRA/TURUN/TAHAN) — kemungkinan tegangan otot rahang/temporal.
  Beta periodik lebih tinggi pada penari: parietal PRA (g +0,99), temporo-posterior POST (g +0,96).
- Model campuran segmen (28): tidak ada beda grup di fase mana pun (p ≥ 0,46).
- Catatan: H13 sebelumnya melemah dengan gabungan median (uji sensitivitas 20 partisipan) → ulangi sensitivitas pada 28.

## ✅ Demografi PARTISIPAN.xlsx + koreksi grup (2026-09-24) — MENGGANTIKAN pembagian grup sebelumnya
- `data/participants.csv` kini dari PARTISIPAN.xlsx (38 partisipan): `age`, `dance_years` (PENGALAMAN),
  `onset_age` (ONSET), `vakum_years` (PERNAH VAKUM), `activity_per_month` (AKTIFITAS/BULAN),
  `proporsi_hidup_menari` = dance_years/age. **Grup TIDAK dapat ditebak dari nomor**: P29 (56 th, 49 th
  menari), P30 (55/50) dan P34 (33/27) = PENARI (sebelumnya salah dicatat non-penari). Grup lengkap:
  penari P01–P09, P11–P21, P29, P30, P34 (23); non-penari P10, P22–P28, P31–P33, P35–P38 (15).
- Kohort 28 yang sudah diproses = 17 penari (usia 15–56, median 30) vs 11 non-penari (21–57, median 44).
  Belum diproses: P16–P21 (penari lansia 55–102 th) dan P22–P25 (non-penari muda 20 th ×3, 48 th) →
  PRIORITAS untuk memecah konfound usia.
- **Hasil H1–H13 setelah koreksi grup (FDR atas 14 uji):** H7 CV TAHAN g −1,44 (p_FDR 0,009), H11 mu
  periodik posterior TAHAN g −1,17 (p_FDR 0,015), H2, H3, H6, H8, H10b, H13 p_FDR 0,047–0,048; H10a/H12
  ≈0,08; H1/H4/H5/H9 n.s. Tahan terhadap: tanpa P01/P08 (offset belum dikonfirmasi) dan pembatasan
  usia tumpang-tindih 21–57 th + usia sebagai kovariat (CV TAHAN p 0,001; garis latar TAHAN p 0,010; mu
  posterior TAHAN p 0,012; NAIK/TURUN p ≈ 0,047).
- **Dosis-respons (`dose_response_v2.csv`; OLS HC3 + usia):** seluruh sampel, dance_years memprediksi CV
  TAHAN, durasi TURUN, mu posterior TAHAN (p_FDR 0,004–0,006), NAIK/garis latar TAHAN (≈0,04–0,05); r
  usia–tahun 0,12 (VIF 1,0). TETAPI model `penari + dance_years + usia` tidak dapat memisahkan grup dari
  tahun (celah 0 vs ≥10 th) → efek seluruh sampel = efek grup. **Di dalam penari (n 17) dance_years
  kolinear dengan usia (r 0,92, VIF 6,3) → tidak ada efek**; hanya activity_per_month → CV TAHAN (β −0,57,
  p 0,012, p_FDR 0,08) dan onset_age → CV TAHAN (p 0,013, p_FDR 0,09). Dosis-respons sesungguhnya butuh
  penari dengan tahun menari berbeda pada usia sama (P16–P21 akan membantu) → gunakan juga
  proporsi_hidup_menari / onset_age / aktivitas.
- **Sensitivitas pembersihan (28, grup terkoreksi; varian A baku / B tepi datar 1,6 dtk / C median / D B+C):**
  perilaku tidak berubah; H11 tahan di semua varian (g −1,17/−1,12/−0,68/−0,76; p ≤ 0,04); H10a & H12
  justru MENGUAT dengan median (g −0,82…−0,98; p 0,006–0,018); H13 melemah dengan median (rho 0,43 → 0,27–0,28,
  p ≈ 0,08); H2 melemah dengan tepi datar diperlebar (p 0,11–0,13); H1/H4/H5/H9 tetap nol/berganti tanda.
- Konfound hari rekaman tetap ada; P29/P30/P34 (penari, hari rekaman non-penari) sedikit mengurainya.

## 🔎 Pola offset EEG−video seluruh kohort (2026-09-24, `scripts/pola_offset.py` → `results/pola_offset.csv`)
- Pindai korelasi gerak tubuh video × selubung EMG 20–34 Hz (tanpa 4 dtk awal: transien awal rekaman), per blok.
- 20/28 berkumpul 0,6–1,1 dtk (offset tetap 0,85 wajar), konsisten di keempat hari rekaman, tanpa tren jam.
- Pencilan jelas (kopling kuat, kedua blok sepakat): **P01 +4,15** (sesi pertama studi, 9 Sep 09:24; EDF 20,5 dtk
  lebih panjang dari video → EEG dinyalakan lebih dulu), **P09 +1,70**, **P04 +1,65**, **P13 +0,05**, P26 +0,35.
  Lemah: P14 +2,7 (r 0,21). Tanpa kopling (tidak dapat diverifikasi): P29, P35; lemah P33/P34/P30.
- P08 hasil pindai konstan ≈ 0,95–1,0 di kedua blok (bertentangan dgn keputusan per blok 1,20→0,95); P11 blok 1
  0,85 (keputusan 1,28). Ambang alarm 1,0 dtk terlalu longgar untuk deviasi ≈ 0,8 dtk (≈ separuh fase NAIK/TURUN).
- Selisih durasi EDF−video: 9–10 Sep EDF lebih pendek (−3…−31 dtk; EEG distop lebih awal) vs 12–14 Sep hampir sama
  (−0,6…+5,5) → prosedur STOP berubah, prosedur START konsisten. Menunggu keputusan pengguna untuk koreksi.

## ⭐ Tujuan Utama Riset (dikoreksi pengguna, 2026-09-23)
**Regresi antara DURASI MENARI (tahun pengalaman) dan kemampuan kontrol gerak (EEG + perilaku)**
pada sampel beragam — analisis dosis-respons, bukan sekadar penari vs non-penari.
- Data yang dibutuhkan (belum ada): `dance_years`, `age`, idealnya `start_age` & jam latihan/minggu
  → tambahkan ke data/participants.csv. Non-penari = 0 tahun (atau paparan minimal).
- **Kolinearitas usia × durasi menari** (penari tua menari lebih lama) → wajib: durasi menari +
  usia dalam satu model, cek VIF; alternatif: usia mulai menari atau proporsi hidup menari.
- Model utama: outcome ~ dance_years (+log/kurva jenuh) + usia (+ jenis kelamin); analisis di dalam
  penari (n=24) + seluruh sampel (non-penari = 0; pertimbangkan model hurdle/grup + tahun).
- Outcome kandidat (dari eksplorasi): CV durasi TAHAN, durasi NAIK/TURUN, garis latar TURUN/TAHAN,
  mu periodik sentral TURUN, mu temporo-posterior TAHAN. Batasi ke beberapa outcome utama / skor
  komposit + FDR. Hipotesis H1–H13 dirumuskan ulang sebagai kemiringan (slope) dosis-respons.

## Jawaban Pengguna (2026-09-23)
1. **Start rekaman:** EEG dan video direkam di dua device berbeda, dimulai manual
   oleh dua operator pada aba-aba **hitungan ke-3** (terlihat oleh kedua operator).
   → Prior: `sync_offset_sec ≈ 0` dengan ketidakpastian ~±1–2 dtk (waktu reaksi
   manusia + delay inisialisasi software). Presisi ini **tidak cukup** untuk
   ERD/ERS, sehingga offset tetap harus disempurnakan dan divalidasi berbasis data
   per partisipan (Tahap 2). Selisih durasi EDF−video kemungkinan besar berasal
   dari waktu **stop** yang berbeda, bukan dari start.
2. **`Add_lead1` / `Add_lead2`:** "sepertinya lead referensi" (belum pasti).
   → Diperlakukan sebagai `misc` sampai diverifikasi secara empiris (lihat
   EEG_PROCESSING.md, Tahap 3). Jika terbukti berisi potensial A1/A2, referensi
   linked-ear dapat direkonstruksi.
3. **Label HUD gerakan:** `NGEED`, `AGEM KANAN`, `AGEM KIRI`.
4. **Sub-fase:** semua gerakan (ngeed, agem kanan, agem kiri) terdiri dari
   `TURUN → TAHAN → NAIK`. **Sebagian partisipan tidak mengikuti instruksi HUD
   dengan tepat**, sehingga fase aktual **wajib dikonfirmasi dari video**
   (pose/gerak tubuh), bukan hanya dari label HUD. Refinement onset di Tahap 4
   menjadi **wajib**, bukan opsional.

## Setting Ruang Rekaman & Struktur Folder (dari pengguna, 2026-09-23)
- Partisipan berdiri menghadap **monitor instruksi** (HUD) di meja; **webcam di tripod
  di pojok ruangan**; **dua operator duduk di samping/belakang partisipan** (satu
  memegang berkas kabel elektroda; laptop akuisisi EEG dan laptop task terpisah).
  Amplifier/headbox di tiang tripod setinggi kepala. Partisipan memakai **kamen**.
- Uji MediaPipe pada foto setting: deteksi default menangkap **operator**, bukan
  partisipan → pose wajib dibatasi ke area partisipan + pemilihan pose. Lutut tertutup
  kamen (visibilitas ≈ 0,1) → fase gerak dari **bahu + pinggul**, bukan lutut.
- Foto setting **tidak** di-commit ke repo (partisipan dapat dikenali).
- Struktur folder: **satu folder per partisipan**, berisi video, `PXX_Baseline.EDF`,
  `PXX_Trial.EDF`. Grup/usia/timepoint dari file demografis terpisah. Belum jelas
  bagaimana folder pre vs post non-penari dibedakan.

## Catatan Teknis Hasil Verifikasi (menggantikan asumsi di atas bila bertentangan)
- **Notch 50 Hz tidak dapat diterapkan**: sampling 100 Hz → 50 Hz = Nyquist (MNE
  menolak). Interferensi listrik ditangani low-pass 40 Hz. (Mengoreksi Tahap 3.)
- **Referensi bukan linked-ear**: kanal kiri → A1, kanan → A2 (referensi telinga
  ipsilateral). Asimetri A1 vs A2 masuk langsung ke selisih C3/C4 — relevan untuk
  LRP dan LI. `Add_lead` terbukti datar (P02), jadi tidak bisa dikoreksi. (Mengoreksi Tahap 3.)
- **Refinement onset dari video wajib** (lihat jawaban no. 4), bukan opsional.
- **LRP butuh cabang preprocessing terpisah**: high-pass ≤ 0,1 Hz (filter 1 Hz untuk
  ERD/ERS akan menghapus potensial lambat), dan presisi onset jauh di bawah 200 ms.
  Dengan hanya 4 repetisi per sisi, SNR LRP sangat rendah — laporkan sebagai
  eksploratif. Detail di EEG_PROCESSING.md.

## Temuan dari Data Riil P02 (EDF Baseline + Trial, dianalisis 2026-09-23)
- **`Add_lead1` / `Add_lead2` datar**: SD 0,4 µV, nilai hanya −3 s.d. +0,2 µV
  (kuantisasi 0,1 µV). **Tidak berisi sinyal** → tidak bisa dipakai untuk
  rekonstruksi linked-ear. Referensi telinga ipsilateral (A1/A2) adalah **final**.
  Kanal diabaikan (`misc`).
- **Filter perangkat KT88 sudah terpasang saat rekaman** (header `prefilter`
  kosong, tetapi terlihat di spektrum):
  - **Low-pass ≈ 35 Hz** yang curam (turun ~40 dB antara 34 dan 37 Hz) → bandwidth
    efektif ≤ 35 Hz. Beta 13–30 Hz aman; "EMG" untuk sinkronisasi pakai 20–34 Hz.
  - **High-pass ≈ 0,5–1 Hz** (power turun > 15 dB di bawah ~0,8 Hz, mean blok ≈ 0)
    → **potensial lambat (LRP) sudah terlemahkan oleh perangkat**. LRP kemungkinan
    besar tidak dapat diukur secara valid dari data ini (lihat EEG_PROCESSING.md 10.3).
- **Tidak ada clipping**: rentang fisik ±3280 µV, resolusi 0,1 µV, puncak ±450 µV.
- **Tidak ada puncak alpha yang jelas** pada P02 di semua segmen (Baseline "puncak"
  7,5–8 Hz hanya +0 dB di atas flank). Implikasi: IAF/PAF bisa tidak terdefinisi
  untuk sebagian partisipan (terutama lansia) → perlu aturan NaN / specparam.
- **Baseline kemungkinan mata terbuka** (P02: ~6 kedipan/menit). Konfirmasi ke
  pengguna — memengaruhi sumber PAF untuk NDV Paper B.
- **Romberg EC mungkin tidak terekam penuh di EDF P02**: 46 dtk terakhir EDF tanpa
  kedipan tetapi tanpa kenaikan alpha; EDF P02 17–34 dtk lebih pendek dari video dan
  Romberg adalah segmen terakhir. Harus diverifikasi dengan timeline video setelah
  sinkronisasi — **QC wajib: EDF harus mencakup seluruh segmen Romberg**.

## Temuan dari Video + Pipeline P02 (2026-09-23)
- Video 441,5 dtk, VFR (11–129 ms/frame), tanpa durasi di header; audio ada. Panel HUD
  x 960–1280, y 270–449; webcam x 0–960; area partisipan tanpa operator x 340–740, y 90–640.
- Protokol panel: BERSIAP 5 dtk; tiap repetisi 8 dtk (TURUN hitungan 1–3, TAHAN 4–5,
  NAIK 6–8); BERDIRI RILEKS 8 dtk; blok 1 = rep 1–2 tiap gerakan, ISTIRAHAT UTAMA 180 dtk,
  blok 2 = rep 3–4; Romberg EO 30 dtk → BERDIRI ISTIRAHAT 15 dtk → EC 30 dtk.
  Label baru: `BERSIAP`, `Berdiri Istirahat (15 Detik)`. Label `NGEED` terkonfirmasi.
- Offset EEG = video + 0,75 dtk (tanpa drift signifikan). **Romberg EC P02 hanya 13%
  di dalam EDF** → EEG dihentikan sebelum video selesai.
- P3/P4 bising (kontak elektroda?) → diinterpolasi; kanal kiri terganggu saat Romberg EO
  (kemungkinan elektroda telinga A1).
- ERD TAHAN plausibel (−44…−52%); TURUN/NAIK kemungkinan didominasi artefak gerak.
- Pipeline `eegpipe` (lihat EEG_PROCESSING.md "Menjalankan Pipeline") berjalan penuh pada P02.

## Temuan P10 (non-penari) dan perbandingan dengan P02 (2026-09-23)
- Video 441,6 dtk, EDF Trial 429 dtk; tata letak panel & area partisipan sama dengan P02.
  **Pengamat duduk tepat di belakang partisipan** (di dalam area partisipan) → saat agem
  MediaPipe menggabungkan dua orang (kepala/bahu pada pengamat). Identitas kini dilacak
  dari kontinuitas seluruh kerangka; lintasan batang tubuh dihaluskan 0,5 dtk, plato =
  persentil-90; repetisi dengan derau pelacakan > 3 px memakai fallback protokol HUD
  (ditandai `phase_source=hud_fallback`). Rekomendasi perekaman: tidak ada orang di
  belakang partisipan dalam garis pandang kamera.
- **Sinkronisasi:** boxcar HUD gagal (EEG P10 tanpa perbedaan power antar blok, r 0,09);
  tahap kasar kini memakai kecepatan tubuh (pose) → offset +0,90 dtk (IQR 0,07; tanpa
  drift). P02 dengan metode baru: +0,68 dtk (sebelumnya +0,75; dalam ketidakpastian).
- Fase: P10 8 ok / 4 short_hold; median TAHAN agem 0,94 dtk (P02 2,84 dtk) — non-penari
  menahan agem lebih singkat/tidak stabil. Kanal buruk: F7. ICA kedipan hanya −42%.
- ERD: P02 menunjukkan ERD pada TAHAN (mu −41%, beta −29%); **P10 tidak menunjukkan ERD
  di fase mana pun** (TAHAN +125%). n=1 per grup → belum bisa disimpulkan.
- Romberg: P10 EC 55% terekam (15 dtk). **Kedua partisipan tidak punya alpha oksipital
  yang jelas** (alpha relatif 5–12% di EO/EC/Baseline; reaktivitas EC/EO P10 1,08) →
  kemungkinan alpha tenggelam dalam derau broadband (SD 40–90 µV). Risiko besar untuk
  fitur Paper D berbasis alpha. Rekomendasi: cek impedansi dan uji mata-tertutup
  singkat (efek Berger) di awal sesi sebagai QC perekaman.

## Metode Referensi Rata-rata Spektral & Hipotesis H1–H5 (2026-09-23)
- Tahap pipeline `spectral` (eegpipe/spectral.py): specparam per kanal × fase × gerakan;
  indeks global = median perubahan garis latar per belahan (kiri/A1, kanan/A2); tonjolan
  relatif = perubahan tonjolan − median belahan (tafsiran relatif); batas ketelitian per
  partisipan dari uji noise 1/f buatan (P02 3,8 dB; P10 4,7 dB). Status: EKSPLORATIF.
- Indeks global per belahan juga mendeteksi masalah referensi (P02 TURUN kiri +7 vs kanan +1,7 dB).
- Hipotesis H1–H5 di config.yaml (`python -m eegpipe hypotheses`): H1 neural efficiency,
  H2 kestabilan motorik (garis latar), H3 durasi tahan, H4 fronto-parietal kiri pada
  non-penari, H5 lateralisasi kanan saat TAHAN pada penari. P02 vs P10: kelima arah sesuai
  harapan secara deskriptif; H1/H4/H5 di bawah batas ketelitian; uji formal butuh ≥3/grup.

## Temuan P01, P03, P04 (penari) + tahap baseline (2026-09-23)
- **Sinkronisasi (metode baru):** offset utama = median offset lokal 12 repetisi, dua langkah
  (lebar ±2 dtk → sempit ±1 dtk), lolos bila SE ≤ 0,25 dtk. Offset: P01 +4,52±0,25; P02
  +0,58±0,08; P04 +1,37±0,19; P10 +0,95±0,17. **P03 berhenti**: offset per-repetisi bimodal
  (≈0,5–1,25 vs ≈1,8–2,5 dtk; SE 0,29) → perlu tinjauan manual/anchor lain.
- **Baseline.EDF = rekaman istirahat terpisah SEBELUM Trial**, di luar video (dikonfirmasi pengguna;
  isi tidak ada di Trial, sambungan tidak kontinu) → dipakai terpisah (tahap `baseline`):
  kedipan 18–25/mnt → **mata terbuka**; IAF tidak terdefinisi pada semua partisipan; P10
  Baseline terlalu bising (0 jendela oksipital bersih ≤150 µV).
- **Baseline.EDF tidak cocok sebagai acuan ERD**: power-nya jauh lebih rendah dari berdiri di
  dalam Trial → ERD/ERS membengkak (P02 TAHAN −46% vs +363%). Acuan utama tetap DIAM di Trial.
- **P01 & P04 didominasi artefak broadband bahkan pada PRA** (indeks global +7,5/+7,9 dB, rasio
  ptp PRA/baseline 2,3–3,1) → ERD konvensional +100…+1400% tidak dapat ditafsirkan; batas
  ketelitian P01 6,7 dB. Penyebab belum pasti (gerak/ayunan pra-gerak, lengan agem diangkat
  lebih awal — onset lengan P04 hingga 7,4 dtk sebelum turun — atau sisa ketidakpastian sync).
- H3 (durasi tahan agem) konsisten: penari 2,73/2,84/2,97 dtk vs non-penari 0,94 dtk.
  H1–H5 belum dapat diuji (non-penari n=1).
- **Update sync (akhir 2026-09-23):** sinyal video = batang tubuh + pergelangan (SE 0,04–0,24 dtk)
  + validasi onset-ke-onset (koreksi bila |lag| > 0,5 dtk, n ≥ 5, IQR ≤ 0,6). Offset final:
  P01 +3,25 (terkoreksi dari +4,52: ekor artefak panjang membiaskan xcorr), P02 +0,75,
  P03 +0,48 (terkoreksi dari +1,03; lag −0,55 dtk, marginal — tinjau), P04 +1,23, P10 +1,05.
- P04: artefak broadband pada PRA (+7,7 dB) tanpa gerak video yang sepadan — belum terjelaskan.
- Endpoint H (penari n=4 vs non-penari n=1): arah H1–H5 sesuai harapan; H3 paling tegas
  (tahan agem 2,40–2,97 vs 0,94 dtk). Uji formal menunggu ≥3 non-penari.
- **P36–P38 (non-penari, 2026-09-23):** offset +0,70/+0,95/+1,05 dtk (SE 0,10–0,17), Romberg EC
  99–100% terekam. P38: pose kurang andal (4 hud_fallback, hanya 2 epoch ERD, batas ketelitian
  8,2 dB). Uji H1–H5 (4 vs 4, Welch satu arah, FDR): arah H1/H2/H3/H5 sesuai harapan, H4 tidak;
  tidak ada yang signifikan (p 0,14–0,78; p_FDR ≥ 0,36) — daya uji sangat rendah pada n=4/grup.
- **P05–P07 (penari) & P33–P35 (non-penari), 2026-09-23 (mode hemat, belum ditinjau):**
  P05 +1,08, P06 +0,85, P07 +0,70 dtk lolos (P06 hanya 4 epoch; P07 cek onset −2,12 dtk dengan
  n=4, tidak dikoreksi — tinjau). **P33–P35 berhenti di sync**: P33 33% repetisi menempel batas
  pencarian; P34 offset +33 dtk dan P35 −28 dtk (di luar prior ±5 dtk; r halus 0,21/0,01) →
  kemungkinan EEG/video dimulai jauh berbeda atau file tertukar — **tinjau minggu depan**.
  Uji H1–H5 (7 penari vs 4 non-penari): arah H1/H2/H3/H5 sesuai, tidak ada yang signifikan
  (p_FDR ≥ 0,35). Tahan agem penari 2,40–3,10 dtk (n=7) vs non-penari 0,94–3,26 dtk.
- **Audit segmen & pendekatan baru (uji cepat 2026-09-23, skrip scripts/audit_segmen/):**
  Pengguna menetapkan: waktu fase sepenuhnya dari video, offset TETAP 0,85 dtk (median 11 partisipan,
  SD 0,2; dibekukan), pangkas batas fase 0,25 dtk (maks. 15% durasi), TAHAN singkat TETAP dipakai,
  12 segmen digabung per subfase (turun/tahan/naik) → model campuran; agem ka/ki terpisah untuk LI/H5.
  Temuan: penyebab utama gugurnya segmen = aturan "jendela acuan per repetisi harus diam" (non-penari
  kehilangan 5–10 dari 12) → diganti acuan GABUNGAN per partisipan (50% jendela 2 dtk paling diam di
  BERDIRI RILEKS + ISTIRAHAT UTAMA, dari video). Segmen TAHAN: non-penari 4 → 10, penari 9 → 11.
  Presisi per partisipan membaik ±40%. **ERD power total berubah arah** dengan acuan gabungan (TAHAN
  ≈ +5 dB di kedua grup; beda grup lama d −1,25 hilang, d 0,04) → didominasi broadband. Specparam:
  garis latar TAHAN non-penari +7,9 vs penari +2,7 dB (d −0,87, p 0,20; sejalan H2); mu periodik ≈ 0
  di kedua grup (+0,36 vs −0,27 dB; di bawah batas ketelitian). Beda ERD grup lama kemungkinan
  artefak seleksi segmen + pilihan acuan. **Diimplementasikan penuh minggu depan.**
  Per fase (specparam, acuan gabungan; scripts/audit_segmen/specparam_fase.py): garis latar
  non-penari > penari di TURUN (+12,7 vs +5,9 dB, d −0,90) dan TAHAN (d −0,87), hampir sama di NAIK.
  **Mu periodik TURUN: non-penari −0,71 vs penari +0,50 dB (d +1,75, p 0,018 tanpa koreksi; tidak
  lolos FDR atas 9 uji)** → non-penari menunjukkan ERD mu saat turun, penari tidak (sejalan H1).
  Besaran < 1 dB — eksploratif, perlu kohort penuh.
  **Kerangka subsegmen (pengguna):** TURUN = koordinasi/stabilitas dinamis; TAHAN = kontrol
  keseimbangan (durasi = kekuatan/keunggulan, mungkin area selain C3/C4); NAIK = gerak sehari-hari
  (paling mudah). Uji cepat durasi (11 partisipan, median per partisipan, tanpa hud_fallback):
  NAIK penari 1,0 vs non-penari 1,7 dtk (d −2,34, p 0,012); variabilitas TAHAN (CV) 0,25 vs 0,62
  (d −2,12, p 0,019); TAHAN 2,84 vs 1,96 dtk (d +1,18, p 0,19); TURUN 1,50 vs 1,26 dtk (d +0,75).
  Peta 8 area × 3 fase × 3 ukuran (72 uji; scripts/audit_segmen/specparam_area.py): 6 dengan p<0,1
  (≈ peluang), tidak ada yang lolos FDR; terkuat TAHAN temporo-posterior T5/T6 mu periodik
  (non-penari +2,3 vs +0,2 dB, d −2,0) dan TURUN sentral (d +1,75). Frontopolar kemungkinan artefak
  mata/otot. → Durasi & variabilitas subsegmen = penanda paling kuat saat ini; peta area eksploratif.
  **Latensi puncak antar-kanal (scripts/audit_segmen/latensi_puncak.py):** puncak ERD mu relatif
  (mu/broadband) per kanal F3–O2, dikunci onset TURUN, 11 partisipan. Presisi latensi per partisipan
  SD bootstrap ≈ 1,2 dtk; urutan kanal tidak konsisten antar-partisipan (rho Spearman 0,04) →
  "perambatan puncak" antar-kanal TIDAK dapat dipetakan dari data ini (100 Hz, 12 segmen, ERD lambat,
  konduksi volume, referensi telinga ipsilateral). Catatan: mu relatif turun ≈ −3 dB di semua kanal,
  tetapi sebagian dapat berasal dari kenaikan broadband di penyebut. Alternatif: konektivitas fase
  berarah (PSI/wPLI) dalam satu belahan per subsegmen — eksploratif.
  **Konektivitas berarah (scripts/audit_segmen/konektivitas.py):** PSI + wPLI, F3→C3→P3 & F4→C4→P4,
  mu/beta, TURUN/TAHAN, ±76 jendela 0,5 dtk per fase. Tidak ada arah konsisten (semua p ≥ 0,09) dan
  tidak ada beda grup (p_FDR ≥ 0,90); wPLI rendah (0,13–0,37). → Alur antar-area tidak terdeteksi
  dengan data ini; bukan prioritas analisis.
  **Romberg uji cepat (scripts/audit_segmen/romberg_cepat.py; specparam, offset tetap):** EC terekam
  cukup hanya pada 8/11 (P02 10%, P03/P04 0%). Tonjolan alpha periodik kini TERDETEKSI (EC +1,1…+1,9 dB
  di atas garis latar), tetapi reaktivitas EC−EO kecil (+0,3…+0,8 dB; oksipital p 0,10, frontal
  p 0,047 tanpa koreksi) dan tidak berbeda antar grup (p ≥ 0,59). Kendala utama Romberg = cakupan EC,
  bukan pemotongan segmen.

## Temuan P08, P09, P11 (penari) & P30–P32 (non-penari), 2026-09-24
- ⚠️ USANG (lihat PARTISIPAN.xlsx: P29/P30/P34 penari). Grup (dikonfirmasi pengguna): nomor kecil = penari, nomor besar = non-penari, **kecuali P10
  (non-penari, dikonfirmasi)** — jangan tetapkan grup dari nomor saja. Nama file bervariasi: `PXX_Baseline2.EDF` (P08/P11/P30),
  video `PXX_video.webm`; glob `*Baseline*.EDF` / `*.webm` sudah menangkapnya.
- OCR 4 rep × 3 gerakan di keenamnya; pose 0–1% frame tanpa deteksi; tanpa kanal buruk.
- **Sinkronisasi:** P30/P31/P32 +0,98/+0,95/+1,00 dtk. **P09 +1,73 ± 0,17** (tertinggi di kohort;
  offset blok 2 tersebar 0,92–2,78, cek onset −1,40 dtk IQR 2,25) → tinjau. **P08 & P11 gagal QC
  drift** (−0,36 / −0,86 dtk, p ≤ 0,005): offset blok 1 ≠ blok 2 (P08 +1,20 → +0,95 bertahap;
  P11 +1,28 → +0,65, lebih mirip loncatan di ISTIRAHAT UTAMA). Keputusan pengguna: **offset per
  blok** (`sync.offset_blocks` di decisions, batas = awal ISTIRAHAT UTAMA; `sync.to_eeg()`).
- Fase: P08/P11 12 ok; P09 & P31 hanya 7/6 ok (3 incomplete); epoch ERD 5–12.
- **Romberg EC terpotong pada ketiga penari** (P09 9%, P08 45%, P11 66%) vs 98–100% non-penari —
  pola sama dengan P02/P03/P04: EEG dihentikan sebelum video selesai.
- Tahan agem: penari 5,93/2,14/3,34 vs non-penari 4,00/1,34/2,36 dtk.
- H1–H5 (3 vs 3): tidak ada yang signifikan (p_FDR ≥ 0,84); H1 & H4 berlawanan arah. n terlalu kecil.
- Tahap `group` butuh usia (regresi grup × usia) → `data/participants.csv` belum berisi usia.
- Bug diperbaiki: log area_map crash (`SeriesGroupBy.iloc`) sehingga Romberg/baseline/laporan
  tidak pernah jalan setelah area_map.
- **Gabungan dengan audit 2026-09-23 (7 vs 4) — meta-analisis efek tetap Hedges g, 10 penari vs
  7 non-penari** (data individual kohort lama tidak tersimpan; hanya d & rerata di catatan ini;
  kohort baru dihitung dengan skrip audit yang sama, offset tetap 0,85): durasi NAIK g −1,50
  (p_FDR 0,04; I² 34%), mu periodik TURUN g +1,39 (p_FDR 0,04), durasi TAHAN g +1,13 (p_FDR 0,06),
  CV TAHAN g −1,26 (p_FDR 0,06; I² 45%), garis latar TAHAN g −0,77 / TURUN −0,54 (n.s.). Semua
  searah dengan audit lama; efek kohort baru lebih kecil. Mu TURUN < 1,3 dB (di bawah batas
  ketelitian). Beta TAHAN kohort baru d +21 = artefak SD≈0 pada n=3, abaikan.

## Pertanyaan Terbuka untuk Pengguna (mohon dikonfirmasi sebelum coding dimulai)
> Status: pertanyaan 1–4 sudah dijawab (lihat di atas). Yang masih terbuka:
> 5 (struktur folder), 6 (bahasa pemrograman), verifikasi isi `Add_lead`,
> dan posisi region webcam di frame video.

1. Mekanisme start EEG vs start video — dipicu bersamaan atau terpisah? (Penting:
   selisih durasi EDF vs video berbeda arah antara P01 dan P02, jadi tidak ada
   formula offset tunggal yang bisa diasumsikan.)
2. Apa isi channel `Add_lead1` dan `Add_lead2`?
3. Label HUD untuk gerakan "ngeed" belum ditemukan di sampel P01/P02 — nama
   HUD-nya apa, dan di bagian mana urutan task ia muncul?
4. Urutan pasti sub-fase dalam satu siklus agem — apakah selalu
   turun→tahan→naik, atau bervariasi per repetisi/jenis agem?
5. Apakah struktur folder final akan sama persis dengan sampel (`PXX_Baseline.EDF`,
   `PXX_Trial.EDF`, `motor_PXX_Trial_*.webm`) untuk seluruh 38 partisipan, termasuk
   subfolder per grup?
6. Software/bahasa pemrograman pilihan: Python + MNE-Python (disarankan) atau ada
   preferensi lain?

## Batasan yang Harus Selalu Diingat
- Tidak ada elektroda midline (Fz/Cz/Pz) — jangan asumsikan bisa mengukur frontal
  midline theta atau ERD sensorimotor murni di Cz; selalu pakai proxy C3/C4 dan
  sebut eksplisit sebagai limitasi di laporan/naskah.
- Sinkronisasi EEG-video BUKAN given — selalu validasi per partisipan, jangan
  asumsikan offset konstan antar-sesi.
- Rentang usia partisipan sangat lebar (remaja–102 tahun) — pertimbangkan dampaknya
  pada power spektral EEG basal (individual alpha peak frequency bisa bergeser
  pada lansia) sebelum membandingkan lintas grup secara naif.
