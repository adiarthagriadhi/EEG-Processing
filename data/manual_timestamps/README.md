Letakkan `PXX_timestamps.csv` di folder ini (satu file per partisipan). Bila ada, pipeline memakainya
menggantikan OCR + pose + sinkronisasi + deteksi fase (lihat docs/MANUAL_TIMESTAMPS.md).

Format: `urutan,waktu_detik,waktu_hhmmss,label,nama_video`
Label: N / AKA / AKI (mulai turun: ngeed / agem kanan / agem kiri) → T (mulai tahan) → N (mulai naik) → B (berdiri);
TT = mulai tutup mata (Romberg EC). Waktu = detik EEG (offset 0).
