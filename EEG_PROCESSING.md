# Panduan Pemrosesan EEG–Video: Penari Bali vs Non-Penari

Panduan kerja langkah demi langkah untuk mengolah data mentah proyek ini
(`PXX_Baseline.EDF`, `PXX_Trial.EDF`, `motor_PXX_Trial_*.webm`) sampai menjadi
tabel ERD/ERS gerakan dan fitur Romberg yang siap dianalisis statistik.

- **Konteks ilmiah, fakta data, dan keputusan desain:** lihat [`CLAUDE.md`](CLAUDE.md).
  Dokumen ini adalah turunan teknisnya (bagaimana mengerjakannya).
- **Status:** potongan kode di bawah adalah **templat** yang belum diuji pada data
  nyata. Status jawaban pertanyaan terbuka ada di [Bagian 15](#15-pertanyaan-terbuka-yang-memblokir).

---

## Daftar Isi

1. [Ringkasan Data & Implikasi Teknis](#1-ringkasan-data--implikasi-teknis)
2. [Struktur Folder](#2-struktur-folder)
3. [Instalasi](#3-instalasi)
4. [Alur Pipeline](#4-alur-pipeline)
5. [Tahap 0 — Manifest](#5-tahap-0--manifest)
6. [Tahap 1 — Timeline Task dari Video (OCR)](#6-tahap-1--timeline-task-dari-video-ocr)
7. [Tahap 2 — Sinkronisasi EEG↔Video](#7-tahap-2--sinkronisasi-eegvideo)
8. [Tahap 3 — Preprocessing EEG](#8-tahap-3--preprocessing-eeg)
9. [Tahap 4 — Epoching Gerakan](#9-tahap-4--epoching-gerakan)
10. [Tahap 5 — ERD/ERS](#10-tahap-5--erders)
11. [Tahap 5b — Fitur Romberg](#11-tahap-5b--fitur-romberg)
12. [Tahap 6 — Statistik](#12-tahap-6--statistik)
13. [Kontrol Kualitas](#13-kontrol-kualitas)
14. [Limitasi untuk Naskah](#14-limitasi-untuk-naskah)
15. [Pertanyaan Terbuka yang Memblokir](#15-pertanyaan-terbuka-yang-memblokir)
16. [Referensi](#16-referensi)

---

## 1. Ringkasan Data & Implikasi Teknis

| Fakta data (dari `CLAUDE.md`) | Implikasi pada pipeline |
|---|---|
| Sampling rate **100 Hz** (Nyquist = 50 Hz) | **Notch 50 Hz tidak bisa diterapkan.** MNE akan error karena 50 Hz tepat di Nyquist. Jangan *resample*. |
| **Filter perangkat sudah terpasang** (terlihat di spektrum P02; header `prefilter` kosong): low-pass curam ≈ **35 Hz**, high-pass ≈ **0,5–1 Hz** | Bandwidth efektif ≈ 1–35 Hz. Filter software 1–35 Hz hanya menyamakan antar-file. Interferensi 50 Hz sudah hilang. **Potensial lambat (LRP) sudah terlemahkan oleh perangkat** (10.3). |
| Analisis sampai beta (≤ 30 Hz) | Masih aman di bawah Nyquist; gamma tidak dapat dianalisis. |
| 16 kanal KT88, **tanpa midline** (Fz/Cz/Pz) | Gunakan proksi: C3/C4 (sensorimotor), F3/F4 atau F7/F8 (frontal), P3/P4, O1/O2. |
| Referensi **ipsilateral**: kiri → A1, kanan → A2 | **Bukan linked-ear dan bukan referensi bersama.** Perbandingan kiri–kanan (C3 vs C4) ikut dipengaruhi beda aktivitas A1 vs A2. *Average reference* tidak sepenuhnya valid di sini (lihat Tahap 3). |
| Nama kanal `Fp1-A1`, `T3-A1`, … | Harus di-*rename* ke `Fp1`, `T3`, … sebelum *montage*. T3/T4/T5/T6 dikenali di montage 10-20 MNE. |
| `Add_lead1`, `Add_lead2` **datar** (P02: SD 0,4 µV, hanya noise kuantisasi) | Tidak berisi sinyal → diabaikan (`misc`). Referensi *linked-ear* **tidak bisa** direkonstruksi; referensi telinga ipsilateral adalah final. |
| P02: **tidak ada puncak alpha jelas** di semua segmen; Baseline kemungkinan mata terbuka | IAF/PAF bisa tidak terdefinisi → aturan `NaN` (11). Sumber PAF untuk NDV perlu dikonfirmasi. |
| P02: EDF 17–34 dtk lebih pendek dari video; Romberg adalah segmen terakhir | Romberg EC mungkin **terpotong**. QC wajib: EDF harus mencakup seluruh segmen Romberg setelah sinkronisasi. |
| Start EEG & video manual oleh dua operator pada hitungan ke-3 | Offset awal ≈ 0 ± 1–2 dtk. Tidak cukup presisi untuk ERD/ERS, jadi disempurnakan dengan korelasi silang sinyal gerak (Tahap 2). |
| Sebagian partisipan tidak mengikuti TURUN→TAHAN→NAIK dengan tepat | Fase aktual **wajib** ditentukan dari video (Tahap 4); onset HUD hanya sebagai jendela pencarian. |
| Header EDF `startdate` palsu (2013-04-01) | Tidak boleh dipakai untuk sinkronisasi. |
| Video `.webm` dari browser (vp9, ~29,4 fps) | Kemungkinan besar ***variable frame rate***. **Waktu frame harus diambil dari timestamp (PTS), bukan `nomor_frame / fps`.** |
| Selisih durasi EDF − video beda tanda antar partisipan | Offset sinkronisasi dihitung **per partisipan**; validasi dengan anchor kedua (Tahap 2). |
| Usia remaja–102 tahun | Pakai *relative power*/%ERD, IAF individual, usia sebagai kovariat. |

---

## 2. Struktur Folder

```
EEG-Processing/
├── CLAUDE.md                     # konteks proyek (sumber kebenaran)
├── EEG_PROCESSING.md             # panduan ini
├── config.yaml                   # parameter pipeline (filter, window, band)
├── data/
│   ├── raw/                      # JANGAN diubah; tidak di-commit ke git
│   │   ├── P01/  P01_Baseline.EDF  P01_Trial.EDF  motor_P01_Trial_<ts>.webm
│   │   └── P02/  ...
│   ├── manifest.csv              # Tahap 0 (+ sync_offset_sec dari Tahap 2)
│   ├── timeline/                 # PXX_task_timeline.csv (Tahap 1), PXX_movement_phases.csv (Tahap 4)
│   └── derivatives/              # PXX_clean_raw.fif, PXX_move-epo.fif
├── scripts/
│   ├── 00_manifest.py
│   ├── 01_ocr_timeline.py
│   ├── 02_sync.py
│   ├── 03_preprocess.py
│   ├── 04_epoch.py
│   ├── 05_erd_ers.py
│   ├── 05b_romberg.py
│   └── 06_stats.py
├── reports/                      # QC HTML/PNG per partisipan
└── results/                      # erd_ers_long.csv, romberg_features.csv
```

> Data mentah EEG/video partisipan **jangan di-commit ke GitHub** (privasi dan ukuran file).
> Tambahkan `data/raw/` ke `.gitignore`.

---

## 3. Instalasi

```bash
python -m venv .venv && source .venv/bin/activate
pip install mne mne-icalabel python-picard numpy scipy pandas matplotlib \
            av pytesseract opencv-python rapidfuzz statsmodels pingouin pyyaml \
            mediapipe            # pose estimation (Tasks API, mediapipe ≥ 1.0) untuk Tahap 4
# Linux tanpa GUI: sudo apt install libegl1 libgles2   (dibutuhkan mediapipe)
# Tesseract OCR engine (sistem):
#   Ubuntu: sudo apt install tesseract-ocr ffmpeg
#   macOS : brew install tesseract ffmpeg
#   Windows: installer dari github.com/UB-Mannheim/tesseract
```

---

## 4. Alur Pipeline

```
Tahap 0  Manifest (participant_id, group, timepoint, age, path…)
   │
Tahap 1  Video ─► crop HUD ─► OCR ─► PXX_task_timeline.csv   (waktu VIDEO)
   │
Tahap 2  Prior hitungan ke-3 (≈0) ─► xcorr gerak video×EEG ─► validasi Romberg
         ─► sync_offset_sec ─► manifest   ⛔ gerbang validasi
   │
Tahap 3  EDF ─► rename/montage ─► filter 1–35 Hz ─► kanal buruk ─► ICA (mata saja)
         (+ verifikasi isi Add_lead)
   │
Tahap 4  Pose video ─► fase aktual TURUN/TAHAN/NAIK + kepatuhan (verifikasi manual)
         ─► offset ─► Epochs per repetisi (onset aktual)
   │
   ├─► Tahap 5   ERD/ERS theta/mu/beta per fase ─► LI, topografi beta ─► erd_ers_long.csv
   ├─► Tahap 5   LRP (cabang filter 0,05–8 Hz, onset ekstrapolasi) ─► lrp.csv
   └─► Tahap 5b  Romberg EO/EC ─► romberg_features.csv (join dgn Stork Test)
   │
Tahap 6  Mixed model; Welch indeks gerakan + BH + sensitivitas usia (Paper A);
         Welch + korelasi parsial Romberg Tier 1 × Stork (Paper D);
         RCI, NDV, Gap Closure (Paper B); korelasi parsial Romberg × Stork
```

Semua parameter disimpan di satu file `config.yaml`, jangan ditulis langsung (*hardcode*) di skrip:

```yaml
sfreq_expected: 100
filter: {l_freq: 1.0, h_freq: 35.0}   # perangkat KT88 sudah LP ≈ 35 Hz & HP ≈ 0,5–1 Hz
hud_box: {x0: 960, y0: 250, x1: 1280, y1: 480}   # verifikasi per file
webcam_box: {x0: null, y0: null, x1: null, y1: null}   # area webcam di frame komposit
participant_box: {x0: null, y0: null, x1: null, y1: null}   # area partisipan saja, TANPA operator
pose_model: models/pose_landmarker_full.task
ocr_sample_sec: 0.2
sync: {prior_offset_sec: 0.0, max_lag_sec: 5.0, max_drift_sec: 0.2, max_residual_sec: 0.5}
phases: {late_sec: 1.5, short_hold_sec: 1.0, min_phase_sec: 0.5}
bands: {theta: [4, 8], mu: [8, 13], beta: [13, 30]}
roi: [C3, C4, P3, P4, O1, O2]
is_simulated: true    # ganti ke false saat data riil dipakai (12.6)
lrp: {l_freq: 0.05, h_freq: 8.0, tmin: -1.5, tmax: 0.5, baseline: [-1.5, -1.0], window: [-0.2, 0.0]}
erd:
  tmin: -2.5          # detik relatif onset TURUN aktual; tmax = durasi gerak terpanjang + 1 dtk
  baseline: [-2.0, -0.5]
```

---

## 5. Tahap 0 — Manifest

Struktur folder (dikonfirmasi pengguna): **satu folder per partisipan**, berisi
rekaman video, `PXX_Baseline.EDF`, dan `PXX_Trial.EDF`. Kelompok, usia, dan timepoint
**tidak** tersimpan di folder, jadi diambil dari file demografis terpisah
(`data/participants.csv`) yang digabung lewat `participant_id`.

`data/manifest.csv`:

| participant_id | group | timepoint | age | path_baseline_edf | path_trial_edf | path_video | sync_offset_sec | sync_validated | notes |
|---|---|---|---|---|---|---|---|---|---|
| P01 | penari | NA | … | data/raw/P01/P01_Baseline.EDF | data/raw/P01/P01_Trial.EDF | data/raw/P01/motor_P01_Trial_….webm | | | |

```python
from pathlib import Path
import pandas as pd

rows = []
for d in sorted(Path("data/raw").glob("P*")):
    pid = d.name
    video = sorted(d.glob(f"motor_{pid}_Trial_*.webm"))
    rows.append(dict(
        participant_id=pid,
        path_baseline_edf=next(iter(d.glob(f"{pid}_Baseline.EDF")), None),
        path_trial_edf=next(iter(d.glob(f"{pid}_Trial.EDF")), None),
        path_video=video[0] if len(video) == 1 else None,   # 0 atau >1 file → cek manual
        sync_offset_sec=None, sync_validated=False,
    ))
man = pd.DataFrame(rows)
# group, timepoint, age digabung dari file data demografis (join by participant_id)
man.to_csv("data/manifest.csv", index=False)
print(man.isna().sum())      # laporkan file yang hilang
```

---

## 6. Tahap 1 — Timeline Task dari Video (OCR)

**Tujuan:** menghasilkan daftar segmen `label + sub-fase` beserta waktu mulai dan
selesainya **dalam detik video**.

### 6.1 Kalibrasi kotak HUD per file

Simpan satu frame dari setiap video, lalu periksa apakah kotak HUD dari `config.yaml`
tepat mengenai panel instruksi:

```bash
ffmpeg -ss 60 -i motor_P01_Trial_<ts>.webm -frames:v 1 reports/P01_frame60.png
```

### 6.2 Cek frame rate & timestamp

```bash
ffprobe -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time \
        -of csv=p=0 motor_P01_Trial_<ts>.webm | head
ffprobe -v error -show_entries format=duration -of csv=p=0 motor_P01_Trial_<ts>.webm
```

Jika jarak antar-timestamp tidak konstan, berarti video *variable frame rate* dan
waktu **harus** diambil dari PTS. Kode di bawah sudah memakai PTS.

### 6.3 OCR dan deteksi batas segmen

```python
import re
import av, pytesseract
import pandas as pd
from rapidfuzz import process, fuzz

MOVES = ["NGEED", "AGEM KANAN", "AGEM KIRI"]
PHASES = ["TURUN", "TAHAN", "NAIK"]
VOCAB = [f"{m} {p}" for m in MOVES for p in PHASES] + [
    "ISTIRAHAT UTAMA", "BERDIRI RILEKS",
    "BERDIRI FOKUS MATA TERBUKA", "BERDIRI MATA TERTUTUP",
]

def normalize(text):
    text = re.sub(r"[\d:()]+|DETIK", " ", text.upper())   # buang countdown & "(30 Detik)"
    text = re.sub(r"[^A-Z ]", " ", text)
    text = " ".join(text.split())
    match = process.extractOne(text, VOCAB, scorer=fuzz.token_set_ratio)
    return (match[0], match[1]) if match and match[1] >= 80 else ("UNKNOWN", 0)

def ocr_video(path, box, step=0.2):
    x0, y0, x1, y1 = box
    samples, next_t = [], 0.0
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            t = frame.time                     # PTS dalam detik
            if t is None or t < next_t:
                continue
            next_t = t + step
            img = frame.to_ndarray(format="gray")[y0:y1, x0:x1]
            raw_text = pytesseract.image_to_string(img, config="--psm 6")
            label, score = normalize(raw_text)
            samples.append(dict(t=t, raw=raw_text.strip(), label=label, score=score))
    return pd.DataFrame(samples)

def to_segments(samples):
    s = samples[samples.label != "UNKNOWN"].reset_index(drop=True)
    seg_id = (s.label != s.label.shift()).cumsum()
    seg = s.groupby(seg_id).agg(label=("label", "first"),
                                start_time_video_sec=("t", "first"),
                                end_time_video_sec=("t", "last"),
                                n_samples=("t", "size"))
    seg[["task", "subphase"]] = seg.label.str.extract(r"^(NGEED|AGEM KANAN|AGEM KIRI)\s+(TURUN|TAHAN|NAIK)$")
    seg.task = seg.task.fillna(seg.label)
    return seg.reset_index(drop=True)
```

Output `data/timeline/PXX_task_timeline.csv` berisi kolom `label, task, subphase,
start_time_video_sec, end_time_video_sec`, ditambah nomor repetisi (hitung per task
secara berurutan).

**Validasi (wajib):** periksa manual 10–15% segmen dengan membandingkan waktu di
CSV terhadap video di pemutar (VLC menampilkan waktu presisi). Juga pastikan:

- Jumlah repetisi per gerakan = 4.
- Urutan sub-fase HUD selalu `TURUN → TAHAN → NAIK` untuk NGEED, AGEM KANAN, dan AGEM KIRI.
  Catatan: ini adalah urutan **instruksi**. Fase yang benar-benar dilakukan partisipan
  dikonfirmasi dari video di Tahap 4.
- Sampel `UNKNOWN` berturut-turut > 1 detik → periksa frame tersebut.

---

## 7. Tahap 2 — Sinkronisasi EEG↔Video

⛔ **Gerbang:** jangan lanjut ke Tahap 4 untuk partisipan yang `sync_validated = False`.

Definisi (disimpan di manifest):

```
t_eeg = t_video + sync_offset_sec
sync_offset_sec = t_anchor_EEG − t_anchor_video
```

### 7.1 Titik awal: aba-aba hitungan ke-3

EEG dan video dimulai manual oleh dua operator pada hitungan ke-3. Karena itu
**prior** `sync_offset_sec ≈ 0`, dengan ketidakpastian sekitar ±1–2 dtk (waktu reaksi
tiap operator dan delay inisialisasi software). Prior ini cukup untuk membatasi
pencarian, tetapi **tidak cukup presisi** untuk ERD/ERS: jendela analisis berorde
ratusan milidetik. Selisih durasi EDF−video (+12 dtk pada P01, −17 s.d. −34 dtk pada
P02) kemungkinan besar berasal dari waktu **stop** yang berbeda, sehingga tidak
bertentangan dengan start yang hampir bersamaan.

### 7.2 Penyempurnaan: korelasi silang sinyal gerak (seluruh sesi)

Setiap gerakan ngeed/agem menghasilkan **gerak tubuh di video** dan **artefak
gerak/otot di EEG** secara bersamaan. Dengan mengorelasikan kedua sinyal sepanjang
sesi (12 repetisi × 3 sub-fase), offset ditentukan oleh banyak kejadian sekaligus,
bukan satu anchor. Hasilnya lebih presisi (±0,1 dtk pada resolusi 10 Hz) dan lebih
tahan terhadap satu kejadian yang ambigu.

```python
import numpy as np
import av, mne
from scipy.signal import correlate, correlation_lags

FS = 10.0   # resolusi bersama (Hz)

def video_motion(path, box, fs=FS):
    """Energi gerak (selisih antar-frame) di area partisipan, di-resample ke grid fs."""
    x0, y0, x1, y1 = box                           # participant_box di config.yaml (tanpa operator)
    ts, energy, prev = [], [], None
    with av.open(str(path)) as c:
        for fr in c.decode(video=0):
            img = fr.to_ndarray(format="gray")[y0:y1, x0:x1].astype(np.float32)
            if prev is not None:
                ts.append(fr.time); energy.append(np.abs(img - prev).mean())
            prev = img
    grid = np.arange(0, ts[-1], 1 / fs)
    return grid, np.interp(grid, ts, energy)      # interpolasi → aman untuk VFR

def eeg_motion(raw, fs=FS):
    """Envelope artefak gerak/otot di kanal frontal-temporal (20–34 Hz: perangkat LP ≈ 35 Hz)."""
    picks = ["Fp1", "Fp2", "F7", "F8", "T3", "T4"]
    env = raw.copy().pick(picks).filter(20, 34).apply_hilbert(envelope=True) \
             .get_data().mean(axis=0)
    grid = np.arange(0, raw.times[-1], 1 / fs)
    return grid, np.interp(grid, raw.times, env)

def xcorr_offset(v, e, fs=FS, max_lag_sec=5.0):
    """Lag (dtk) yang memaksimalkan korelasi; positif = kejadian muncul lebih akhir di EEG."""
    z = lambda x: (x - x.mean()) / x.std()
    v, e = z(np.log1p(v)), z(np.log1p(e))
    cc = correlate(e, v, mode="full") / min(len(v), len(e))
    lags = correlation_lags(len(e), len(v), mode="full") / fs
    ok = np.abs(lags) <= max_lag_sec              # batasi ke sekitar prior ≈ 0
    i = np.argmax(cc[ok])
    return lags[ok][i], cc[ok][i], (lags[ok], cc[ok])

raw = mne.io.read_raw_edf(path_trial_edf, preload=True)
raw.rename_channels(lambda ch: ch.split("-")[0])
tv, v = video_motion(path_video, participant_box)
te, e = eeg_motion(raw)
offset, peak, (lags, cc) = xcorr_offset(v, e)
print(f"sync_offset_sec = {offset:+.2f} dtk (r = {peak:.2f})")
```

**Dari setting ruang rekaman:** operator duduk tepat di samping/belakang partisipan dan
memegang berkas kabel elektroda. Karena itu:

- Area sinyal gerak video harus **hanya area partisipan**. Gerak operator di video tidak
  punya pasangan di EEG dan akan menurunkan korelasi.
- Tarikan atau goyangan kabel oleh operator menimbulkan artefak di EEG **tanpa** gerak
  partisipan di video. Hal ini menurunkan `r` tetapi tidak menggeser puncak lag, selama
  gerakan partisipan yang dominan. Catat di log jika operator terlihat menangani kabel.

Kriteria penerimaan:

- Puncak korelasi **tunggal dan jelas** (plot `lags` vs `cc`), serta |offset| ≤ ~2 dtk
  sesuai prior hitungan ke-3. Jika puncaknya lebih jauh atau datar, periksa manual.
- **Cek drift:** jalankan `xcorr_offset` terpisah pada paruh pertama dan paruh kedua
  sesi. Jika selisihnya > 0,2 dtk, gunakan model linear `t_eeg = a · t_video + b` yang
  dicocokkan dari offset beberapa jendela waktu.
- Overlay visual: plot `v` (digeser offset) dan `e` pada satu grafik untuk 2–3
  repetisi gerakan.

### 7.3 Validasi independen (akhir sesi): transisi Romberg mata terbuka → tertutup

Saat mata tertutup, **alpha oksipital (O1/O2) naik dengan jelas** dan biasanya
diawali artefak kedip/tutup mata di Fp1/Fp2. Tanda ini terlihat objektif di EEG dan
waktunya diketahui dari HUD. Anchor ini dipakai untuk:

1. **Memvalidasi** offset dari 7.2 dengan tanda yang bukan berasal dari gerak:
   selisih prediksi vs observasi harus < ~0,5 dtk.
2. **Mendeteksi drift clock** di ujung sesi, sebagai pelengkap cek paruh-sesi di 7.2.

```python
alpha = raw.copy().pick(["O1", "O2"]).filter(8, 13) \
           .apply_hilbert(envelope=True).get_data().mean(axis=0)
# Plot alpha envelope di sekitar prediksi t_eeg transisi EO→EC
```

Catat di manifest: `sync_offset_sec`, `sync_xcorr_r`, `sync_drift_sec` (selisih paruh
1 vs 2), `sync_method`, `sync_residual_sec`
(selisih pada anchor validasi), `sync_validated` (True/False).

---

## 8. Tahap 3 — Preprocessing EEG

```python
import mne

raw = mne.io.read_raw_edf(path_trial_edf, preload=True)
assert raw.info["sfreq"] == 100

# 1) Rename & tipe kanal
raw.rename_channels(lambda ch: ch.split("-")[0])          # "C3-A1" → "C3"
raw.set_channel_types({"Add_lead1": "misc", "Add_lead2": "misc"})   # sampai terverifikasi (8.1)
raw.set_montage("standard_1020")  # MNE ≥1.13 menyarankan nama baru "colin27_1020"

# 2) Filter — TANPA notch (50 Hz = Nyquist). Perangkat sudah LP ≈ 35 Hz dan HP ≈ 0,5–1 Hz;
#    filter software menyamakan karakteristik antar-file
raw.filter(l_freq=1.0, h_freq=35.0)

# 3) Kanal buruk (inspeksi visual), lalu interpolasi
raw.plot(duration=30, scalings=dict(eeg=100e-6))
raw.interpolate_bads(reset_bads=True)
```

### 8.1 Referensi

Data direkam dengan **referensi telinga ipsilateral** (kiri–A1, kanan–A2).

| Opsi | Kapan dipakai | Catatan |
|---|---|---|
| **Pertahankan referensi asli** (disarankan untuk analisis utama) | ERD/ERS dinyatakan dalam % terhadap baseline di kanal yang sama | Offset referensi sebagian besar hilang dalam normalisasi %; perbandingan antar-hemisfer tetap dilaporkan sebagai limitasi. |
| *Average reference* | Analisis sensitivitas | Dengan 16 kanal tanpa midline dan referensi campuran, hasilnya belum menjadi *average reference* yang sebenarnya. |
| Linked-ear matematis | **Hanya jika** verifikasi 8.1.1 membuktikan `Add_lead` berisi A1/A2 | `Ckiri_linked = Ckiri − ½(A2−A1)`, `Ckanan_linked = Ckanan + ½(A2−A1)`. |

#### 8.1.1 Verifikasi isi `Add_lead1` / `Add_lead2`

> **Hasil P02 (2026-09-23): datar.** SD 0,4 µV; nilai hanya −3,0 s.d. +0,2 µV dengan
> langkah 0,1 µV (resolusi EDF), sedangkan kanal EEG ber-SD 18–95 µV. Kanal ini tidak
> berisi sinyal, jadi rekonstruksi *linked-ear* tidak mungkin. Tetap jalankan cek di
> bawah untuk beberapa partisipan lain; jika semuanya datar, kanal ini diabaikan.

Menurut pengguna, kedua kanal ini "sepertinya lead referensi". Sebelum dipakai,
periksa secara empiris untuk tiap beberapa partisipan:

```python
import numpy as np

add = raw.copy().pick(["Add_lead1", "Add_lead2"]).filter(1, 40, picks="misc")
eeg = raw.copy().pick("eeg")
print("SD (µV):", add.get_data().std(axis=1) * 1e6)       # datar (~0)? mirip EEG (10–50)?
corr = np.corrcoef(np.vstack([add.get_data(), eeg.get_data()]))[:2, 2:]
for name, r in zip(["Add_lead1", "Add_lead2"], corr):
    print(name, dict(zip(eeg.ch_names, np.round(r, 2))))
add.compute_psd(picks="misc", fmax=45).plot()
add.plot(duration=20)                                      # cari QRS jantung (ciri khas telinga)
```

Cara membaca hasil:

| Pola | Kemungkinan isi | Tindakan |
|---|---|---|
| Nyaris datar / noise sangat kecil | Kanal tidak terpakai | Abaikan (`misc`) |
| Korelasi **negatif** seragam dengan semua kanal kiri (Add_lead1) atau kanan (Add_lead2), ada QRS jantung | Potensial telinga A1/A2 terhadap referensi internal amplifier | Rekonstruksi linked-ear dari selisih `Add_lead2 − Add_lead1`, tetapi uji dulu tanda dan skalanya pada beberapa partisipan |
| Satu kanal berisi `A1−A2` (atau `A2−A1`) | Selisih antar-telinga | Rekonstruksi langsung dengan rumus di atas |
| Kedip besar, lebih kuat dari Fp1/Fp2 | EOG | `set_channel_types(... "eog")`, pakai di ICA |
| Broadband tinggi saat gerak | EMG | Pakai sebagai referensi artefak gerak (juga membantu sinkronisasi 7.2) |

Konfirmasi juga ke manual/konfigurasi montage perangkat KT88 yang dipakai saat
perekaman. Keputusan final dicatat di `CLAUDE.md`.

### 8.2 ICA — hanya artefak mata

```python
from mne.preprocessing import ICA

n_eeg = len(mne.pick_types(raw.info, eeg=True))          # 16; Add_lead (misc) tidak dihitung
ica = ICA(n_components=n_eeg - len(raw.info["bads"]) - 1,  # rank turun karena interpolasi
          method="picard", fit_params=dict(extended=True, ortho=False),
          random_state=97, max_iter="auto")
ica.fit(raw.copy().pick("eeg"), reject_by_annotation=True)

eog_idx, scores = ica.find_bads_eog(raw, ch_name=["Fp1", "Fp2"])  # Fp sebagai proksi EOG
ica.plot_components(); ica.plot_sources(raw); ica.plot_properties(raw, picks=eog_idx)
ica.exclude = eog_idx        # setelah diverifikasi visual
ica.save(f"data/derivatives/{pid}-ica.fif", overwrite=True)   # dipakai ulang di cabang LRP (8.3)
ica.apply(raw)
raw.save(f"data/derivatives/{pid}_clean_raw.fif", overwrite=True)
```

- **ICLabel kurang andal di sini**: ICLabel dilatih pada data dengan filter 1–100 Hz,
  sedangkan data ini hanya sampai 50 Hz. Hasilnya boleh dipakai sebagai saran, tetapi
  keputusan akhir tetap berdasarkan inspeksi visual.
- **Jangan buang komponen "otot/gerak" secara otomatis**. Ritme mu/beta sensorimotor
  bisa ikut terbuang. Buang hanya komponen mata yang jelas (kedip dan saccade).
- Jika `Add_lead1/2` ternyata EOG, ganti `ch_name` di `find_bads_eog` ke kanal tersebut.
- **Gerak mata terkunci waktu dengan gerakan.** Partisipan menatap monitor instruksi saat
  menurunkan tubuh, sehingga sudut pandang berubah dan muncul gerak mata vertikal tepat di
  sekitar onset TURUN. Artefak ini paling berpengaruh pada F3/F4 (theta frontal) dan LRP.
  Pastikan komponen gerak mata vertikal ikut dibuang, lalu periksa rata-rata Fp1/Fp2
  terhadap onset setelah ICA.
- Segmen dengan artefak gerak besar diberi anotasi `BAD_motion` dan tidak dipakai
  untuk *fit* ICA.

### 8.3 Cabang preprocessing terpisah untuk LRP (Paper A)

> ⚠️ **Temuan P02:** perangkat KT88 sudah menerapkan *high-pass* ≈ 0,5–1 Hz saat
> perekaman (power turun > 15 dB di bawah ~0,8 Hz). Filter software 0,05 Hz tidak bisa
> mengembalikan komponen lambat yang sudah hilang. Lihat 10.3 sebelum memakai cabang ini.

LRP adalah **potensial lambat**, sedangkan *high-pass* 1 Hz untuk ERD/ERS akan
menghapusnya. Karena itu LRP memakai salinan data sendiri dari EDF mentah. ICA tetap
di-*fit* pada data 1 Hz (lebih stabil), lalu **diterapkan** ke data LRP.

```python
raw_lrp = mne.io.read_raw_edf(path_trial_edf, preload=True)
raw_lrp.rename_channels(lambda ch: ch.split("-")[0])
raw_lrp.set_channel_types({"Add_lead1": "misc", "Add_lead2": "misc"})
raw_lrp.info["bads"] = bads_from_main_branch            # kanal buruk yang sama
raw_lrp.filter(l_freq=0.05, h_freq=8.0)                 # potensial lambat; low-pass per Paper A
raw_lrp.interpolate_bads(reset_bads=True)
ica = mne.preprocessing.read_ica(f"data/derivatives/{pid}-ica.fif")
ica.apply(raw_lrp)
raw_lrp.save(f"data/derivatives/{pid}_lrp_raw.fif", overwrite=True)
```

---

## 9. Tahap 4 — Epoching Gerakan

### 9.1 Konfirmasi fase aktual dari video (wajib)

Semua gerakan (NGEED, AGEM KANAN, AGEM KIRI) diinstruksikan `TURUN → TAHAN → NAIK`,
tetapi **sebagian partisipan tidak mengikutinya dengan tepat** (terlambat, hold
terlalu singkat, atau urutan tidak lengkap). Karena itu **onset epoch ditentukan dari
gerak tubuh di video, bukan dari label HUD**. Label HUD hanya dipakai sebagai jendela
pencarian.

**Langkah semi-otomatis:**

1. **Lintasan tubuh:** pose estimation pada region webcam untuk mengambil posisi
   vertikal **batang tubuh** di setiap frame, menggunakan timestamp PTS. Ngeed/agem
   menurunkan tubuh dengan menekuk lutut, sehingga batang tubuh turun saat TURUN,
   stabil saat TAHAN, dan naik saat NAIK. Kode di 9.1.1.
2. **Segmentasi otomatis** per repetisi, dalam jendela `[onset HUD TURUN − 1 dtk,
   akhir HUD NAIK + 3 dtk]` (jendela harus mencakup posisi berdiri sebelum dan sesudah).
   Posisi pinggul dinormalisasi ke kedalaman gerak (0 = berdiri, 1 = terendah), lalu
   fase ditentukan dari persilangan **10% dan 90%**. Pendekatan berbasis posisi ini
   lebih tahan terhadap noise pose dibanding berbasis kecepatan. Pada uji data
   sintetis dengan noise 1–4 piksel, galat onset rata-rata ≈ 0,03–0,06 dtk. Konsekuensinya,
   onset TURUN terdeteksi sedikit setelah gerak benar-benar dimulai (≈10% durasi turun).

```python
import numpy as np
from scipy.ndimage import median_filter

def first_run(mask, start=0, min_len=6):
    """Indeks awal run True pertama (≥ min_len sampel berturut-turut) mulai dari `start`."""
    run = 0
    for i in range(start, len(mask)):
        run = run + 1 if mask[i] else 0
        if run >= min_len:
            return i - min_len + 1
    return None

def segment_phases(t, hip_y, lo=0.1, hi=0.9, smooth_sec=0.3, min_run_sec=0.2,
                   min_depth_px=15):
    """t: waktu video (dtk, PTS); hip_y: posisi vertikal pinggul (piksel, makin besar =
    makin bawah) dalam jendela satu repetisi. Posisi dinormalisasi 0 (berdiri) → 1
    (posisi terendah); fase ditentukan dari persilangan 10% / 90% kedalaman gerak.
    Mengembalikan onset aktual TURUN, TAHAN, NAIK, akhir NAIK (dtk video), dan kedalaman."""
    fps = 1 / np.median(np.diff(t))
    y = median_filter(hip_y, size=max(3, int(smooth_sec * fps) | 1), mode="nearest")
    stand, low = np.percentile(y, 5), np.percentile(y, 95)
    depth = low - stand
    nan = dict(act_turun=np.nan, act_tahan=np.nan, act_naik=np.nan, act_end=np.nan,
               depth_px=depth)
    if depth < min_depth_px:                                # tidak benar-benar turun
        return nan
    z = (y - stand) / depth
    n = max(2, int(min_run_sec * fps))
    i_turun = first_run(z > lo, 0, n)
    i_tahan = first_run(z > hi, i_turun, n) if i_turun is not None else None
    i_naik = first_run(z < hi, i_tahan, n) if i_tahan is not None else None
    i_end = first_run(z < lo, i_naik, n) if i_naik is not None else None
    pick = lambda i: t[i] if i is not None else np.nan
    return dict(act_turun=pick(i_turun), act_tahan=pick(i_tahan),
                act_naik=pick(i_naik), act_end=pick(i_end), depth_px=depth)

def extrapolated_onset(t, hip_y, smooth_sec=0.3):
    """Onset TURUN yang lebih presisi untuk LRP (10.3): garis melalui persilangan 10% dan
    50% kedalaman, diekstrapolasi ke 0%. Mengoreksi keterlambatan deteksi 10%."""
    fps = 1 / np.median(np.diff(t))
    y = median_filter(hip_y, size=max(3, int(smooth_sec * fps) | 1), mode="nearest")
    stand, low = np.percentile(y, 5), np.percentile(y, 95)
    z = (y - stand) / (low - stand)
    n = max(2, int(0.2 * fps))
    i10 = first_run(z > 0.1, 0, n)
    i50 = first_run(z > 0.5, i10, n) if i10 is not None else None
    if i50 is None:
        return np.nan
    return t[i10] - 0.1 * (t[i50] - t[i10]) / 0.4
```

3. **Verifikasi manual semua repetisi.** Jumlahnya sedikit (12 per partisipan), jadi
   verifikasi bisa dilakukan untuk semuanya: buat plot lintasan pinggul dengan garis
   onset HUD dan onset aktual, lalu cek ulang di video bila ragu. Koreksi manual ditulis
   langsung di CSV.
4. **Kepatuhan (compliance)** dicatat per repetisi:

| Kode | Kriteria (usulan, dapat disesuaikan) | Perlakuan |
|---|---|---|
| `ok` | Ketiga fase ada, urutan benar | Dianalisis |
| `late` | Onset TURUN aktual > 1,5 dtk setelah HUD | Dianalisis dengan onset aktual; kovariat latensi |
| `short_hold` | Durasi TAHAN aktual < 1 dtk | ERD fase TAHAN dieksklusi; TURUN/NAIK tetap dipakai |
| `incomplete` | Fase hilang / urutan salah | Eksklusi repetisi |
| `no_video` | Tubuh tidak terlihat / pose gagal | Eksklusi, atau fallback onset HUD (ditandai) |

Output `data/timeline/PXX_movement_phases.csv`:

| participant_id | task | rep | hud_turun | act_turun | act_tahan | act_naik | act_end | compliance | verified_by | notes |
|---|---|---|---|---|---|---|---|---|---|---|

Waktu disimpan dalam **detik video**, lalu dikonversi ke waktu EEG dengan offset dari
Tahap 2. Latensi respons (`act_turun − hud_turun`) juga menjadi variabel perilaku yang
dapat dibandingkan antara penari dan non-penari.

#### 9.1.1 Ekstraksi pose — hal khusus dari setting ruang rekaman

Setting (foto dari pengguna): partisipan berdiri menghadap monitor instruksi, webcam
di tripod di pojok ruangan, dan **dua operator duduk di samping/belakang partisipan**
(satu memegang berkas kabel elektroda). Partisipan memakai **kamen** (kain panjang).
Hasil uji MediaPipe pada foto setting:

| Uji | Hasil | Konsekuensi |
|---|---|---|
| Deteksi pada frame penuh (setting default) | Satu-satunya orang yang terdeteksi adalah **operator yang duduk**, bukan partisipan | **Wajib** memilih orang yang benar: crop ke area partisipan dan pilih pose berdasarkan posisi |
| Crop area partisipan, ambang deteksi 0,2 | Partisipan terdeteksi; visibilitas pinggul 0,99, **lutut 0,11–0,16** | Lutut tertutup kamen → jangan pakai landmark lutut/pergelangan kaki. Pakai **bahu + pinggul** (+ hidung) |

Catatan: foto diambil dari belakang partisipan, bukan dari sudut webcam. Hasil di
atas perlu diulang pada frame video asli.

```python
import av
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

# Model: https://storage.googleapis.com/mediapipe-models/pose_landmarker/
#        pose_landmarker_full/float16/latest/pose_landmarker_full.task
# mediapipe ≥ 1.0 hanya punya Tasks API (mp.solutions sudah dihapus).
# Linux tanpa GUI butuh libEGL: sudo apt install libegl1 libgles2
TRUNK = [11, 12, 23, 24]          # bahu kiri/kanan, pinggul kiri/kanan

def trunk_trajectory(path, participant_box, model="pose_landmarker_full.task",
                     max_jump=0.15):
    """Posisi vertikal batang tubuh partisipan per frame (piksel frame penuh).
    participant_box: area berdiri partisipan di frame (config.yaml), tanpa operator."""
    x0, y0, x1, y1 = participant_box
    opts = vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.VIDEO, num_poses=2,
        min_pose_detection_confidence=0.2, min_pose_presence_confidence=0.2,
        min_tracking_confidence=0.5)
    ts, ys, prev_x = [], [], None
    with vision.PoseLandmarker.create_from_options(opts) as lm, av.open(str(path)) as c:
        for fr in c.decode(video=0):
            crop = np.ascontiguousarray(fr.to_ndarray(format="rgb24")[y0:y1, x0:x1])
            h, w = crop.shape[:2]
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop),
                                      int(fr.time * 1000))
            cand = []
            for p in res.pose_landmarks:
                cx = np.mean([p[k].x for k in TRUNK]) * w
                vis = np.mean([p[k].visibility for k in TRUNK])
                if vis > 0.5:
                    cand.append((cx, np.mean([p[k].y for k in TRUNK]) * h + y0))
            if not cand:
                ts.append(fr.time); ys.append(np.nan); continue
            # pilih pose paling dekat dengan posisi partisipan sebelumnya; tolak lompatan
            # besar (mis. hanya operator yang terdeteksi di frame ini) agar tidak berpindah orang
            ref = prev_x if prev_x is not None else w / 2
            cx, y = min(cand, key=lambda c: abs(c[0] - ref))
            if abs(cx - ref) > max_jump * w:
                ts.append(fr.time); ys.append(np.nan); continue
            prev_x = cx
            ts.append(fr.time); ys.append(y)
    return np.array(ts), np.array(ys)
```

- `participant_box` ditentukan sekali per file dari frame sampel. Pilih area tempat
  partisipan berdiri, sesempit mungkin tanpa memotong tubuh saat turun, dan
  **tidak mencakup operator**.
- Frame tanpa deteksi (`NaN`) diinterpolasi hanya jika celahnya < 0,3 dtk. Celah lebih
  panjang di dalam jendela repetisi → kode `no_video`.
- QC visual: buat video pendek atau montase frame dengan titik bahu/pinggul yang
  digambar, untuk memastikan yang dilacak adalah partisipan dan bukan operator.
- Sudut kamera miring (webcam di pojok) tidak masalah untuk gerak vertikal, tetapi
  pergeseran badan ke samping pada agem kanan/kiri terlihat terdistorsi. Gunakan hanya
  sumbu vertikal untuk fase.

### 9.2 Epoching berbasis onset aktual

```python
import numpy as np
import pandas as pd
import mne

man = pd.read_csv("data/manifest.csv").set_index("participant_id")
row = man.loc[pid]
assert row.sync_validated, f"{pid}: sinkronisasi belum divalidasi"

ph = pd.read_csv(f"data/timeline/{pid}_movement_phases.csv")
ph = ph[ph.compliance != "incomplete"].dropna(subset=["act_turun"]).reset_index(drop=True)
to_eeg = lambda tv: tv + row.sync_offset_sec                 # atau model linear a·t+b

raw = mne.io.read_raw_fif(f"data/derivatives/{pid}_clean_raw.fif", preload=True)
sf = raw.info["sfreq"]
events = np.column_stack([np.round(to_eeg(ph.act_turun) * sf).astype(int),
                          np.zeros(len(ph), int), np.arange(1, len(ph) + 1)])
event_id = {f"{r.task.replace(' ', '_')}/rep{r.rep}": i + 1 for i, r in ph.iterrows()}

# Metadata: waktu fase relatif ke onset TURUN aktual → dipakai untuk jendela ERD per fase
meta = ph[["task", "rep", "compliance"]].copy()
for col in ["act_tahan", "act_naik", "act_end"]:
    meta[col.replace("act_", "rel_")] = ph[col] - ph.act_turun
meta["latency_hud"] = ph.act_turun - ph.hud_turun

epochs = mne.Epochs(raw, events, event_id, tmin=-2.5, tmax=float(meta.rel_end.max()) + 1.0,
                    baseline=None, metadata=meta, reject_by_annotation=True, preload=True)
epochs.save(f"data/derivatives/{pid}_move-epo.fif", overwrite=True)
```

Catatan:

- `tmax` mengikuti repetisi dengan durasi gerak terpanjang, ditambah margin untuk efek
  tepi wavelet. Fase tiap repetisi diambil dari `epochs.metadata`.
- Pastikan **jendela baseline** (mis. −2 s.d. −0,5 dtk dari onset TURUN **aktual**)
  jatuh di segmen `BERDIRI RILEKS` atau istirahat, **bukan** di sisa gerakan sebelumnya.
  Partisipan yang terlambat (`late`) justru punya jeda diam lebih panjang sebelum onset.
- Target 4 repetisi × {NGEED, AGEM KANAN, AGEM KIRI} = 12 per partisipan. Catat jumlah
  yang bertahan per kode kepatuhan.

---

## 10. Tahap 5 — ERD/ERS

Definisi (Pfurtscheller & Lopes da Silva, 1999):

```
%ERD/ERS = (A − R) / R × 100
A = power pada jendela aktivitas, R = power pada jendela referensi (baseline)
Negatif = ERD (desinkronisasi), Positif = ERS (sinkronisasi)
```

```python
import numpy as np
import pandas as pd
import mne

epochs = mne.read_epochs(f"data/derivatives/{pid}_move-epo.fif")
roi = ["C3", "C4", "P3", "P4", "O1", "O2", "F3", "F4"]   # F3/F4: theta frontal (Paper A)
freqs = np.arange(4, 31, 1.0)
tfr = epochs.compute_tfr(method="morlet", freqs=freqs, n_cycles=freqs / 2,
                         picks=roi, average=False, return_itc=False)
tfr.apply_baseline(baseline=(-2.0, -0.5), mode="percent")   # (A−R)/R
data = tfr.get_data() * 100                                   # epoch × kanal × freq × waktu

bands = {"theta": (4, 8), "mu": (8, 13), "beta": (13, 30)}
rows = []
for i, m in epochs.metadata.reset_index(drop=True).iterrows():
    # Jendela per fase dari onset AKTUAL (video), relatif ke onset TURUN = 0
    windows = {"TURUN": (0.0, m.rel_tahan), "TAHAN": (m.rel_tahan, m.rel_naik),
               "NAIK": (m.rel_naik, m.rel_end)}
    if m.compliance == "short_hold":
        windows.pop("TAHAN")
    for phase, (t0, t1) in windows.items():
        if not np.isfinite([t0, t1]).all() or t1 - t0 < 0.5:   # fase terlalu pendek
            continue
        tmask = (tfr.times >= t0) & (tfr.times < t1)
        for b, (lo, hi) in bands.items():
            fmask = (freqs >= lo) & (freqs < hi)
            vals = data[i][:, fmask][:, :, tmask].mean(axis=(1, 2))
            for ch, v in zip(roi, vals):
                rows.append(dict(participant_id=pid, task=m.task, rep=m.rep, phase=phase,
                                 compliance=m.compliance, latency_hud=m.latency_hud,
                                 band=b, channel=ch, erd_pct=v, phase_dur=t1 - t0))
pd.DataFrame(rows).to_csv(f"results/{pid}_erd_ers.csv", index=False)

# Visualisasi rata-rata
tfr.average().plot(picks=["C3", "C4"], title=f"{pid} %ERD/ERS")
```

- **Per fase:** ERD dihitung terpisah untuk TURUN, TAHAN, dan NAIK menggunakan batas
  fase aktual dari video. Durasi fase berbeda antar repetisi, jadi `phase_dur` ikut
  disimpan dan fase < 0,5 dtk dibuang (terlalu pendek untuk estimasi mu/beta).
  Untuk theta (4 Hz, `n_cycles` = 2), fase < 1 dtk sebaiknya tidak dipakai.
- **Lateralisasi:** lihat Indeks Lateralisasi (10.1).
- **Band individual** (opsional, direkomendasikan karena rentang usia lebar): definisikan
  mu sebagai IAF−2 s.d. IAF+2 Hz, dengan IAF diambil dari `PXX_Baseline.EDF`.
- Baseline alternatif: power rata-rata dari `PXX_Baseline.EDF`. Pilih satu definisi dan
  gunakan secara konsisten.
- Resolusi: 100 Hz dengan Morlet `n_cycles = f/2` memberi panjang wavelet ≈ 0,5 dtk untuk
  semua frekuensi. Pastikan epoch cukup panjang agar tepi (*edge effect*) tidak jatuh ke
  jendela analisis.

### 10.1 Indeks Lateralisasi (LI) — Paper A

Rumus di draft Paper A:

```
LI = (ERD_kontra − ERD_ipsi) / (ERD_kontra + ERD_ipsi)       # kontra = C3 untuk AGEM KANAN
```

⚠️ **Masalah numerik**: ERD dinyatakan dalam % yang bisa negatif (ERD) **atau** positif
(ERS). Jika satu sisi ERD dan sisi lain ERS, penyebut mendekati 0, sehingga LI meledak
atau keluar dari rentang [−1, 1]. Contoh: kontra −30%, ipsi +30% → pembagian dengan 0.
Karena itu dihitung dua versi:

| Versi | Rumus | Catatan |
|---|---|---|
| `li_erd` (sesuai draft) | seperti di atas | Hanya valid jika **kedua** sisi ERD (< 0); selain itu `NaN` dan dihitung sebagai hilang |
| `li_power` (disarankan sebagai utama) | `(P_ipsi − P_kontra) / (P_ipsi + P_kontra)` pada power absolut selama fase gerak | Selalu terdefinisi, rentang [−1, 1]; positif = dominasi kontralateral |

```python
def lateralization(erd_df, power_df=None):
    """erd_df: baris dari results/PXX_erd_ers.csv (band beta/mu, C3 & C4, per fase)."""
    agem = erd_df[erd_df.task.isin(["AGEM KANAN", "AGEM KIRI"])]
    w = agem.pivot_table(index=["participant_id", "task", "rep", "phase", "band"],
                         columns="channel", values="erd_pct").reset_index()
    kanan = w.task == "AGEM KANAN"
    w["contra"] = np.where(kanan, w.C3, w.C4)            # 🔎 konfirmasi pemetaan sisi (15)
    w["ipsi"] = np.where(kanan, w.C4, w.C3)
    both_erd = (w.contra < 0) & (w.ipsi < 0)
    w["li_erd"] = np.where(both_erd, (w.contra - w.ipsi) / (w.contra + w.ipsi), np.nan)
    return w
```

`li_power` dihitung dengan cara yang sama dari power absolut TFR (sebelum
`apply_baseline`). Interpretasi LI tetap dibatasi oleh **referensi telinga ipsilateral**:
selisih C3/C4 ikut memuat selisih A1/A2, kecuali referensi *linked-ear* berhasil
direkonstruksi (8.1.1).

### 10.2 Topografi ERD beta — Paper A

Peta skalp 16 kanal untuk AGEM KANAN dan AGEM KIRI secara terpisah. Karena tidak ada
elektroda garis tengah, gunakan interpolasi **nearest-neighbour** (setiap kanal
digambar sebagai wilayahnya sendiri, tanpa menghaluskan nilai melewati garis tengah):

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(8, 4))
for ax, task in zip(axes, ["AGEM_KANAN", "AGEM_KIRI"]):
    tfr_task = tfr_all[task].average()                 # TFR semua 16 kanal, mode percent
    beta = tfr_task.copy().crop(tmin=0, tmax=None, fmin=13, fmax=30).data.mean(axis=(1, 2)) * 100
    mne.viz.plot_topomap(beta, tfr_task.info, axes=ax, image_interp="nearest",
                         contours=0, cmap="RdBu_r", vlim=(-40, 40), show=False)
    ax.set_title(f"{task} — ERD beta (%)")
```

Untuk topografi, hitung TFR pada **semua** 16 kanal (bukan hanya `roi`). Rata-rata grup
dihitung dari rata-rata per partisipan (bukan dari gabungan semua epoch).

### 10.3 Lateralized Readiness Potential (LRP) — Paper A

Domain waktu, memakai data cabang 8.3 (bukan TFR). Metode *double subtraction*
(Coles, 1989):

```
LRP = ½ · [ (C3 − C4)_AGEM KANAN + (C4 − C3)_AGEM KIRI ]
Nilai negatif = aktivasi persiapan di hemisfer kontralateral
Amplitudo = rata-rata LRP pada jendela −200 s.d. 0 ms sebelum onset gerak
```

```python
raw_lrp = mne.io.read_raw_fif(f"data/derivatives/{pid}_lrp_raw.fif", preload=True)
ep = mne.Epochs(raw_lrp, events, event_id, tmin=-1.5, tmax=0.5,
                baseline=(-1.5, -1.0), metadata=meta, preload=True)   # events dari 9.2
ep = ep[ep.metadata.compliance.isin(["ok", "late", "short_hold"]).to_numpy()]

def diff(evk, a, b):
    return (evk.copy().pick([a]).data - evk.copy().pick([b]).data)[0]

ev_r, ev_l = ep["AGEM_KANAN"].average(), ep["AGEM_KIRI"].average()
lrp = 0.5 * (diff(ev_r, "C3", "C4") + diff(ev_l, "C4", "C3"))       # Volt
win = (ev_r.times >= -0.2) & (ev_r.times <= 0.0)
lrp_amp_uV = lrp[win].mean() * 1e6
```

⚠️ **Hal-hal yang membatasi LRP pada data ini (wajib dibaca sebelum dijadikan temuan):**

0. **High-pass perangkat ≈ 0,5–1 Hz (temuan P02) — kendala paling berat.** LRP adalah
   pergeseran lambat yang naik selama ratusan milidetik sebelum gerak. Filter high-pass
   pada 0,5–1 Hz melemahkan dan mendistorsi bentuknya (menjadi bifasik), dan efek ini
   tidak bisa dibalik di software. **Rekomendasi:** LRP tidak dijadikan hasil
   konfirmatori di Paper A. Pilihannya: (a) dihapus dari Paper A, atau (b) dilaporkan
   sebagai analisis eksploratif dengan pernyataan eksplisit tentang filter perangkat.
   Lateralisasi motorik tetap bisa diwakili oleh **LI dari ERD mu/beta** (10.1), yang
   tidak terpengaruh high-pass.

1. **Jumlah trial sangat sedikit.** Hanya 4 repetisi per sisi, sedangkan LRP biasanya
   butuh puluhan trial per sisi agar sinyalnya terlihat di atas noise. Dengan 4 trial,
   amplitudo per partisipan sangat berisik. Perlakukan sebagai **eksploratif**, laporkan
   jumlah trial per partisipan, dan pertimbangkan analisis tingkat grup (*grand average*,
   *jackknife*) daripada amplitudo per individu.
2. **Presisi onset.** Jendela −200–0 ms menuntut onset gerak yang presisi jauh di bawah
   200 ms. Onset dari persilangan 10% (9.1) terlambat ≈ 10% durasi turun (≈ 0,1–0,2 dtk),
   sehingga jendela bisa berisi awal gerakan dan artefaknya. **Gunakan onset
   ekstrapolasi** (garis lurus melalui persilangan 10% dan 50%, diekstrapolasi ke 0%)
   untuk LRP (`extrapolated_onset` di 9.1; pada uji sintetis galatnya ≈ −0,01 ± 0,04 dtk),
   dan tambahkan ketidakpastian sinkronisasi (±0,1 dtk) ke laporan.
3. **Gerakan seluruh tubuh.** Ngeed/agem bukan gerakan tangan terisolasi. Lateralisasi
   motoriknya kurang tegas dibanding tugas menekan tombol, dan artefak gerak mulai
   muncul tepat di sekitar onset. NGEED (bilateral) tidak dipakai untuk LRP.
4. **Referensi ipsilateral.** `C3−A1` dikurangi `C4−A2` = `(C3−C4) − (A1−A2)`, jadi
   aktivitas lambat yang berbeda di kedua telinga masuk langsung ke LRP. Hal ini bisa
   diatasi jika referensi *linked-ear* berhasil direkonstruksi (8.1.1).

---

## 11. Tahap 5b — Fitur Romberg

Segmen: `BERDIRI FOKUS MATA TERBUKA` (EO, 30 dtk) dan `BERDIRI MATA TERTUTUP` (EC, 30 dtk).
Bukan analisis ERD/ERS, melainkan **power spektral kondisi tunak**.

```python
import numpy as np
import pandas as pd
import mne

def seg_psd(raw, label, pad=2.0):
    ann = [a for a in raw.annotations if a["description"].startswith(label)][0]
    seg = raw.copy().crop(ann["onset"] + pad, ann["onset"] + ann["duration"] - pad)  # buang transisi
    ep = mne.make_fixed_length_epochs(seg, duration=2.0, overlap=1.0, preload=True)
    ep.drop_bad(reject=dict(eeg=150e-6))
    sp = ep.compute_psd(method="welch", fmin=1, fmax=40, n_fft=200)  # resolusi 0,5 Hz
    psd, f = sp.get_data(return_freqs=True)
    return psd.mean(axis=0), f, sp.ch_names, len(ep)

def bp(psd, f, chs, picks, lo, hi, relative=True):
    idx = [chs.index(c) for c in picks]
    m = (f >= lo) & (f < hi)
    band = np.trapezoid(psd[idx][:, m], f[m], axis=-1)
    if relative:
        band = band / np.trapezoid(psd[idx][:, (f >= 1) & (f < 40)], f[(f >= 1) & (f < 40)], axis=-1)
    return band.mean()

eo, f, chs, n_eo = seg_psd(raw, "BERDIRI_FOKUS_MATA_TERBUKA")
ec, _, _, n_ec   = seg_psd(raw, "BERDIRI_MATA_TERTUTUP")

def iaf(psd, picks, min_peak_db=3.0, k_noise=3.0):
    """Center of gravity alpha, HANYA jika ada puncak alpha nyata di atas tren 1/f.
    Tren aperiodik = garis lurus log-log pada 2–30 Hz (tanpa 7–14 Hz). Residual
    dihaluskan 3 bin; puncak harus ≥ min_peak_db DAN ≥ k_noise × SD residual di luar
    alpha, serta tidak di tepi jendela. P02 (fluktuasi ±1,5–3 dB tanpa puncak) → NaN."""
    spec = psd[[chs.index(c) for c in picks]].mean(axis=0)
    fit = ((f >= 2) & (f < 7)) | ((f > 14) & (f <= 30))
    coef = np.polyfit(np.log10(f[fit]), np.log10(spec[fit]), 1)
    resid_db = 10 * (np.log10(spec) - np.polyval(coef, np.log10(f)))
    smooth = np.convolve(resid_db, np.ones(3) / 3, mode="same")
    noise = np.std(smooth[fit])
    m = (f >= 7) & (f <= 14)
    i = np.argmax(smooth[m])
    if smooth[m][i] < max(min_peak_db, k_noise * noise) or i in (0, m.sum() - 1):
        return np.nan
    pk = f[m][i]
    w = (f >= pk - 2) & (f <= pk + 2)
    excess = np.clip(10 ** (resid_db[w] / 10) - 1, 0, None)        # hanya bagian di atas tren
    return (f[w] * excess).sum() / excess.sum()

feat = dict(
    participant_id=pid,
    # Tier 1
    alpha_occ_EC=bp(ec, f, chs, ["O1", "O2"], 8, 13),
    alpha_reactivity_EC_EO=bp(ec, f, chs, ["O1", "O2"], 8, 13, False)
                          / bp(eo, f, chs, ["O1", "O2"], 8, 13, False),
    mu_sm_EC=bp(ec, f, chs, ["C3", "C4"], 8, 13),
    mu_sm_EO=bp(eo, f, chs, ["C3", "C4"], 8, 13),
    theta_front_EC=bp(ec, f, chs, ["F3", "F4"], 4, 8),
    # Tier 2
    iaf_occ_EC=iaf(ec, ["O1", "O2"]), iaf_par_EC=iaf(ec, ["P3", "P4"]),
    beta_sm_EO=bp(eo, f, chs, ["C3", "C4"], 13, 30),
    beta_sm_EC=bp(ec, f, chs, ["C3", "C4"], 13, 30),
    alpha_par_EC=bp(ec, f, chs, ["P3", "P4"], 8, 13),
    # Paper A: rasio theta/alpha (default: F3/F4 theta ÷ O1/O2 alpha, EC; 🔎 konfirmasi di 15)
    theta_alpha_ratio_EC=bp(ec, f, chs, ["F3", "F4"], 4, 8, False)
                        / bp(ec, f, chs, ["O1", "O2"], 8, 13, False),
    # QC
    n_epochs_EO=n_eo, n_epochs_EC=n_ec,
    is_simulated=IS_SIMULATED,                    # lihat 12.6
)
pd.DataFrame([feat]).to_csv(f"results/{pid}_romberg_features.csv", index=False)
```

- Satu baris per partisipan, dengan `participant_id` sebagai kunci untuk digabung dengan
  data Standing Stork Test (waktu per partisipan).
- Untuk non-penari yang punya pre/post, tambahkan kolom `timepoint` agar penggabungan
  tidak tertukar.
- Tier 3 (entropi, koherensi) ditunda sampai Tier 1–2 selesai.
- **Cakupan segmen (QC wajib):** setelah sinkronisasi, pastikan onset + durasi segmen
  EO dan EC berada di dalam rentang EDF. Pada P02, EDF 17–34 dtk lebih pendek dari
  video dan Romberg adalah segmen terakhir, sehingga EC mungkin terpotong. Segmen yang
  tidak lengkap (< 20 dtk bersih) → fitur `NaN` dengan catatan, **jangan** memakai
  sisa segmen tanpa ditandai.
- **Validasi `iaf`:** pada data P02 hasilnya `NaN` di semua segmen (tanpa puncak). Pada
  spektrum sintetis dengan puncak +5 dB, deteksi 100% untuk 9 dan 10,5 Hz dengan galat
  < 0,05 Hz, tetapi hanya 75% untuk 7,5 Hz karena dekat tepi jendela 7–14 Hz. Tidak ada
  deteksi palsu pada 50 spektrum tanpa puncak. Untuk partisipan lansia (alpha melambat),
  pertimbangkan jendela 6–14 Hz.
- **Tanpa puncak alpha:** partisipan seperti P02 tidak menunjukkan puncak alpha. Power
  band 8–13 Hz tetap bisa dihitung, tetapi pertimbangkan *specparam*/FOOOF untuk
  memisahkan komponen aperiodik (1/f), dan laporkan jumlah partisipan tanpa puncak
  alpha per grup.

---

## 12. Tahap 6 — Statistik

### 12.1 ERD/ERS gerakan — linear mixed model

```python
import pandas as pd
import statsmodels.formula.api as smf

df = pd.concat(pd.read_csv(p) for p in Path("results").glob("P*_erd_ers.csv"))
df = df.merge(pd.read_csv("data/manifest.csv")[["participant_id", "group", "timepoint", "age"]])
sub = df[(df.band == "mu") & (df.channel == "C3")]
m = smf.mixedlm("erd_pct ~ group * task * phase + age", sub,
                groups=sub["participant_id"]).fit(reml=True)
print(m.summary())
# Intervensi non-penari: "erd_pct ~ timepoint * movement + age" pada subset non-penari,
# atau group × timepoint bila desainnya memungkinkan.
```

### 12.2 Paper D — Kontrol postural: Romberg EEG × Standing Stork Test

Desain **cross-sectional**, seluruh 38 partisipan pada satu timepoint (non-penari
peserta pelatihan: data **pre**, sama seperti Paper A). Tidak memakai RCI/NDV/Gap
Closure dan tidak bergantung pada Paper A, jadi bisa dikerjakan paralel.

**Analisis utama:** Welch's t-test penari vs non-penari (fungsi `welch` di 12.3) untuk
fitur Tier 1 dan durasi Stork Test, dengan BH dalam keluarga Paper D:

```python
paper_d = ["alpha_occ_EC", "alpha_reactivity_EC_EO", "mu_sm_EC", "mu_sm_EO",
           "theta_front_EC", "stork_time_sec"]
res_d = pd.DataFrame([welch(pp, c) for c in paper_d])
res_d["p_fdr"] = multipletests(res_d.p, method="fdr_bh")[1]
```

**Analisis sekunder:** korelasi parsial fitur Tier 1 × durasi Stork Test pada **sampel
gabungan** (bukan per grup), dikontrol usia:

```python
import pingouin as pg
from statsmodels.stats.multitest import multipletests

rom = pd.concat(pd.read_csv(p) for p in Path("results").glob("P*_romberg_features.csv"))
d = rom.merge(stork, on="participant_id").merge(demo[["participant_id", "age"]])

tier1 = ["alpha_occ_EC", "alpha_reactivity_EC_EO", "mu_sm_EC", "mu_sm_EO", "theta_front_EC"]
res = pd.concat([
    pg.partial_corr(d, x=feat, y="stork_time_sec", covar="age", method="spearman")
      .assign(feature=feat)
    for feat in tier1
])
res["p_fdr"] = multipletests(res["p-val"], method="fdr_bh")[1]
```

Tier 1 dianalisis sebagai hipotesis utama dengan koreksi FDR. Tier 2/3 dilaporkan
terpisah sebagai eksploratif.

Catatan Paper D:
- Korelasi pada sampel gabungan bisa didorong oleh **perbedaan grup** (penari punya
  Stork Test lebih lama **dan** EEG berbeda → korelasi tanpa hubungan dalam grup).
  Sebagai uji sensitivitas, tambahkan `group` sebagai kovariat kedua
  (`covar=["age", "group"]`) dan laporkan keduanya.
- Pastikan `n` per fitur dilaporkan, karena segmen Romberg yang terpotong
  (lihat 11) menghasilkan `NaN`.

### 12.3 Paper A — uji grup Welch untuk 5 indeks konvensional

Satu nilai per partisipan per indeks (rata-rata repetisi). Definisi default di bawah
ditandai 🔎 dan perlu dikonfirmasi (Bagian 15).

> **Strategi 4 naskah (CLAUDE.md):** jika Paper D dibuat, indeks Romberg (Alpha
> Oksipital Romberg-EC, rasio Theta/Alpha Romberg) **tidak ditonjolkan** di Paper A/B.
> Indeks tersebut hanya dirujuk singkat ke Paper D, untuk menghindari *salami slicing*.
> Keluarga BH Paper A lalu hanya berisi indeks gerakan + LI (+ LRP bila dipertahankan)
> + interaksi usia.

| Indeks | Definisi default | Sumber |
|---|---|---|
| ERD Beta Agem | %ERD beta di C **kontralateral**, fase TURUN 🔎, rata-rata AGEM KANAN + KIRI | 10 |
| Theta Frontal Agem | %ERS theta F3/F4, fase TURUN+TAHAN 🔎, AGEM KANAN + KIRI | 10 |
| Alpha Oksipital Romberg-EC | `alpha_occ_EC` (relatif) → **dipindah ke Paper D** | 11 |
| Rasio Theta/Alpha Romberg | `theta_alpha_ratio_EC` 🔎 → **dipindah ke Paper D** | 11 |
| Durasi Stork Test | data eksternal | — |

```python
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

def welch(d, col):
    a = d.loc[d.group == "penari", col].dropna()
    b = d.loc[d.group == "non-penari", col].dropna()
    t, p = stats.ttest_ind(a, b, equal_var=False)
    sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    J = 1 - 3 / (4 * (len(a) + len(b)) - 9)                  # koreksi Hedges
    return dict(index=col, n_penari=len(a), n_nonpenari=len(b),
                mean_diff=a.mean() - b.mean(), t=t, p=p, hedges_g=J * (a.mean() - b.mean()) / sp)

indices = ["erd_beta_agem", "theta_front_agem", "alpha_occ_EC", "theta_alpha_ratio_EC",
           "stork_time_sec"]
res = pd.DataFrame([welch(pp, c) for c in indices])     # pp: tabel 1 baris/partisipan (pre saja)
```

- **Koreksi multiple comparison** (belum ada di draft Paper A): 5 indeks + LI + LRP +
  interaksi usia × kelompok diuji sebagai satu **keluarga**. Terapkan Benjamini-Hochberg
  pada seluruh p-value keluarga itu, bukan per tabel.
- Untuk non-penari, uji grup hanya memakai data **pre** (timepoint pre), agar tidak ada
  partisipan yang terhitung dua kali.

**Regresi usia × kelompok + uji sensitivitas (wajib sebelum dilaporkan sebagai temuan utama):**

```python
import statsmodels.formula.api as smf

def age_models(d, y):
    full = smf.ols(f"{y} ~ group * age", d).fit(cov_type="HC3")        # SE robust
    infl = full.get_influence().cooks_distance[0]
    no_infl = smf.ols(f"{y} ~ group * age", d[infl < 4 / len(d)]).fit(cov_type="HC3")
    q = d.age.quantile([0.05, 0.95])
    trimmed = smf.ols(f"{y} ~ group * age", d[d.age.between(*q)]).fit(cov_type="HC3")
    spline = smf.ols(f"{y} ~ group * cr(age, df=3)", d).fit(cov_type="HC3")  # non-linear
    return {k: m.params.get("group[T.penari]:age", np.nan)
            for k, m in dict(full=full, no_influential=no_infl,
                             trimmed_5_95=trimmed).items()}, spline
```

Laporkan koefisien interaksi dari ketiga model berdampingan. Jika arah atau
signifikansinya berubah setelah partisipan dengan usia ekstrem dikeluarkan, temuan
tersebut **tidak** dilaporkan sebagai temuan utama. Model spline menguji apakah hubungan
dengan usia memang linear.

### 12.4 Paper B — Reliable Change Index (RCI)

```
RCI    = (Post − Pre) / S_diff
S_diff = SD_pre · √(2 · (1 − r_xx))          |RCI| ≥ 1,96 → perubahan individual nyata
```

⚠️ `r_xx` **harus dihitung dari data riil**. Nilai 0,70–0,85 di draft hanyalah placeholder.
Tidak ada sesi test-retest tanpa intervensi, jadi yang tersedia adalah **reliabilitas
internal dalam sesi**:

| Indeks | Cara menghitung `r_xx` |
|---|---|
| ERD/ERS (4 repetisi per gerakan) | Split-half ganjil–genap (rep 1+3 vs 2+4) antar partisipan, dikoreksi Spearman-Brown `2r/(1+r)` |
| Fitur Romberg (30 dtk) | Paruh pertama vs paruh kedua segmen (15 dtk vs 15 dtk), Spearman-Brown |

```python
def split_half_r(df, value, unit="participant_id", split="rep"):
    odd = df[df[split] % 2 == 1].groupby(unit)[value].mean()
    even = df[df[split] % 2 == 0].groupby(unit)[value].mean()
    r = odd.corr(even)
    return 2 * r / (1 + r)                     # Spearman-Brown

def rci(pre, post, sd_pre, rxx):
    s_diff = sd_pre * np.sqrt(2 * (1 - rxx))
    return (post - pre) / s_diff
```

Catatan: reliabilitas dalam sesi **lebih tinggi** daripada test-retest antar-hari, sehingga
`S_diff` terlalu kecil dan RCI menjadi terlalu liberal. Tulis ini sebagai limitasi.
Hitung `r_xx` dari seluruh sampel pada pengukuran pre (penari + non-penari) agar
estimasinya lebih stabil, dan laporkan interval kepercayaannya (*bootstrap*).

### 12.5 Paper B — NDV dan Gap Closure

**Nonequivalent Dependent Variable (NDV):** *Peak Alpha Frequency* (PAF) saat istirahat
mata tertutup, diuji pre vs post **terpisah** dari 5 indeks target.

```python
paf = pp_nonpenari.pivot(index="participant_id", columns="timepoint", values="paf_rest_EC")
t, p = stats.ttest_rel(paf["post"], paf["pre"])
w = stats.wilcoxon(paf["post"], paf["pre"])     # pembanding non-parametrik (n kecil)
```

🔎 Sumber PAF: `PXX_Baseline.EDF` P02 **kemungkinan mata terbuka** (~6 kedipan/menit)
dan tidak punya puncak alpha. Alternatifnya segmen Romberg EC (berdiri), tetapi segmen
itu mungkin terpotong (11). Jika PAF `NaN` untuk banyak partisipan, NDV ini tidak dapat
dipakai. Perlu dikonfirmasi apakah protokol Baseline memang mata terbuka.

**Gap Closure (%)** = (Post − Pre) / (Benchmark penari − Pre) × 100

- **Ketergantungan urutan:** benchmark diambil dari hasil **final** Paper A. Gap Closure
  tidak dihitung sebelum Paper A dikunci. Simpan benchmark di file terpisah
  (`results/paperA_benchmark.csv`) beserta versi atau tanggalnya.
- ⚠️ **Penyebut mendekati nol:** partisipan yang nilai pre-nya sudah dekat rata-rata
  penari akan menghasilkan Gap Closure ekstrem (±ribuan %). Tetapkan aturan sebelum
  melihat hasil, misalnya `NaN` jika |Benchmark − Pre| < 0,25 SD penari, dan laporkan
  jumlah partisipan yang terkena aturan ini.
- **Benchmark disesuaikan usia** (disarankan): dengan rentang usia remaja–102 tahun,
  gunakan nilai prediksi penari **pada usia partisipan tersebut** (dari regresi usia
  kelompok penari di Paper A), bukan rata-rata kasar.

```python
def gap_closure(pre, post, benchmark, sd_dancer, min_gap_sd=0.25):
    gap = benchmark - pre
    return np.where(np.abs(gap) < min_gap_sd * sd_dancer, np.nan, (post - pre) / gap * 100)
```

### 12.6 Penanda data simulasi

Selama data riil belum lengkap, setiap output CSV dan gambar diberi penanda:

- Kolom `is_simulated` (True/False) di semua file `results/*.csv`, diambil dari satu
  sumber: `config.yaml` → `is_simulated`.
- Judul gambar diberi awalan `[SIMULATED RESULTS]` jika `is_simulated = True`.
- Skrip statistik **menolak** mencampur baris simulasi dan riil dalam satu analisis:
  `assert df.is_simulated.nunique() == 1`.

---

## 13. Kontrol Kualitas

Log per partisipan (`results/qc_log.csv`):

| participant_id | sync_offset_sec | sync_xcorr_r | sync_drift_sec | sync_residual_sec | ocr_manual_check_ok | add_lead_verdict | bad_channels | n_ica_eye_removed | n_reps_ok/late/short_hold/incomplete (/12) | n_move_epochs_kept | n_romberg_epochs_EO/EC | include | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

**Checklist per partisipan**

- [ ] File lengkap (manifest tidak kosong)
- [ ] Kotak HUD dicek pada frame sampel
- [ ] Kotak webcam & `participant_box` dicek; pose melacak **partisipan, bukan operator** (cek montase frame)
- [ ] Timeline OCR divalidasi manual; 4 repetisi per gerakan (NGEED, AGEM KANAN, AGEM KIRI)
- [ ] Offset xcorr: puncak tunggal, |offset| ≤ 2 dtk, drift paruh-sesi < 0,2 dtk
- [ ] Offset divalidasi dengan transisi alpha Romberg (residual < 0,5 dtk)
- [ ] Fase aktual TURUN/TAHAN/NAIK diverifikasi manual untuk **semua** 12 repetisi; kode kepatuhan terisi
- [ ] Sampling rate = 100 Hz; filter 1–35 Hz; tanpa notch; `Add_lead` datar (dicek)
- [ ] Kanal buruk dicatat & diinterpolasi (C3/C4 buruk → pertimbangkan eksklusi)
- [ ] Hanya komponen ICA mata yang dibuang, diverifikasi visual
- [ ] Jendela baseline tidak tumpang tindih dengan gerakan sebelumnya
- [ ] Segmen Romberg EO/EC **lengkap di dalam EDF** setelah sinkronisasi (P02: EC mungkin terpotong)
- [ ] PSD Romberg EC: ada puncak alpha? Jika tidak, catat `no_alpha_peak` (P02: tidak ada)
- [ ] Cabang LRP: filter 0,05–8 Hz, ICA yang sama diterapkan, onset ekstrapolasi dipakai, jumlah trial per sisi dicatat
- [ ] `is_simulated` benar di semua output
- [ ] Laporan QC HTML tersimpan (`mne.Report`) di `reports/`

---

## 14. Limitasi untuk Naskah

- **Tidak ada elektroda midline.** ERD sensorimotor diukur pada proksi C3/C4, dan theta
  frontal pada F3/F4, bukan Fz.
- **Sampling rate 100 Hz.** Analisis dibatasi ≤ 40 Hz, gamma tidak dapat dianalisis, dan
  notch 50 Hz tidak diterapkan.
- **Referensi telinga ipsilateral.** Membatasi interpretasi asimetri hemisfer. Tidak
  dapat dikoreksi karena `Add_lead` tidak berisi sinyal.
- **Filter perangkat KT88** (≈ 0,5–1 Hz s.d. ≈ 35 Hz) diterapkan saat perekaman.
  Laporkan di Metode. Hal ini membatasi analisis potensial lambat (LRP) dan beta atas.
- **Sinkronisasi EEG–video**: start manual oleh dua operator (aba-aba hitungan ke-3),
  lalu disempurnakan pasca-perekaman dengan korelasi silang sinyal gerak dan divalidasi
  dengan transisi alpha Romberg. Laporkan offset, r, drift, dan residual (rata-rata ± SD).
- **Onset gerakan dari video** (pose estimation + verifikasi manual), bukan dari sensor
  gerak/EMG. Resolusi temporal dibatasi frame rate (~30 fps) dan presisi sinkronisasi.
- **Operator dalam ruang dan penanganan kabel**: operator duduk dekat partisipan dan
  memegang kabel elektroda, sehingga ada potensi artefak kabel yang tidak terkait gerak
  partisipan. Kamen menutupi lutut, jadi fase gerak diukur dari batang tubuh
  (bahu/pinggul), bukan sudut lutut.
- **Kepatuhan instruksi bervariasi**: sebagian partisipan tidak mengikuti
  TURUN→TAHAN→NAIK dengan tepat. Laporkan jumlah repetisi per kode kepatuhan per grup,
  karena perbedaan kepatuhan antara penari dan non-penari sendiri adalah temuan.
- **Rentang usia sangat lebar.** Usia dikontrol sebagai kovariat, IAF individual
  dipertimbangkan, dan regresi usia × kelompok disertai uji sensitivitas (12.3).
- **LRP eksploratif**: hanya 4 trial per sisi, gerakan seluruh tubuh, dan referensi
  ipsilateral (10.3).
- **RCI** memakai reliabilitas dalam sesi (split-half), bukan test-retest, sehingga
  cenderung liberal (12.4).
- **Paper B tanpa kelompok kontrol eksternal**: NDV (PAF) hanya menyingkirkan sebagian
  penjelasan alternatif.

---

## 15. Pertanyaan Terbuka yang Memblokir

Dari `CLAUDE.md` (jawaban pengguna 2026-09-23):

| # | Pertanyaan | Status / jawaban | Tahap |
|---|---|---|---|
| 1 | Mekanisme start EEG vs video | ✅ Dua device, start manual pada aba-aba hitungan ke-3 → prior offset ≈ 0, disempurnakan dengan xcorr (7.2) | 2 |
| 2 | Isi `Add_lead1` / `Add_lead2` | ✅ Diverifikasi pada P02: **datar**, tidak berisi sinyal → diabaikan; linked-ear tidak mungkin | 3 |
| 3 | Label HUD ngeed | ✅ `NGEED`, `AGEM KANAN`, `AGEM KIRI` | 1 |
| 4 | Urutan sub-fase | ✅ `TURUN → TAHAN → NAIK` untuk semua gerakan; kepatuhan dikonfirmasi dari video (9.1) | 4, 5 |
| 5 | Struktur folder untuk ke-38 partisipan | ✅ Satu folder per partisipan: video + EDF Baseline + EDF Trial. ❓ Sisa: bagaimana folder **pre vs post** non-penari dibedakan (nama folder/kode berbeda?) | 0 |
| 6 | Konfirmasi Python + MNE-Python | ❓ Terbuka (diasumsikan ya) | Semua |
| 7 | Posisi region webcam dan area partisipan di frame video | ⚠️ Setting ruang sudah diketahui (foto). Koordinat tetap perlu **satu screenshot frame video asli** | 2, 4 |
| 8 | Pemetaan sisi untuk LI/LRP: AGEM KANAN → hemisfer kontralateral = **C3**? (agem melibatkan lengan dan tungkai; "tangan kanan" di draft = AGEM KANAN?) | 🔎 Baru | 5 |
| 9 | Fase mana yang dipakai untuk "ERD Beta Agem" dan "Theta Frontal Agem" (TURUN, TAHAN, atau gabungan)? | 🔎 Baru (default: TURUN; TURUN+TAHAN) | 6 |
| 10 | Definisi "Rasio Theta/Alpha Romberg": kondisi (EC/EO) dan kanal (theta F3/F4 ÷ alpha O1/O2, atau kanal yang sama)? | 🔎 Baru (default: EC, F3/F4 ÷ O1/O2) | 5b, 6 |
| 11 | `PXX_Baseline.EDF`: istirahat mata tertutup atau terbuka? Duduk atau berdiri? (menentukan sumber PAF untuk NDV) | 🔎 Data P02 menunjukkan **mata terbuka** (~6 kedipan/menit). Mohon konfirmasi protokol | 6 |
| 12 | LRP: dipertahankan sebagai eksploratif atau dihapus dari Paper A? (high-pass perangkat ≈ 0,5–1 Hz) | 🔎 Baru | 5, 6 |
| 13 | Apakah perangkat KT88 bisa diatur ke *time constant* lebih panjang (HP ≤ 0,1 Hz) dan low-pass lebih tinggi untuk perekaman berikutnya (mis. post-test Paper B)? | 🔎 Baru | Perekaman |

---

## 16. Referensi

- Pfurtscheller, G., & Lopes da Silva, F. H. (1999). Event-related EEG/MEG synchronization
  and desynchronization: basic principles. *Clinical Neurophysiology*, 110(11), 1842–1857.
- Gramfort, A., et al. (2013). MEG and EEG data analysis with MNE-Python.
  *Frontiers in Neuroscience*, 7, 267.
- Klimesch, W. (1999). EEG alpha and theta oscillations reflect cognitive and memory
  performance. *Brain Research Reviews*, 29(2–3), 169–195.
- Pion-Tonachini, L., et al. (2019). ICLabel. *NeuroImage*, 198, 181–197.
- Pernet, C., et al. (2020). Issues and recommendations from the OHBM COBIDAS MEEG
  committee. *Nature Neuroscience*, 23, 1473–1483.
- Coles, M. G. H. (1989). Modern mind-brain reading: psychophysiology, physiology, and
  cognition. *Psychophysiology*, 26(3), 251–269.
- Jacobson, N. S., & Truax, P. (1991). Clinical significance: a statistical approach to
  defining meaningful change in psychotherapy research. *Journal of Consulting and
  Clinical Psychology*, 59(1), 12–19.
- Miller, J., Patterson, T., & Ulrich, R. (1998). Jackknife-based method for measuring
  LRP onset latency differences. *Psychophysiology*, 35(1), 99–115.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate.
  *Journal of the Royal Statistical Society B*, 57(1), 289–300.
