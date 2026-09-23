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

## Pertanyaan Terbuka untuk Pengguna (mohon dikonfirmasi sebelum coding dimulai)
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
