# Rujukan metode (analisis baru)

Dasar literatur untuk setiap langkah yang **sudah dilakukan** dan yang **direncanakan**. Status per 2026-09-26.

⚠️ Rujukan diverifikasi dari abstrak / ringkasan hasil pencarian. Naskah lengkap belum dibaca karena server tidak dapat
membuka PubMed/PMC/bioRxiv/Springer. Angka dan detail metode wajib dicek di naskah asli sebelum dikutip. Rujukan
bertanda ‡ belum ditemukan versi ilmiahnya (baru sumber populer).

Kolom **Status**: ✔ sudah diterapkan · ○ direncanakan (RENCANA_ANALISIS.md) · ✗ dipertimbangkan, tidak dipakai.

## A. Rujukan per tahap pipeline

| Tahap | Yang kita lakukan | Status | Rujukan & kaitannya |
|---|---|---|---|
| 1 Timestamp & jendela | Fase dari timestamp manual oleh penari ahli (offset 0); jendela per repetisi mengikuti onset dan durasi fase repetisi itu sendiri | ✔ | **Pilihan metodologis, bukan kompromi** (keputusan pengguna 2026-09-26): tari Bali punya ukuran gerak yang khas (agem, ngeed) dan variasi tempo adalah ciri kulturalnya, sehingga batas fase hanya dapat ditentukan sahih oleh pengamat yang memahami struktur gerak itu; aba-aba HUD dan pelacak pose otomatis tidak menangkapnya (analisis repo: pelacak pose terganggu kamen dan penonton; fase HUD ≠ fase gerak aktual). Jendela yang mengikuti onset & durasi tiap repetisi sejalan dengan logika penguncian pada event gerak (Gwin dkk. 2011: event dari motion capture + time-warping karena durasi siklus berbeda-beda). Yang tetap perlu dilaporkan: reliabilitas anotasi (anotator kedua pada sebagian repetisi, lihat C). |
| 1 Sinyal | Bandpass 1–35 Hz, penanda sinyal datar | ✔ | Klug & Gramann 2021: high-pass ≥ 1 Hz memperbaiki dekomposisi pada data mobile. Bigdely-Shamlo dkk. 2015 (PREP): deteksi kanal datar sebagai langkah awal baku. |
| 1 Epoch TE | Jendela 1 dtk geser 0,25 dtk, hanya bagian informatif tiap fase | ✔ | Lihat bagian B (dasar pemilihan momen). Estimasi spektrum: metode Welch (Welch 1967). |
| 2 Referensi | A: rata-rata per belahan (menggantikan telinga ipsilateral) | ✔ | Bigdely-Shamlo dkk. 2015: referensi rata-rata mengurangi derau bersama, tetapi rentan kanal buruk → versi robust. Rata-rata per belahan adalah adaptasi kita karena referensi asli A1/A2 berbeda per belahan; belum ada rujukan langsung. |
| 3 Kanal buruk | A2: rata-rata belahan robust, pencilan dikeluarkan berulang | ✔ | Bigdely-Shamlo dkk. 2015 (referensi robust iteratif). Delorme 2023: interpolasi/penanganan kanal buruk termasuk sedikit langkah yang terbukti membantu. |
| 4 Lonjakan | ASR k = 20, per belahan (8 kanal), kalibrasi Istirahat ≥ 20 dtk | ✔ | Mullen dkk. 2015 (algoritma ASR); Chang dkk. 2020: k optimal 20–30; Anders dkk. 2020: ASR lebih baik pada tugas motorik (termasuk berdiri satu kaki), kualitas stabil untuk k ≥ 10; studi ASR kanal sedikit (IEEE 2022): parameter perlu disetel untuk jumlah kanal kecil. |
| 4 Validasi ASR | Uji sintetis & distorsi Istirahat (K4) | ✔ | — |
| 4 Validasi ASR semi-simulasi | ERD buatan disuntikkan ke Istirahat nyata → apakah ASR mempertahankannya | ○ | Studi ASR kanal sedikit (IEEE 2022). |
| 5 Mata & otot | ICA/ICLabel, BSS-CCA, regresi Fp1–Fp2 diuji; tidak ada yang diterapkan di analisis utama | ✗ (sensitivitas) | Pion-Tonachini dkk. 2019 (ICLabel); De Clercq dkk. 2006 (BSS-CCA untuk otot); Klug & Gramann 2021 (ICA butuh banyak kanal, 16 kanal terbatas); Downey & Ferris 2023 (iCanClean, butuh kanal acuan derau: `Add_lead` datar, jadi tidak dapat). |
| 6 Aturan pakai | Repetisi dipakai bila cakupan ≥ 75%; ≥ 3 repetisi | ✔ | Frömer dkk. 2018: model campuran per-trial tahan terhadap jumlah trial tak sama → repetisi sebagai unit, bukan rata-rata. |
| Estimasi power | dB relatif Istirahat (M0) | ✔ | Pfurtscheller & Lopes da Silva 1999 (definisi ERD/ERS relatif acuan). |
| Kenaikan power menyeluruh | M1 specparam, M2/M2b relatif, M3, M4 dibandingkan; usul M2b | ✔ pilot, menunggu keputusan | Donoghue dkk. 2020 (komponen aperiodik tercampur dengan power pita); "Power struggles" 2026 (power relatif: mengurangi faktor non-saraf, tetapi pita saling bergantung). |
| Rencana beku & log revisi | Semua pilihan ditetapkan dari ukuran kualitas, tanpa melihat beda grup | ✔ | Pernet dkk. 2020 (COBIDAS MEEG). |
| Sensitivitas "minimal" | Tanpa ASR, hanya filter + penanganan kanal buruk | ○ | Delorme 2023. |
| Statistik | ANCOVA grup + usia, Hedges g, BH | ✔ rencana | Benjamini & Hochberg 1995; model campuran: Frömer dkk. 2018. |

