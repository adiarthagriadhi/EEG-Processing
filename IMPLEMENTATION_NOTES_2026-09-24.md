# Implementasi Minggu: Offset Tetap 0.85s, 12 Segmen Gabungan, Area-Map

## Status: SELESAI

### 1. Area-Map Stage (✓ SELESAI)
- **File**: `eegpipe/area_map.py` (228 baris)
- **Fitur Utama**:
  - 8 area anatomis: frontopolar, frontal, frontotemporal, sentral, temporal, parietal, temporo_posterior, oksipital
  - Acuan gabungan per partisipan: 50% jendela 2-detik paling diam dari BERDIRI RILEKS + ISTIRAHAT UTAMA
  - Fixed offset 0.85s (median dari 11 partisipan audit, SD 0.2)
  - 12 segmen gabungan per fase (TURUN/TAHAN/NAIK)
  - Trim 0.25s (max 15% durasi) dari edges fase
  - Specparam per area: garis latar (aperiodik) + mu/beta periodik
  - Output: CSV dengan kolom area, phase, garis_latar_db, mu_periodic_db, beta_periodic_db, n_windows

### 2. Pipeline Integration (✓ SELESAI)
- **File**: `eegpipe/pipeline.py` (update)
- **Perubahan**:
  - Tambah `stage_area_map()` function
  - Tambah "area_map" ke STAGES list (urutan: setelah spectral, sebelum romberg)
  - Update `run()` untuk call `stage_area_map()` saat "area_map" dalam stages

### 3. Key Findings dari Audit (Terintegrasi)
- **Presisi gabungan**: ±40% lebih baik dibanding per-repetisi acuan
- **Segmen valid**: P10 non-penari 4→10, penari 9→11 (dengan acuan gabungan vs per-repetisi)
- **ERD power**: Berubah +5 dB (sebelumnya −1.25 dB) dengan acuan gabungan
- **Specparam**: Lebih informatif (separates aperiodic vs periodic)
  - Garis latar TAHAN: non-penari +7.9 vs penari +2.7 dB (d −0.87, p 0.20)
  - Mu periodik TURUN: non-penari −0.71 vs penari +0.50 dB (d 1.75, p 0.018)

### 4. Langkah Selanjutnya (Ketika Data Tersedia)

```bash
# Run area_map untuk satu partisipan
python -m eegpipe run P02 --force area_map

# Run area_map untuk semua partisipan
python -m eegpipe run-all --force area_map

# Analisis statistik group-level (Paper A/D)
python -m eegpipe group
```

### 5. Output yang Diharapkan

Untuk setiap partisipan:
- `data/results/{pid}_area_map.csv` → specparam per area × fase
- Kolom hasil:
  - participant_id, area, phase
  - garis_latar_db: perubahan intercept aperiodik (TAHAN vs DIAM)
  - mu_periodic_db, beta_periodic_db: perubahan tonjolan relatif
  - n_windows: jumlah segmen valid yang digunakan

### 6. Catatan Teknis

1. **Acuan Gabungan**: Menyelesaikan masalah utama audit
   - Sebelumnya: per-repetisi acuan → sebagian partisipan kehilangan 5-10 segmen
   - Sekarang: gabungan 50% jendela paling diam → konsisten di semua partisipan

2. **Fixed Offset**: Dari audit insights
   - Offset median 11 partisipan: 0.85 ± 0.20s (range +0.48 to +1.37s)
   - Fixed 0.85s + combined reference lebih robust dari per-participant offset
   - Per-participant offset tetap dipakai untuk sync video-EEG global

3. **Fase Ketenangan (Quietness)**: Menggunakan 1-30 Hz filtered signal
   - Indikator: median absolute value (lebih robust dari RMS)
   - Source: EEG channels (CHANNELS list)

4. **Specparam Fitting**:
   - Grid: 2-30 Hz @ 0.5 Hz resolution
   - Mode: fixed aperiodic
   - Max peaks: 4
   - Peak width: 2-8 Hz

### 7. Validasi Kode

```
✓ Syntax check: python -m py_compile eegpipe/area_map.py eegpipe/pipeline.py
✓ Import check: from eegpipe import area_map
✓ Stage registration: "area_map" dalam STAGES
✓ Integration: stage_area_map() callable dari run()
```

### 8. Testing Checklist (Ketika Data Ada)

- [ ] Run P02 (sudah ada di audit): bandingkan hasil area_map dengan audit script
- [ ] Run P01, P03, P04 (lainnya dari audit): verifikasi konsistensi
- [ ] Run P36, P37, P38 (non-penari audit): pastikan presisi meningkat
- [ ] Run P05-P07, P10, P33-P35 (mode hemat audit): full analysis
- [ ] Run semua 38 partisipan: end-to-end pipeline

### 9. Hipotesis H6-H13 (Area-Map Exploratory)

Dari audit: area-map sebagai exploratory (hanya 6 dari 72 uji dengan p<0.1).
Prioritas analisis:
- H1-H5: tetap utama (ERD/spectral per-channel)
- H6-H8: durasi & variabilitas subfase (TERKUAT, p<0.05)
- H9-H11: mu periodik per area (eksploratif, p<0.1)
- H12-H13: interaksi subfase & korelasi EEG-behavior

