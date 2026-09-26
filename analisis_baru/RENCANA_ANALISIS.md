# Rencana analisis gelombang EEG (metode baru)

**Status:** DRAF untuk dibekukan. Ditulis 2026-09-25, **sebelum** nilai ERD/ERS atau perbedaan grup dilihat. Nilai dB
di `hasil/tahap6_aturan/dataset/` belum dibuka untuk tujuan analisis. Rencana ini dibekukan (commit + entri log)
setelah Tahap 5–6 dibekukan dan **sebelum** skrip analisis dijalankan pada kohort. Setiap perubahan sesudahnya dicatat
di **Log revisi** dan dilaporkan sebagai penyimpangan dari rencana.

Analisis repo (`hasil_analisis/`, H1–H13) hanya menjadi **pembanding** arah temuan; hipotesis di sini dirumuskan ulang
untuk metode baru.

---

## 1. Data masukan
- Pipeline: timestamp manual (offset 0) → 1–35 Hz → ASR k 20 → referensi A2 → epoch TR (TE + Pra-Gerak, Pasca-Naik; Berdiri dipersempit) → aturan bersih
  (RENCANA_BEKU.md) → Tahap 5 (tanpa koreksi mata/otot tambahan) → Tahap 6 (R1 cakupan ≥ 75%, R2 ≥ 3 repetisi).
- Unit analisis:
  - **nilai partisipan** × fase × kanal (`nilai_partisipan.csv`, `lolos_R2`), untuk uji tingkat partisipan;
  - **nilai repetisi** (`nilai_repetisi.csv`, `lolos_R1`), untuk model campuran.
- Ukuran EEG: power pita **theta 4–8, mu 8–13, beta 13–30 Hz** dalam dB relatif Istirahat (jeda antar-blok).
  **ERD** = nilai < 0 (power turun dibanding Istirahat), **ERS** = nilai > 0.
- Demografi: `participants.csv` (grup, usia, dance_years, onset_age, activity_per_month, proporsi_hidup_menari).
  Hari rekaman dari nama video di file timestamp.
- Partisipan yang gagal K0 tidak dianalisis. Sel yang gagal R2 = data hilang. Tidak ada imputasi.

## 2. Batasan yang memengaruhi tafsir (ditetapkan sebelum melihat hasil)
0. **Dasar timestamp manual** (keputusan pengguna 2026-09-26): tari Bali punya ukuran gerak yang khas dan variasi
   tempo adalah ciri kulturalnya. Batas fase ditentukan oleh penari ahli per repetisi, bukan dari aba-aba HUD atau
   deteksi otomatis. Konsekuensi: (a) jendela mengikuti onset dan durasi masing-masing repetisi; (b) variasi durasi
   fase **tidak otomatis berarti ketidakstabilan** — pada penari dapat mencerminkan tempo yang disengaja, sehingga U5
   (CV Tahan) ditafsirkan bersama penilaian ketepatan gerak (Bagian 6b); (c) reliabilitas anotasi diukur dengan
   anotator kedua (penari ahli) pada ≥ 20% repetisi, dilaporkan sebagai selisih onset (median, IK) per label.
1. **Referensi A2** (rata-rata per belahan): setiap kanal diukur **relatif terhadap rata-rata belahannya**. ERD yang
   merata di satu belahan tidak terlihat. Yang terukur adalah ERD **fokal** (mis. C3 lebih kuat daripada kanal kiri
   lainnya). Semua pernyataan ditulis sebagai "ERD sentral relatif belahan".
2. **Tidak ada kanal garis tengah** (Cz/Fz/Pz); sentral = C3/C4.
3. **Referensi telinga ipsilateral asli** tidak dipakai di analisis utama. Hasil dengan referensi telinga (D)
   dilaporkan sebagai sensitivitas.
4. **Frontopolar, frontotemporal, temporal** (Fp1/Fp2, F7/F8, T3/T4) rawan artefak mata/otot. Tidak dipakai untuk
   hipotesis utama.
5. **Gerak dan Naik** hanya diwakili inisiasinya (±1,5 dtk pertama). Temuannya disebut "inisiasi gerak/naik", bukan
   seluruh fase.
6. **Romberg:** buka mata = TT − 45 dtk (tetap). Efek Berger belum terlihat terhadap Istirahat, sehingga diuji ulang
   terhadap Buka Mata sebagai syarat validitas (Bagian 7).
