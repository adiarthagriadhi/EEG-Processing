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