## B. Momen jendela observasi terarah (epoch TE)

| Fase & jendela TE | Alasan | Rujukan |
|---|---|---|
| **Gerak** [onset − 0,5, onset + maks(1; durasi/3)] | ERD mu mulai ±2 dtk dan beta ±1,5 dtk **sebelum** onset, kontralateral lebih kuat; puncak saat eksekusi. Jendela kita hanya menangkap 0,5 dtk pra-onset (kompromi terhadap Berdiri sebelumnya) → ditulis "inisiasi gerak". | Pfurtscheller & Lopes da Silva 1999 |
| | Pada gerak berkelanjutan, alpha/mu pulih sebagian sesudah awal gerak, beta tetap tertekan → bagian **awal** paling informatif untuk mu. | Erbil & Ungan 2007 |
| | Gerak repetitif: tiap fase gerak punya modulasi osilasi sendiri; ERD berkelanjutan mencerminkan keadaan "sedang bergerak", modulasi fase terpisah. | Macerollo & Brown 2017; Seeber dkk. 2014 |
| **Tahan** [onset + durasi/3, Naik] | Saat menahan/menggenggam, beta naik tonik (keadaan dipertahankan). Sepertiga awal dibuang karena masih transisi dari gerak. | Kilavik dkk. 2013; Engel & Fries 2010 |
| **Naik** [onset − 0,5, onset + maks(1; durasi/3)] | Sama dengan Gerak (inisiasi gerak baru). | Pfurtscheller & Lopes da Silva 1999 |
| **Berdiri** TE [onset + durasi/3, akhir − 0,5] → TR [B + 2,5, akhir − 2] | Berdiri sesudah rebound dan sebelum persiapan gerak berikutnya, tanpa tumpang tindih. | Turunan dari Pra-Gerak & Pasca-Naik |
| **Pra-Gerak** [onset − 2, onset] (epoch TR ✔) | ERD persiapan: mu ±2 dtk, beta ±1,5 dtk sebelum onset. Fase tersendiri agar tidak mengencerkan ERD eksekusi. | Pfurtscheller & Lopes da Silva 1999 |
| **Pasca-Naik (rebound beta)** [akhir Naik + 0,5, akhir Naik + 2,5] (epoch TR ✔) | Beta naik melebihi acuan ±0,5 dtk sesudah gerak berhenti, bisa beberapa detik; butuh jeda antar-gerak panjang (Berdiri 8 dtk memenuhi). Jendela Berdiri TE saat ini membuang momen ini. | Pfurtscheller & Lopes da Silva 1999; Kilavik dkk. 2013; *Front. Neurosci.* 2025 (PMBR); Erbil & Ungan 2007 (rebound sesudah gerak berkelanjutan) |
| Alternatif: *time-warping* | Durasi fase berbeda antar-repetisi; spektrogram dapat diregangkan agar event gerak jatuh pada waktu relatif yang sama. Menjadi sensitivitas bila jendela TE dipersoalkan. | Gwin dkk. 2011 |