7. **Hari rekaman bertumpang tindih dengan grup** (penari 9–11 Sep; non-penari 12–14 Sep, kecuali P10). Ditangani di
   Bagian 6.

## 3. Pertanyaan & ukuran UTAMA (Paper A: *movement generation*)
Keluarga uji utama = 5 ukuran. Area **sentral** = rata-rata C3 dan C4 (dB, rata-rata kanal yang lolos R2; bila
hanya satu yang lolos, dipakai satu).

| Kode | Ukuran | Alasan (dari konsep, bukan dari data) |
|---|---|---|
| U1 | beta sentral, **inisiasi Gerak** (semua gerakan) | ERD beta pra- dan awal gerak = penanda persiapan motorik |
| U2 | mu sentral, **inisiasi Gerak** | ERD mu awal gerak |
| U3 | beta sentral, **Tahan** | kontrol isometrik berkelanjutan; hipotesis efisiensi neural |
| U4 | mu sentral, **Tahan** | idem |
| U5 | **CV durasi Tahan** (perilaku, dari timestamp) | kestabilan menahan; temuan terkuat analisis repo (H7), diuji ulang dengan waktu manual |

**Arah yang diharapkan (hipotesis efisiensi neural, dua sisi diuji):** penari menunjukkan ERD sentral yang lebih lemah
(nilai lebih mendekati 0) pada U1–U4 dan CV Tahan lebih kecil pada U5. Uji tetap **dua sisi**.

**Uji utama:** per ukuran, ANCOVA tingkat partisipan `ukuran ~ grup + usia` dengan galat baku robust HC3. Efek grup
dilaporkan sebagai Hedges g (dari residu usia) dengan IK 95%, serta nilai p. Koreksi Benjamini-Hochberg (q = 0,05)
atas 5 ukuran U1–U5.

**Model campuran (sensitivitas utama):** nilai repetisi `dB ~ grup + usia + gerakan + (1 | partisipan)` untuk
U1–U4, memakai semua repetisi yang lolos R1 (bukan hanya rata-ratanya).

**Daya uji:** dengan 23 penari vs 15 non-penari, α = 0,05 dua sisi dan daya 80%, efek yang dapat dideteksi sekitar
g ≈ 0,93. Efek yang lebih kecil tidak dapat dinyatakan "tidak ada". Hasil nol dilaporkan dengan IK 95%.

## 4. Pertanyaan SEKUNDER (eksploratif, dilaporkan terpisah)
Masing-masing keluarga dikoreksi BH sendiri dan diberi label eksploratif.

| Kode | Ukuran |
|---|---|
| S1 | ERD sentral **ada**? Uji satu sampel (≠ 0) per grup untuk U1–U4 dan Naik/Berdiri. Ini validitas: tanpa ERD, perbandingan grup sulit ditafsirkan. |
| S2 | **Lateralisasi** Agem: LI = (kontralateral − ipsilateral) untuk mu/beta Tahan dan inisiasi Gerak. Agem Kanan: kontra = C3; Agem Kiri: kontra = C4. Ngeed tidak dipakai. Dibandingkan antar grup. Catatan A2: LI membandingkan C3 relatif belahan kiri dengan C4 relatif belahan kanan. |
| S3 | **Peta area**: 5 area non-rawan (frontal F3/F4, sentral, parietal P3/P4, oksipital O1/O2, temporo-posterior T5/T6) × 4 fase × 3 pita = 60 uji grup. |
| S4 | **Inisiasi Naik** dan **Berdiri** (mu/beta sentral), termasuk kemungkinan ERS beta sesudah gerak pada Berdiri. |
| S5 | **Theta frontal** (F3/F4) Tahan: beban kognitif/kompensasi. |
| S6 | **Perilaku lain** dari timestamp: durasi Gerak, Tahan, Naik (median per partisipan). |
| S7 | **Per gerakan** (Ngeed / Agem Kanan / Agem Kiri) untuk U1–U4 (4 repetisi per gerakan, jadi presisi lebih rendah). |
| S8 | **Rebound beta Pasca-Naik** [B + 0,5, B + 2,5 dtk]: beta sentral relatif Istirahat; uji ≠ 0 (ERS diharapkan) lalu beda grup. Syarat tafsir: kenaikan harus khas beta (M0 beta > 0 **dan** M2b beta ≥ 0); bila hanya M0 yang naik, kenaikan bersifat menyeluruh dan tidak disebut rebound. *Diterapkan di epoch TR (`epoch.potong_TR`), aturan Tahap 6 sama.* Rujukan: Pfurtscheller & Lopes da Silva 1999; Kilavik dkk. 2013. |
| S10 | **Pra-Gerak** [onset − 2, onset]: ERD mu/beta persiapan, sentral dan lateralisasi (Agem). Dilaporkan dengan M0 **dan** M2b: sebelum onset belum ada artefak gerak, sehingga M0 lebih dapat ditafsirkan di sini. *Epoch TR.* Rujukan: Pfurtscheller & Lopes da Silva 1999. |
| S9 | **Ketepatan gerak** (bila penilaian tersedia, Bagian 6b): `dB ~ nilai + fase + (1 | partisipan)` di dalam partisipan untuk U1–U4; beda grup diulang hanya pada repetisi bernilai 2 (benar); interaksi grup × nilai. |

