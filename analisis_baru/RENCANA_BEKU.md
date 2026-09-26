# Rencana beku: pipeline EEG saat gerak (metode baru)

**Status:** BEKU sejak 2026-09-25. Versi beku = commit yang menambahkan berkas ini (`git log -- analisis_baru/RENCANA_BEKU.md`).
Parameter di bawah dan di `gerakeeg/verifikasi.py` tidak diubah tanpa entri di **Log revisi**.

**Set penyetelan:** P08, P09 (penari, 10 Sep) dan P31, P32 (non-penari, 14 Sep). Semua pilihan ditetapkan dari data
keempatnya dan hanya berdasarkan **ukuran kualitas data**: % data bersih, kontaminasi otot, galat baku, dan
reliabilitas antar-repetisi. Tidak ada pilihan yang didasarkan pada perbedaan grup atau hasil hipotesis. Hasil
keempatnya tidak dihitung sebagai verifikasi.

## 1. Masukan per partisipan
- `data/raw/PXX/PXX_Trial.EDF`: 16 kanal EEG KT88, 100 Hz.
- `data/manual_timestamps/PXX_timestamps.csv`: kolom `urutan, waktu_detik, label`. Label N/AKA/AKI → T → N → B;
  TT = tutup mata; buka mata = TT − 45 dtk (tetap), atau label BM bila ada. Waktu = detik EEG, offset 0.
- Impor file unggahan: `.venv/bin/python analisis_baru/impor_data.py <file/folder>`.

## 2. Pipeline yang dibekukan
| Langkah | Pilihan beku | Parameter |
|---|---|---|
| Istilah & jendela | Gerak (Ngeed/Agem Kanan/Agem Kiri) → Tahan → Naik → Berdiri; Tutup Mata; Istirahat (turunan) | jendela observasi = [onset − 0,5 dtk, onset berikut]; Berdiri maks. B + 8 dtk; Tutup Mata [TT − 0,5, TT + 30]; Istirahat [B terakhir blok 1 + 8, Gerak pertama blok 2 − 5]; jeda blok > 60 dtk |
| Sinyal | bandpass 1–35 Hz (FIR fase-nol); penanda datar dari EDF mentah | datar: SD < 0,5 µV per 0,2 dtk; kanal-jendela datar bila ≥ 10% sampel datar |
| Epoching | **TE**: jendela 1 dtk, geser 0,25 dtk, hanya di bagian informatif | Gerak & Naik: [onset − 0,5, onset + maks(1; durasi/3)]; Tahan: [onset + durasi/3, Naik]; Berdiri: [onset + durasi/3, akhir − 0,5] |
| Lonjakan (Tahap 4) | **ASR k = 20** pada sinyal kontinu, per belahan (8 kanal), sebelum referensi | kalibrasi: potongan Istirahat 1 dtk, kedelapan kanal tidak datar & ≤ 150 µV, minimal 20 dtk (bila kurang: belahan itu tidak dikoreksi, dicatat); jendela 0,5 dtk; maks. 66% komponen; implementasi `lonjakan.asr_kalibrasi/asr_proses` |
| Referensi (Tahap 2) + kanal buruk (Tahap 3) | **A2**: rata-rata per belahan, robust per jendela | pencilan: z robust log-ptp > 3 DAN > 2× median belahan, iteratif maks. 3; < 2 kanal baik → belahan hilang di jendela itu |
| Aturan bersih | per kanal-jendela | tidak datar DAN peak-to-peak ≤ 150 µV |
| Acuan power | Istirahat, dipotong dengan cara yang sama | dB relatif rata-rata potongan bersih |
| Estimasi | per repetisi × fase × kanal: rata-rata power (linear) jendela bersih; unit independen = repetisi | Welch segmen 1 dtk; theta 4–8, mu 8–13, beta 13–30, otot 20–34 Hz |

Uji sensitivitas yang direncanakan (bukan hasil utama): epoch E dan T; ASR k = 10; referensi telinga (D).

## 3. Kriteria verifikasi per partisipan
Dihitung oleh `jalankan.py verifikasi`, definisi di `gerakeeg/verifikasi.py`. "Fase" = Gerak, Tahan, Naik, Berdiri;
"≥ 3 fase" = setidaknya 3 dari 4.

| Kode | Pertanyaan | Lolos bila |
|---|---|---|
| K0 | Data dapat dipakai? | timestamp tanpa urutan menyimpang; ≥ 8 repetisi lengkap; B terakhir ≤ durasi EDF |
| K1 | TE lebih bersih dari E? (referensi telinga) | otot 20–34 Hz TE ≤ E pada ≥ 3 fase |
| K2a | Referensi A lebih bersih dari telinga? | % kanal-jendela bersih A ≥ telinga pada ≥ 3 fase |
| K2b | Mekanisme artefak telinga ada? | korelasi rata-rata antar-kanal di dalam belahan saat Gerak (referensi telinga) ≥ 0,30 |
| K3 | A2 tidak merugikan? | otot A2 ≤ A0 + 0,1 dB pada ≥ 3 fase DAN kanal-jendela dikeluarkan ≤ 10% |
| K4 | ASR k = 20 aman? | kalibrasi ≥ 20 dtk di kedua belahan; distorsi power Istirahat: median antar-kanal ≤ 0,25 dB DAN kanal terburuk ≤ 1,0 dB; reliabilitas ≥ tanpa ASR − 0,10 pada ≥ 3 fase; waktu direkonstruksi ≤ 40% per belahan |
| K5 | Hasil akhir layak dianalisis? | per fase: ≥ 75% kanal punya ≥ 3 repetisi bersih (dilaporkan per fase; ringkasan = keempat fase) |

