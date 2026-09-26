# Tujuan dan metode (analisis baru)

Dokumen induk untuk bagian Pendahuluan (tujuan) dan Metode naskah. Rincian parameter: `RENCANA_BEKU.md`; rencana
uji: `RENCANA_ANALISIS.md`; rujukan lengkap: `RUJUKAN.md`. Status 2026-09-26.

## 1. Tujuan

**Tujuan umum.** Mengkarakterisasi aktivitas osilasi kortikal (EEG) yang muncul pada setiap fase gerak tari Bali —
Ngeed, Agem Kanan, Agem Kiri — yang batas fasenya ditentukan oleh penari ahli, dan membandingkan karakter tersebut
antara penari Bali dan non-penari.

**Tujuan khusus.**
1. Menggambarkan pola ERD/ERS mu (8–13 Hz) dan beta (13–30 Hz) di area sensorimotor (C3/C4) pada fase Pra-Gerak,
   Gerak, Tahan, Naik, Pasca-Naik dan Berdiri.
2. Membandingkan pola tersebut antara penari dan non-penari (ukuran utama U1–U4: mu dan beta sentral saat Gerak dan
   Tahan), dengan usia sebagai kovariat.
3. Menilai lateralisasi sensorimotor pada Agem Kanan vs Agem Kiri.
4. Menilai hubungan karakter EEG dengan ketepatan gerak (nilai 0/1/2 dari penari ahli) di dalam partisipan.
5. (Paper D) Menggambarkan EEG saat tes Romberg (Buka Mata vs Tutup Mata) sebagai tugas kontrol postural dan
   hubungannya dengan Standing Stork Test.
6. (Eksploratif) Hubungan dosis-respons antara pengalaman / aktivitas menari dan karakter EEG.

**Yang bukan tujuan.** Timing (durasi dan variasi tempo tiap fase) bukan hipotesis: variasi tempo adalah ciri
kultural tari Bali. Durasi dilaporkan deskriptif dan dipakai sebagai kovariat (keputusan pengguna 2026-09-26).

## 1b. Prinsip: fenomena, bukan waktu (keputusan pengguna 2026-09-26)
- **Objek analisis = karakter EEG yang muncul pada tiap fase** (tingkat power per pita/area, pola antar fase,
  lateralisasi), bukan kapan EEG berubah.
- **Offset adalah prasyarat teknis yang tunduk pada temuan fisiologis**: tetap 0 (timestamp = saat fenomena terlihat,
  mis. mata mulai ditutup); dicek langsung di EEG (P08: kedipan berhenti tepat sebelum TT). **Tidak ada penyetelan
  offset per individu untuk memperoleh pola tertentu** — itu akan sirkular dan sangat individual. Offset sinkronisasi
  repo hanya sensitivitas; ukuran utama (M2b) terbukti tidak berubah oleh geseran ±1 dtk.
- **Tidak dianalisis karena keterbatasan alat** (16 kanal, 100 Hz, referensi telinga, 2–4 repetisi per gerakan):
  urutan/onset aktivasi dari satu area otak ke area lain (latensi, perambatan, konektivitas berarah), dan latensi
  perubahan EEG sesudah gerak. Analisis repo sudah menunjukkan keduanya tidak dapat dipetakan (latensi puncak
  antar-kanal rho 0,04; PSI/wPLI tanpa arah konsisten). Pra-Gerak dan Pasca-Naik ditafsirkan sebagai **keadaan**
  (tingkat power dalam jendela), bukan sebagai waktu onset.

## 2. Metode: yang diadopsi, dimodifikasi, dan dikembangkan sendiri

Keterangan: **Adopsi** = dipakai sesuai rujukan · **Modifikasi** = prinsip rujukan dipakai, pelaksanaannya diubah
untuk data ini · **Baru** = dirumuskan dalam studi ini (dengan alasan; perlu disebut eksplisit di naskah).