## 5. Dosis-respons (tujuan utama riset menurut catatan repo)
- **Di dalam penari:** `ukuran ~ activity_per_month + usia` (utama), lalu `~ dance_years + usia` dan
  `~ proporsi_hidup_menari`, untuk U1–U5. VIF dilaporkan. Bila VIF(dance_years, usia) > 5, efek tahun menari tidak
  ditafsirkan terpisah dari usia.
- **Seluruh sampel:** `ukuran ~ grup + dance_years + usia` hanya deskriptif. Tahun menari non-penari = 0, sehingga
  tidak terpisah dari grup.
- BH atas 5 ukuran per prediktor. Label eksploratif.

## 6. Kendali pengganggu & sensitivitas (ditetapkan sekarang)
| Kode | Analisis |
|---|---|
| K-otot | Tambahkan indeks otot 20–34 Hz (fase sama) sebagai kovariat. Bila efek grup U1–U4 hilang, perbedaan kemungkinan berasal dari otot/gerak, bukan kortikal. |
| K-data | Bandingkan jumlah repetisi dan % data bersih antar grup. Beda besar = risiko bias seleksi. |
| K-hari | (a) tambahkan % sinyal datar partisipan sebagai kovariat; (b) ulangi hanya pada partisipan yang direkam pada hari yang juga memuat grup lain (P10, P29, P30, P34 dan hari-hari bersama), bila n cukup. |
| K-usia | (a) tanpa kovariat usia; (b) batasi ke rentang usia tumpang-tindih kedua grup (20–57 th); (c) tanpa partisipan > 70 th. |
| K-ref | Ulangi U1–U4 dengan referensi telinga (D). |
| K-epoch | Ulangi U1–U4 dengan epoch T dan E; Berdiri juga dengan jendela TE (lebih panjang). |
| K-ASR | Ulangi dengan ASR k 10. |
| K-mata | Ulangi dengan ICA mata. |
| K-aturan | Ulangi dengan R1 cakupan ≥ 50%. |
| K-minimal | Pemrosesan minimal: tanpa ASR (Tahap 4 dilewati), hanya filter 1–35 Hz + A2. *Tahap 4.* Rujukan: Delorme 2023. |
| K-acuan | ERD Tahan dan Gerak relatif **Buka Mata** (berdiri tenang, mata terbuka, dalam sesi yang sama), selain relatif Istirahat. *Tahap estimasi (acuan alternatif di `epoch.acuan`/`koreksi_global`).* Rujukan: Del Percio dkk. 2009 (acuan berdiri tenang untuk tugas keseimbangan). |
| K-warp | Bila jendela TE dipersoalkan: spektrogram per repetisi diregangkan (*time-warping*) agar batas fase jatuh pada waktu relatif yang sama. *Tahap epoch.* Rujukan: Gwin dkk. 2011. |

**Validasi ASR semi-simulasi (Tahap 4, dilaporkan, bukan kriteria lolos/gagal K4):** ERD buatan (−1, −2, −3 dB mu/beta
di C3 atau C4) disuntikkan ke potongan Istirahat nyata dan diberi artefak gerak dari data Gerak; diukur berapa ERD yang
kembali sesudah ASR per belahan (8 kanal). Rujukan: studi ASR kanal sedikit (IEEE 2022); Chang dkk. 2020.