## C. Evaluasi kualitas gerakan

| Aspek | Rujukan | Implikasi |
|---|---|---|
| Rubrik penilaian teknik tari dari video | Instrumen screening teknik balet (2020, *Med. Probl. Perform. Art.*): penilai terlatih, reliabilitas antar-penilai ICC 0,98, intra-penilai 0,78. Rubrik penilaian tari Yunani anak (2024, *Res. Dance Educ.*). | Penilaian dari video oleh penilai terlatih dapat reliabel bila kriterianya eksplisit. |
| Kriteria tari Bali | Wiraga (gerak: agem = sikap badan, tangan, kaki yang dipertahankan; tandang; tangkep), wirama, wirasa ‡ | Untuk tugas ini relevan **wiraga** saja (agem, kedalaman turun, kestabilan tahan). Perlu rujukan akademik (mis. ISI Denpasar) untuk definisi agem yang baku. |
| Reliabilitas penilai | Koo & Li 2016 (pilih & laporkan bentuk ICC; <0,5 buruk, 0,5–0,75 sedang, 0,75–0,9 baik, >0,9 sangat baik); kappa berbobot untuk skala ordinal 0/1/2. | Dua penilai pada ≥ 20% repetisi; laporkan ICC(2,1) atau kappa berbobot kuadrat. |
| EEG dipilah menurut ketepatan gerak | Tinjauan korelat saraf kesalahan motorik (2021); studi meraih: epoch dibagi galat tinggi/rendah (median per partisipan), theta frontal naik sebanding besar galat; beta sensorimotor dipengaruhi ketepatan aksi. | Model di dalam partisipan: `dB ~ nilai + fase + (1 | partisipan)`, dan perbandingan grup pada repetisi benar saja. |
| Efisiensi neural bergantung ketepatan | Del Percio dkk. 2009 (Romberg vs satu kaki; atlet ERD alpha lebih kecil); tinjauan sistematis 2021 (hasil tidak konsisten). | Beda grup harus dipisahkan dari beda ketepatan gerak. |

## D. Parameter & tafsiran

| Parameter | Rujukan |
|---|---|
| ERD/ERS mu & beta, lateralisasi kontralateral | Pfurtscheller & Lopes da Silva 1999 |
| Beta saat menahan & rebound | Kilavik dkk. 2013; Engel & Fries 2010 |
| Theta fronto-sentral naik dan alpha turun saat keseimbangan makin sulit; frekuensi puncak alpha naik | Hülsdünker dkk. 2015; Edwards dkk. 2018 |
| Efek Berger (mata tertutup vs terbuka) | Barry dkk. 2007 (duduk istirahat) |
| Efisiensi neural pada atlet | Del Percio dkk. 2009 (dua studi); tinjauan sistematis 2021 |
| EEG pada tari & gerak kompleks | Müller, Salem & Schöllhorn 2025; studi butoh 2024; Di Nota dkk. 2017; kelas tari pada Parkinson 2025 |