## 4. Aturan kohort
- Kriteria K1–K5 **dipertahankan** bila lolos pada **≥ 75% partisipan yang lolos K0**. Dilaporkan juga per grup.
- Kriteria di bawah 75% → **TINJAU**. Pipeline tidak diubah otomatis. Pilihan alternatif yang sudah tercantum
  (Bagian 2) diuji, lalu keputusan dicatat di Log revisi beserta alasannya.
- Partisipan yang gagal K0 tidak dianalisis dan dilaporkan dengan alasannya.
- Partisipan yang gagal satu kriteria tetap dianalisis dengan pipeline beku, **kecuali**:
  - gagal K4 karena kalibrasi < 20 dtk → belahan itu tanpa ASR (otomatis, dicatat);
  - fase yang gagal K5 → fase itu tidak dipakai untuk partisipan tersebut di analisis per-fase.
- Selama verifikasi, perbedaan grup dan hipotesis **tidak dilihat**. Keduanya baru dihitung sesudah keputusan
  kohort dicatat.

## 5. Tahap berikutnya (belum beku)
Tahap 5 (mata & otot: ICA + ICLabel / BSS-CCA / regresi Fp1–Fp2) dan Tahap 6 (aturan pakai jendela). Keputusannya
diambil sesudah verifikasi kohort, pada set penyetelan yang dinyatakan lebih dulu (usul: ±10 partisipan seimbang
grup × hari rekaman × usia), lalu dibekukan dengan cara yang sama.

## 6. Menjalankan
```bash
.venv/bin/python analisis_baru/impor_data.py <file atau folder unggahan>
.venv/bin/python analisis_baru/jalankan.py verifikasi semua      # → hasil/verifikasi/LAPORAN.md
```
Keluaran: `hasil/verifikasi/lolos_gagal_per_partisipan.csv`, `ringkasan_kohort.csv`, `ukuran_per_varian_fase.csv`,
`LAPORAN.md`.

## Log revisi
| Tanggal | Revisi | Alasan |
|---|---|---|
| 2026-09-25 | Buka Mata diturunkan otomatis: BM = TT − 45 dtk (label `BM` tetap diutamakan). Analisis Buka Mata mulai maks(BM + 1, B terakhir + 8 dtk), selesai BM + 30 (= TT − 15). | Pengguna: jarak BM–TT tetap −45 dtk. TT − 45 jatuh 0,1–2,3 dtk sebelum B terakhir (P08/P09/P31/P32), sehingga awal segmen dipindah ke sesudah Berdiri terakhir agar tidak memuat gerak dan tidak memakai ulang jendela Berdiri. Perluasan; parameter Tahap 1–4 dan K0–K5 tidak berubah. |
| 2026-09-25 | Tambah label opsional `BM` (buka mata) → segmen Buka Mata [BM − 0,5, min(BM + 30, TT)]; analisis 1 dtk mulai BM + 1 dtk; aturan bersih & ≥ 8 jendela bersih sama dengan Tutup Mata. Verifikasi melaporkan cakupan Buka Mata. | Permintaan pengguna untuk Paper D (rasio EC/EO). Perluasan masukan; tidak mengubah parameter Tahap 1–4 maupun kriteria K0–K5. |
| 2026-09-25 (sebelum beku) | K4: distorsi Istirahat didefinisikan sebagai median antar-kanal ≤ 0,25 dB DAN kanal terburuk ≤ 1,0 dB (bukan kanal terburuk ≤ 0,1 dB) | Uji skrip pada set penyetelan: kriteria kanal-terburuk ≤ 0,1 dB gagal pada P09/P31/P32 (0,66–0,79 dB di 3–5 kanal, terutama theta), padahal median ≈ 0,00–0,19 dB. Keputusan Tahap 4 didasarkan pada median. Batas baru berdasar besar efek ERD yang dicari (±1 dB) dan galat baku estimasi (±1,3 dB), bukan pada nilai data. Ditetapkan pada set penyetelan, sebelum data lain dilihat. |
| 2026-09-26 | **Epoch TR** (perluasan TE, berdasar rujukan; `epoch.potong_TR`) menjadi epoch utama analisis: Gerak, Tahan, Naik sama dengan TE; tambah **Pra-Gerak** [onset Gerak − 2, onset] dan **Pasca-Naik** [B + 0,5, B + 2,5]; **Berdiri** dipersempit menjadi [B + 2,5, akhir − 2] agar tidak tumpang tindih dengan Pasca-Naik dan Pra-Gerak berikutnya. Naik tidak dimajukan 2 dtk (akan memakan Tahan). Verifikasi K1–K5 tetap dihitung dengan TE. TE (Berdiri lama) menjadi sensitivitas. | Permintaan pengguna sesudah kajian literatur (RUJUKAN.md B): ERD mu/beta mulai 1,5–2 dtk sebelum onset; rebound beta 0,5–2,5 dtk sesudah gerak berhenti. Uji pada set penyetelan (`hasil/banding_jendela_TE_TR/`): Pra-Gerak dan Pasca-Naik masing-masing 40–48 jendela dan 8–12 repetisi lolos R1 per partisipan; Berdiri turun menjadi 43–113 jendela, repetisi lolos 8–12. Tidak ada pilihan berdasar beda grup. |
| 2026-09-26 | Estimasi menyimpan juga power 4–30 Hz (`total4_db`) per jendela dan `*_m2b_db` per repetisi (= rata-rata power pita / rata-rata power 4–30 Hz, relatif Istirahat). Parameter Tahap 1–4 dan K0–K5 tidak berubah. | Keputusan pengguna: ukuran tingkat = M2b, lateralisasi = M0 (RENCANA_ANALISIS). |