## 6b. Ketepatan gerak (penilaian per repetisi)
Banyak non-penari hanya benar pada ⅓–½ repetisi (pengamatan pengguna). Ketepatan gerak dapat mengacaukan beda grup
(Del Percio dkk. 2009; tinjauan efisiensi neural 2021).
- Kolom `nilai` (0/1/2) di file timestamp, diisi pada baris Gerak (N/AKA/AKI) tiap repetisi (keputusan pengguna 2026-09-26; dibaca `data.bersihkan_timestamp` → `rep.nilai`). Skala berdasar **wiraga**:
  bentuk agem (badan, tangan, kaki), kedalaman turun, kestabilan saat Tahan, urutan sesuai aba-aba.
  0 = salah/tidak lengkap, 1 = sebagian benar, 2 = sesuai pakem. Rubrik tertulis ditetapkan sebelum menilai.
- Penilai: penari ahli, dari video, **tanpa melihat hasil EEG**. Penilai kedua pada ≥ 20% repetisi (acak, seimbang
  grup); reliabilitas = kappa berbobot kuadrat dan ICC(2,1) (Koo & Li 2016). Bila ICC < 0,75 rubrik diperbaiki dulu.
- Dipakai di S9 dan sebagai kovariat sensitivitas (proporsi repetisi benar per partisipan).

Temuan utama dianggap **kokoh** bila arah efek grup sama di semua sensitivitas dan IK tidak berbalik tanda pada
K-otot, K-ref dan K-usia.

## 7. Romberg: Buka Mata vs Tutup Mata (Paper D)
Buka mata = TT − 45 dtk (tetap menurut protokol, konfirmasi pengguna 2026-09-25). Segmen analisis: Buka Mata
[maks(BM + 1, B terakhir + 8), BM + 30 = TT − 15] (±20 dtk), Tutup Mata [TT + 1, TT + 30]; keduanya dibatasi durasi EDF. Pipeline dan aturan bersih sama. Nilai kanal dipakai bila ≥ 8 jendela bersih.

**Syarat masuk per partisipan:** kedua segmen punya nilai O1/O2 yang lolos. Partisipan dengan EDF terpotong sebelum
Tutup Mata (mis. P09, 14% tercakup) dikeluarkan dari Paper D dan dilaporkan.

**Ukuran (Tier 1, CLAUDE.md Tahap 5b):**
| Kode | Ukuran |
|---|---|
| D1 | alpha (8–13 Hz) oksipital O1/O2 saat Tutup Mata |
| D2 | reaktivitas alpha oksipital = Tutup Mata − Buka Mata (dB; "Romberg quotient" EEG) |
| D3 | mu/alpha sentral C3/C4, Buka Mata dan Tutup Mata |
| D4 | theta frontal F3/F4 saat Tutup Mata |
| D5 | theta fronto-sentral (F3/F4 + C3/C4), Tutup Mata − Buka Mata |
| D6 | frekuensi puncak alpha (IAF, O1/O2 dan P3/P4) Buka & Tutup Mata; NaN bila tidak ada puncak (specparam) |

**Tafsiran Romberg sebagai tugas keseimbangan**, bukan istirahat: berdiri dengan mata tertutup menaikkan tuntutan
postural yang dapat menekan alpha dan menaikkan theta (Hülsdünker dkk. 2015; Edwards dkk. 2018). Efek Berger yang lemah
tidak otomatis berarti data buruk. Pembanding: Baseline.EDF (berdiri tenang mata tertutup, di luar sesi Trial) bila
tersedia — bila alpha oksipital jelas di Baseline tetapi tidak di Tutup Mata, penyebabnya kondisi tugas.

Untuk Romberg, ukuran dihitung sebagai power **relatif Buka Mata** (Tutup Mata − Buka Mata, dB) dan juga relatif
Istirahat. Kondisi mata saat Istirahat utama belum diketahui, jadi Buka Mata menjadi acuan yang lebih jelas.

**Validitas lebih dulu (S-Romberg):** efek Berger (D2 > 0) diuji per partisipan dan per grup sebelum D1–D4
dibandingkan. Bila efek Berger tidak muncul pada mayoritas partisipan, D1–D4 hanya dilaporkan deskriptif.
Kemungkinan penyebabnya dibahas (alpha lemah, referensi A2 menghapus alpha oksipital yang merata di belahan).
Sensitivitas: referensi telinga (D) dan bipolar P3-O1/P4-O2.