## E. Daftar pustaka (dengan tautan)
- Anders dkk. 2020, *Med. Biol. Eng. Comput.* — ASR pada tugas motorik. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7560919/
- Barry dkk. 2007, *Clin. Neurophysiol.* 118:2765. https://www.sciencedirect.com/science/article/abs/pii/S1388245707004002
- Benjamini & Hochberg 1995, *J. R. Stat. Soc. B* 57:289.
- Bigdely-Shamlo dkk. 2015, *Front. Neuroinform.* — PREP. https://pubmed.ncbi.nlm.nih.gov/26150785/
- Chang dkk. 2020, *IEEE TBME* 67:1114 — evaluasi ASR. https://pubmed.ncbi.nlm.nih.gov/31329105/
- Dance technique screening instrument 2020 — reliabilitas. https://pubmed.ncbi.nlm.nih.gov/32135002/
- De Clercq dkk. 2006, *IEEE TBME* — BSS-CCA. https://pubmed.ncbi.nlm.nih.gov/17153216/
- Del Percio dkk. 2009, *Brain Res. Bull.* — berdiri. https://pubmed.ncbi.nlm.nih.gov/19429191/
- Del Percio dkk. 2009, *Clin. Neurophysiol.* — ERD alpha atlet. https://www.sciencedirect.com/science/article/abs/pii/S1388245709007561
- Delorme 2023, *Sci. Rep.* 13:2372. https://www.nature.com/articles/s41598-023-27528-0
- Di Nota dkk. 2017, *BMC Neurosci.* 18:28. https://link.springer.com/article/10.1186/s12868-017-0349-0
- Donoghue dkk. 2020, *Nat. Neurosci.* https://www.nature.com/articles/s41593-020-00744-x
- Downey & Ferris 2023, *Sensors* — iCanClean. https://www.mdpi.com/1424-8220/23/19/8214
- Engel & Fries 2010, *Curr. Opin. Neurobiol.* 20:156. https://pubmed.ncbi.nlm.nih.gov/20359884/
- Erbil & Ungan 2007, *Brain Res.* https://pubmed.ncbi.nlm.nih.gov/17689502/
- Frömer, Maier & Abdel Rahman 2018, *Front. Neurosci.* https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2018.00048/full
- Gwin dkk. 2011, *NeuroImage* — EEG terkunci fase jalan. https://pubmed.ncbi.nlm.nih.gov/20832484/
- Hülsdünker dkk. 2015; Edwards dkk. 2018 — dirangkum di https://peerj.com/articles/17313/ dan https://pubmed.ncbi.nlm.nih.gov/30391529/
- Kilavik dkk. 2013, *Exp. Neurol.* https://pubmed.ncbi.nlm.nih.gov/23022918/
- Klug & Gramann 2021, *Eur. J. Neurosci.* https://onlinelibrary.wiley.com/doi/abs/10.1111/ejn.14992
- Koo & Li 2016, *J. Chiropr. Med.* https://pubmed.ncbi.nlm.nih.gov/27330520/
- Macerollo & Brown 2017, *J. Neurophysiol.* 118:4. https://pubmed.ncbi.nlm.nih.gov/28275058/
- Motor errors review 2021. https://pubmed.ncbi.nlm.nih.gov/33603925
- Müller, Salem & Schöllhorn 2025, *Front. Psychol.* https://pubmed.ncbi.nlm.nih.gov/40823410/
- Mullen dkk. 2015, *IEEE TBME* — algoritma ASR.
- Pernet dkk. 2020, *Nat. Neurosci.* — COBIDAS MEEG. https://www.nature.com/articles/s41593-020-00709-0
- Pfurtscheller & Lopes da Silva 1999, *Clin. Neurophysiol.* 110:1842. https://doc.ml.tu-berlin.de/bbci/teaching/PfuSil99.pdf
- Pion-Tonachini dkk. 2019, *NeuroImage* — ICLabel.
- "Power struggles: absolute vs relative EEG power" 2026, *Dev. Cogn. Neurosci.* https://www.sciencedirect.com/science/article/pii/S1878929326000332
- PMBR & jeda antar-gerak 2025, *Front. Neurosci.* https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2025.1547916/full
- Seeber dkk. 2014, *Front. Hum. Neurosci.* https://www.frontiersin.org/articles/10.3389/fnhum.2014.00485/full
- Studi ASR kanal sedikit 2022, *IEEE*. https://ieeexplore.ieee.org/document/9905486/
- Studi butoh (mobile EEG penari) 2024. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11539292/
- Tinjauan sistematis efisiensi neural atlet 2021, *Front. Behav. Neurosci.* https://www.frontiersin.org/journals/behavioral-neuroscience/articles/10.3389/fnbeh.2021.698555/full
- Welch 1967, *IEEE Trans. Audio Electroacoust.* 15:70.
- Wiraga/wirama/wirasa ‡ (sumber populer, perlu padanan akademik). https://www.pustakamadani.com/2019/04/nilai-estetis-tari-wiraga-wirama-dan.html
