# Rencana data cleaning bertahap: EEG saat gerak (jalur timestamp manual)

Dasar yang tetap untuk semua tahap:
- Waktu fase dari timestamp manual, offset EEG 0 dtk.
- Jendela observasi dimajukan 0,5 dtk: PRA [turun − 2,5, turun − 0,5]; TURUN [N − 0,5, T];
  TAHAN [T − 0,5, N(aik)]; NAIK [N(aik) − 0,5, B]; POST [B + 0,5, B + 2]; Romberg EC [TT, TT + 30].
- Setiap tahap diukur ulang dengan peta kualitas Tahap 1: % jendela 1 dtk × kanal yang datar, > 150 µV, dan ok,
  per fase. Tahap berikut baru dimulai setelah hasil tahap sebelumnya disetujui.
- Endpoint akhir tetap memakai model v2 (specparam, acuan gabungan, H1–H13), supaya sebanding.

| Tahap | Tujuan | Alternatif | Status |
|---|---|---|---|
| 1 | Inventaris kualitas (tanpa mengubah data) | – | **Selesai** (`tahap1_kualitas/`) |
| 2 | Referensi | A rata-rata per belahan · B rata-rata 16 kanal · C bipolar tetangga · D telinga A1/A2 (sekarang) | Berikutnya; usul A vs D (+B) |
| 3 | Kanal buruk & sinyal datar | A kanal buruk dari istirahat + datar = data hilang (sekarang) · B kanal buruk per segmen · C interpolasi bagian datar pendek | Menunggu |
| 4 | Lonjakan artefak gerak | A ASR (kalibrasi dari acuan diam) · B tolak per jendela dengan ambang per partisipan · C tanpa koreksi, hanya ditandai | Menunggu |
| 5 | Mata & otot | A ICA + klasifikasi otomatis (ICLabel) kedipan + otot · B BSS-CCA untuk otot · C regresi kedipan dari Fp1/Fp2 | Menunggu |
| 6 | Aturan pakai segmen & sensitivitas | Batas % data bersih per segmen; posisi POST; perbandingan varian tahap 2–5 terhadap endpoint | Menunggu |

## Temuan yang mengarahkan urutan
- Tahap 1: saat TURUN/NAIK/POST hanya 5–30% jendela × kanal yang ok; aturan buang > 150 µV akan
  menghabiskan data gerak → artefak perlu dikoreksi, bukan hanya dibuang.
- Tahap 1: kanal dalam satu belahan berkorelasi tinggi saat gerak (r 0,41–0,74), antar belahan ≈ 0 → artefak
  kemungkinan dari elektroda telinga A1/A2. Karena itu referensi (Tahap 2) dikerjakan sebelum ASR/ICA.
- 16 kanal membatasi ICA (≤ 16 komponen, berkurang bila ada kanal diinterpolasi) → ICA sesudah Tahap 2 dan 4.

## Tahap 2 (berikutnya): rincian usulan
- Hitung ulang peta kualitas Tahap 1 untuk referensi A, B, D (C hanya bila A dan B tidak cukup).
- Ukuran: % jendela ok per fase; korelasi dalam/antar belahan saat gerak; power 1–4 Hz dan 20–34 Hz relatif acuan;
  apakah perbedaan kiri–kanan (P08 kiri, P31 kanan) hilang.
- Catatan: referensi rata-rata per belahan menghapus juga aktivitas yang sama di seluruh satu belahan; hasil
  lateralisasi (LI, H5) harus ditafsirkan ulang bila opsi A dipilih.