| # | Langkah | Status | Dasar rujukan | Yang diubah & alasannya |
|---|---|---|---|---|
| M1 | **Segmentasi fase oleh penari ahli** (timestamp manual per repetisi, offset 0) | Modifikasi | Penguncian EEG pada event gerak dari motion capture (Gwin dkk. 2011) | Event ditentukan penari ahli dari video, bukan sensor gerak: ukuran gerak tari Bali khas dan variasi tempo bersifat kultural; pelacak pose terganggu kamen dan penonton. Reliabilitas diukur dengan anotator kedua. |
| M2 | **Jendela per fase yang mengikuti durasi repetisi sendiri** (Tahan mulai sepertiga durasi; Gerak/Naik sampai maks(1 dtk; sepertiga durasi)) | Modifikasi | *Time-warping* spektrogram ke fase gerak (Gwin dkk. 2011) | Bukan meregangkan spektrogram, tetapi memilih bagian informatif tiap fase secara proporsional terhadap durasinya, sehingga repetisi dengan tempo berbeda tetap sebanding. |
| M3 | **Epoch TR**: Pra-Gerak [−2, 0], Gerak [−0,5, …], Tahan, Naik, Pasca-Naik [B + 0,5, B + 2,5], Berdiri [B + 2,5, akhir − 2] | Modifikasi | Waktu ERD pra-gerak dan ERS pasca-gerak (Pfurtscheller & Lopes da Silva 1999); beta saat menahan & rebound (Kilavik dkk. 2013); awal gerak paling informatif (Erbil & Ungan 2007) | ERD klasik dihitung per trial terkunci onset. Di sini dihitung per fase sebuah gerak berangkai (turun–tahan–naik–berdiri), dengan jendela yang tidak saling tumpang tindih kecuali 0,5 dtk Pra-Gerak/Gerak. Naik tidak dimajukan 2 dtk agar tidak memakan Tahan. |
| M4 | **Acuan = Istirahat antar-blok** (jeda ±170 dtk, turunan dari timestamp) | Modifikasi | ERD/ERS relatif interval acuan (Pfurtscheller & Lopes da Silva 1999) | Acuan klasik = interval sesaat sebelum tiap trial. Jarak antar-gerak di sini hanya ±6 dtk dan diisi Berdiri, sehingga dipakai istirahat panjang dalam sesi yang sama. Sensitivitas: acuan Buka Mata (berdiri tenang; Del Percio dkk. 2009). |
| M5 | **Jendela 1 dtk geser 0,25 dtk, Welch** | Adopsi | Welch 1967 | Resolusi 1 Hz memadai untuk pita mu/beta pada 100 Hz. |
| M6 | **Filter 1–35 Hz; penanda sinyal datar** | Adopsi + Baru | High-pass ≥ 1 Hz untuk data bergerak (Klug & Gramann 2021); deteksi kanal datar (PREP, Bigdely-Shamlo dkk. 2015) | Batas atas 35 Hz mengikuti low-pass perangkat KT88. Penanda datar per kanal × 0,2 dtk (SD < 0,5 µV) dirumuskan untuk reset amplifier KT88. |
| M7 | **ASR per belahan, k = 20, kalibrasi Istirahat ≥ 20 dtk** (implementasi sendiri) | Modifikasi | ASR (Mullen dkk. 2015); k 20–30 (Chang dkk. 2020); ASR pada tugas motorik (Anders dkk. 2020) | Dijalankan terpisah per belahan (8 kanal) karena referensi telinga ipsilateral berbeda per belahan; diimplementasikan sendiri karena pustaka yang tersedia mengubah data kalibrasi bersih dan mengabaikan k pada 100 Hz. Validasi semi-simulasi (studi ASR kanal sedikit, IEEE 2022) direncanakan. |
| M8 | **Referensi A2: rata-rata per belahan yang robust** | Modifikasi | Referensi rata-rata robust iteratif (PREP, Bigdely-Shamlo dkk. 2015) | Rata-rata dihitung per belahan, bukan seluruh kepala, karena rekaman asli memakai A1 untuk kiri dan A2 untuk kanan. Konsekuensi: ERD yang merata di satu belahan tidak terlihat; yang terukur ERD fokal. Sensitivitas: referensi telinga asli. |
| M9 | **Aturan bersih & aturan pakai** (ptp ≤ 150 µV, tidak datar; repetisi dipakai bila cakupan ≥ 75%, ≥ 3 repetisi) | Baru | Model campuran per-trial tahan terhadap jumlah trial tak sama (Frömer dkk. 2018) | Ambang ditetapkan dari ukuran kualitas data set penyetelan, tanpa melihat beda grup. |
| M10 | **Power relatif M2b**: (power pita / power 4–30 Hz) dibanding Istirahat, dB | Modifikasi | Power relatif ("Power struggles" 2026); pemisahan komponen aperiodik (Donoghue dkk. 2020) | Total dihitung 4–30 Hz (tanpa delta yang naik karena gerak) dan dinyatakan relatif Istirahat, untuk menghilangkan kenaikan power menyeluruh saat bergerak. M0 (absolut) dipakai di jendela tanpa gerak tubuh (Pra-Gerak) dan untuk selisih kontra–ipsi (lateralisasi). *Aturan M0/M2b per jendela masih menunggu persetujuan dan harus diuji pada partisipan baru.* |
| M11 | **Syarat rebound khas-beta** (M0 beta > 0 **dan** M2b beta ≥ 0) | Baru | Rebound beta (Kilavik dkk. 2013) | Mencegah kenaikan power menyeluruh sesudah gerak disebut rebound. |
| M12 | **Indeks lateralisasi** = kontralateral − ipsilateral (dB) | Modifikasi | Lateralisasi ERD kontralateral (Pfurtscheller & Lopes da Silva 1999) | Selisih dB (bukan rasio) dan dihitung antar-belahan yang masing-masing direferensikan ke belahannya sendiri (M8). |
| M13 | **Penilaian ketepatan gerak berbasis wiraga** (0/1/2 per repetisi, kolom `nilai` di timestamp) | Modifikasi | Instrumen screening teknik tari dari video (2020); reliabilitas ICC (Koo & Li 2016) | Kriteria diambil dari wiraga tari Bali (agem, kedalaman turun, kestabilan tahan, urutan); dinilai penari ahli tanpa melihat EEG. |
| M14 | **Romberg**: Buka Mata = TT − 45 dtk; ditafsirkan sebagai tugas keseimbangan | Modifikasi | Efek Berger (Barry dkk. 2007); alpha turun & theta naik pada tugas keseimbangan (Hülsdünker dkk. 2015; Edwards dkk. 2018); Romberg sebagai acuan (Del Percio dkk. 2009) | Buka Mata diturunkan dari protokol tetap. Efek Berger saat berdiri tidak diasumsikan sebesar saat duduk istirahat. |
| M15 | **Statistik**: ANCOVA grup + usia (HC3), Hedges g, BH; model campuran per repetisi | Adopsi | Benjamini & Hochberg 1995; Frömer dkk. 2018 | — |
| M16 | **Rencana beku, set penyetelan terpisah, log revisi** | Adopsi | COBIDAS MEEG (Pernet dkk. 2020) | Set penyetelan (P08, P09, P31, P32) tidak dihitung sebagai konfirmasi. |
| M17 | **Uji sensitivitas** (minimal tanpa ASR, referensi telinga, epoch TE/T/E, k 10, acuan Buka Mata, kovariat otot/durasi) | Adopsi | Delorme 2023 | Temuan dianggap kokoh bila arah efek bertahan. |

### Kontribusi metodologis yang dapat diklaim
1. **Segmentasi EEG berbasis struktur gerak tari yang dianotasi ahli** (M1–M3): menggantikan jadwal aba-aba dan pelacak
   otomatis dengan batas fase menurut kaidah tari, sambil tetap memakai jendela yang dipilih dari literatur ERD.
2. **Penanganan referensi telinga ipsilateral pada EEG 16 kanal saat gerak** (M7–M8): ASR dan referensi robust per belahan.
3. **Pemisahan kenaikan power menyeluruh akibat gerak dari ERD pita** (M10–M11).

### Keterbatasan yang wajib disebut
Tidak ada kanal garis tengah (Cz); 100 Hz dengan low-pass perangkat 35 Hz; 2–4 repetisi per gerakan (±12 per
partisipan); acuan antar-blok, bukan pra-trial; gerak dipicu aba-aba HUD (antisipasi dapat memengaruhi Pra-Gerak);
ICA tidak memadai pada 16 kanal; hari rekaman bertumpang tindih dengan grup.