**Uji:** Welch/ANCOVA (grup + usia) untuk D1–D4 (BH atas 4). Korelasi parsial Spearman (dikontrol usia) antara
D1–D4 dan waktu stork test di seluruh sampel (BH atas 4). Semua hanya bila syarat validitas terpenuhi.

## 8. Pre-post (Paper B): bersyarat
Semua data saat ini `timepoint = pre`. Bila data post non-penari masuk: analisis RCI dan Gap Closure sesuai CLAUDE.md,
dengan ukuran U1–U5. Rencana Paper B ditulis terpisah sebelum data post dilihat.

## 9. Keluaran yang direncanakan
- Tabel U1–U5: rata-rata ± SD per grup, g [IK 95%], p, p_BH, n per grup.
- Gambar: profil fase (Gerak inisiasi, Tahan, Naik inisiasi, Berdiri) mu/beta sentral per grup, dengan titik per
  partisipan. Topografi 16 kanal per fase hanya deskriptif. Kanal rawan artefak diberi arsiran.
- Tabel sensitivitas (Bagian 6) dan pembanding arah dengan analisis repo (H7 CV Tahan, H11, H12).

## 10. Yang tidak dilakukan
- Tidak memilih ukuran, kanal, fase atau pita berdasarkan hasil uji.
- Tidak menambah uji utama sesudah data dilihat. Uji tambahan diberi label *post hoc*.
- Tidak mengubah pipeline (Tahap 1–6) sesudah rencana ini dibekukan, kecuali melalui Log revisi RENCANA_BEKU.md.

## Log revisi
| Tanggal | Revisi | Alasan |
|---|---|---|
| 2026-09-25 | Draf pertama | – |
| 2026-09-25 | Pasca-pilot: dibandingkan 5 cara menyatakan power (M0–M4) untuk kenaikan power menyeluruh (`hasil/pilot_koreksi_global/`). Usul: ukuran tingkat (U1–U4, peta area) memakai M2b relatif (pita / total 4–30 Hz; tanpa delta yang naik karena gerak); ukuran selisih (LI) memakai M0. **Belum diterapkan; menunggu persetujuan pengguna.** | Pilot menunjukkan kenaikan power menyeluruh 1–3 dB yang menutupi ERD absolut. Kriteria pemilihan ditetapkan sebelum melihat hasil dan tidak memakai perbedaan grup. |
| 2026-09-25 | **Pilot dijalankan** pada set penyetelan (P08, P09, P31, P32) atas permintaan pengguna, sebelum rencana dibekukan. Hasil di `hasil/pilot_analisis/`. | Permintaan pengguna. Konsekuensi: rencana ini sudah "melihat" data pilot. Setiap perubahan sesudah tanggal ini wajib dicatat dengan alasan, dan keempat partisipan tidak dihitung sebagai data konfirmasi. |
| 2026-09-25 | Buka mata = TT − 45 dtk (tetap), analisis mulai sesudah Berdiri terakhir | Konfirmasi pengguna; masih draf |
| 2026-09-25 | Bagian 7 diperinci: label `BM` tersedia → Buka Mata vs Tutup Mata, syarat validitas Berger, ukuran D1–D4 | Label ditambahkan pengguna; masih draf |
| 2026-09-26 | Tambahan dari kajian literatur (RUJUKAN.md): S8 rebound beta pasca-Naik; S9 + Bagian 6b ketepatan gerak; K-minimal, K-acuan (Buka Mata), K-warp; validasi ASR semi-simulasi; D5–D6 dan tafsiran Romberg sebagai tugas keseimbangan. Tahap penerapan dicantumkan per butir. | Permintaan pengguna; ditambahkan sesudah pilot (n 4) dilihat, sehingga dicatat sebagai revisi. Tidak mengubah U1–U5. |
| 2026-09-26 | Epoch utama TE → TR (RENCANA_BEKU log). S8 diterapkan dengan syarat tafsir khas-beta; S10 Pra-Gerak ditambahkan; nilai kualitas gerak dari kolom `nilai` di timestamp. | Permintaan pengguna (jendela berdasar rujukan, maju 2 dtk; kualitas gerak digabung ke timestamp). U1–U5 tidak berubah (Gerak dan Tahan sama dengan TE). |
| 2026-09-26 | Batasan 0: dasar kultural timestamp manual; U5 ditafsirkan bersama nilai ketepatan gerak; reliabilitas anotasi dengan anotator kedua. | Keputusan pengguna. Tidak mengubah ukuran maupun pipeline. |
