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
| Sampling rate **100 Hz** (Nyquist = 50 Hz) | **Notch 50 Hz tidak bisa diterapkan.** MNE akan error karena 50 Hz tepat di Nyquist. Interferensi listrik dihilangkan oleh **low-pass 40 Hz** saja. Jangan *resample*. |
| Analisis sampai beta (≤ 30 Hz) | Masih aman di bawah Nyquist; gamma tidak dapat dianalisis. |
| 16 kanal KT88, **tanpa midline** (Fz/Cz/Pz) | Gunakan proksi: C3/C4 (sensorimotor), F3/F4 atau F7/F8 (frontal), P3/P4, O1/O2. |
| Referensi **ipsilateral**: kiri → A1, kanan → A2 | **Bukan linked-ear dan bukan referensi bersama.** Perbandingan kiri–kanan (C3 vs C4) ikut dipengaruhi beda aktivitas A1 vs A2. *Average reference* tidak sepenuhnya valid di sini (lihat Tahap 3). |
| Nama kanal `Fp1-A1`, `T3-A1`, … | Harus di-*rename* ke `Fp1`, `T3`, … sebelum *montage*. T3/T4/T5/T6 dikenali di montage 10-20 MNE. |
| `Add_lead1`, `Add_lead2` "sepertinya lead referensi" (belum pasti) | Diset tipe `misc` sampai diverifikasi empiris (Tahap 3). Jika terbukti A1/A2, referensi linked-ear bisa direkonstruksi. |
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
            mediapipe            # pose estimation untuk fase gerak aktual (Tahap 4)
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
Tahap 3  EDF ─► rename/montage ─► filter 1–40 Hz ─► kanal buruk ─► ICA (mata saja)
         (+ verifikasi isi Add_lead)
   │
Tahap 4  Pose video ─► fase aktual TURUN/TAHAN/NAIK + kepatuhan (verifikasi manual)
         ─► offset ─► Epochs per repetisi (onset aktual)
   │
   ├─► Tahap 5   ERD/ERS mu & beta per fase (C3/C4, P3/P4, O1/O2) ─► erd_ers_long.csv
   └─► Tahap 5b  Romberg EO/EC ─► romberg_features.csv (join dgn Stork Test)
   │
Tahap 6  Mixed model (ERD/ERS) & korelasi parsial (Romberg × Stork)
```

Semua parameter disimpan di satu file `config.yaml`, jangan ditulis langsung (*hardcode*) di skrip:

```yaml
sfreq_expected: 100
filter: {l_freq: 1.0, h_freq: 40.0}
hud_box: {x0: 960, y0: 250, x1: 1280, y1: 480}   # verifikasi per file
webcam_box: {x0: null, y0: null, x1: null, y1: null}   # isi setelah cek frame sampel
ocr_sample_sec: 0.2
sync: {prior_offset_sec: 0.0, max_lag_sec: 5.0, max_drift_sec: 0.2, max_residual_sec: 0.5}
phases: {late_sec: 1.5, short_hold_sec: 1.0, min_phase_sec: 0.5}
bands: {theta: [4, 8], mu: [8, 13], beta: [13, 30]}
roi: [C3, C4, P3, P4, O1, O2]
erd:
  tmin: -2.5          # detik relatif onset TURUN aktual; tmax = durasi gerak terpanjang + 1 dtk
  baseline: [-2.0, -0.5]
```

---

## 5. Tahap 0 — Manifest

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
    """Energi gerak (selisih antar-frame) di region webcam, di-resample ke grid fs."""
    x0, y0, x1, y1 = box                           # webcam_box di config.yaml
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
    """Envelope artefak gerak/otot di kanal frontal-temporal."""
    picks = ["Fp1", "Fp2", "F7", "F8", "T3", "T4"]
    env = raw.copy().pick(picks).filter(20, 45).apply_hilbert(envelope=True) \
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
tv, v = video_motion(path_video, webcam_box)
te, e = eeg_motion(raw)
offset, peak, (lags, cc) = xcorr_offset(v, e)
print(f"sync_offset_sec = {offset:+.2f} dtk (r = {peak:.2f})")
```

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

# 2) Filter — TANPA notch (50 Hz = Nyquist); low-pass 40 Hz sudah menekan 50 Hz
raw.filter(l_freq=1.0, h_freq=40.0)

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

ica = ICA(n_components=len(raw.info["ch_names"]) - len(raw.info["bads"]) - 1,
          method="picard", fit_params=dict(extended=True, ortho=False),
          random_state=97, max_iter="auto")
ica.fit(raw.copy().pick("eeg"), reject_by_annotation=True)

eog_idx, scores = ica.find_bads_eog(raw, ch_name=["Fp1", "Fp2"])  # Fp sebagai proksi EOG
ica.plot_components(); ica.plot_sources(raw); ica.plot_properties(raw, picks=eog_idx)
ica.exclude = eog_idx        # setelah diverifikasi visual
ica.apply(raw)
raw.save(f"data/derivatives/{pid}_clean_raw.fif", overwrite=True)
```

- **ICLabel kurang andal di sini**: ICLabel dilatih pada data dengan filter 1–100 Hz,
  sedangkan data ini hanya sampai 50 Hz. Hasilnya boleh dipakai sebagai saran, tetapi
  keputusan akhir tetap berdasarkan inspeksi visual.
- **Jangan buang komponen "otot/gerak" secara otomatis**. Ritme mu/beta sensorimotor
  bisa ikut terbuang. Buang hanya komponen mata yang jelas (kedip dan saccade).
- Jika `Add_lead1/2` ternyata EOG, ganti `ch_name` di `find_bads_eog` ke kanal tersebut.
- Segmen dengan artefak gerak besar diberi anotasi `BAD_motion` dan tidak dipakai
  untuk *fit* ICA.

---

## 9. Tahap 4 — Epoching Gerakan

### 9.1 Konfirmasi fase aktual dari video (wajib)

Semua gerakan (NGEED, AGEM KANAN, AGEM KIRI) diinstruksikan `TURUN → TAHAN → NAIK`,
tetapi **sebagian partisipan tidak mengikutinya dengan tepat** (terlambat, hold
terlalu singkat, atau urutan tidak lengkap). Karena itu **onset epoch ditentukan dari
gerak tubuh di video, bukan dari label HUD**. Label HUD hanya dipakai sebagai jendela
pencarian.

**Langkah semi-otomatis:**

1. **Lintasan tubuh:** pose estimation (mis. MediaPipe Pose) pada region webcam untuk
   mengambil posisi vertikal pinggul (rata-rata *left/right hip*, koordinat y) di setiap
   frame, menggunakan timestamp PTS. Ngeed/agem adalah gerakan menurunkan tubuh dengan
   menekuk lutut, sehingga pinggul turun saat TURUN, stabil saat TAHAN, dan naik saat NAIK.
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
roi = ["C3", "C4", "P3", "P4", "O1", "O2"]
freqs = np.arange(6, 31, 1.0)
tfr = epochs.compute_tfr(method="morlet", freqs=freqs, n_cycles=freqs / 2,
                         picks=roi, average=False, return_itc=False)
tfr.apply_baseline(baseline=(-2.0, -0.5), mode="percent")   # (A−R)/R
data = tfr.get_data() * 100                                   # epoch × kanal × freq × waktu

bands = {"mu": (8, 13), "beta": (13, 30)}
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
- **Lateralisasi:** untuk agem kanan, ERD diharapkan lebih kuat di C3 (kontralateral),
  dan sebaliknya untuk agem kiri. Hitung juga indeks lateralisasi `C3 − C4`, tetapi
  interpretasikan dengan hati-hati karena referensi ipsilateral (A1 vs A2).
- **Band individual** (opsional, direkomendasikan karena rentang usia lebar): definisikan
  mu sebagai IAF−2 s.d. IAF+2 Hz, dengan IAF diambil dari `PXX_Baseline.EDF`.
- Baseline alternatif: power rata-rata dari `PXX_Baseline.EDF`. Pilih satu definisi dan
  gunakan secara konsisten.
- Resolusi: 100 Hz dengan Morlet `n_cycles = f/2` memberi panjang wavelet ≈ 0,5 dtk untuk
  semua frekuensi. Pastikan epoch cukup panjang agar tepi (*edge effect*) tidak jatuh ke
  jendela analisis.

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

def iaf(psd, picks):
    m = (f >= 7) & (f <= 13)
    spec = psd[[chs.index(c) for c in picks]][:, m].mean(axis=0)
    return (f[m] * spec).sum() / spec.sum()          # center of gravity

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
    # QC
    n_epochs_EO=n_eo, n_epochs_EC=n_ec,
)
pd.DataFrame([feat]).to_csv(f"results/{pid}_romberg_features.csv", index=False)
```

- Satu baris per partisipan, dengan `participant_id` sebagai kunci untuk digabung dengan
  data Standing Stork Test (waktu per partisipan).
- Untuk non-penari yang punya pre/post, tambahkan kolom `timepoint` agar penggabungan
  tidak tertukar.
- Tier 3 (entropi, koherensi) ditunda sampai Tier 1–2 selesai.

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

### 12.2 Romberg × Standing Stork Test

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

---

## 13. Kontrol Kualitas

Log per partisipan (`results/qc_log.csv`):

| participant_id | sync_offset_sec | sync_xcorr_r | sync_drift_sec | sync_residual_sec | ocr_manual_check_ok | add_lead_verdict | bad_channels | n_ica_eye_removed | n_reps_ok/late/short_hold/incomplete (/12) | n_move_epochs_kept | n_romberg_epochs_EO/EC | include | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

**Checklist per partisipan**

- [ ] File lengkap (manifest tidak kosong)
- [ ] Kotak HUD dicek pada frame sampel
- [ ] Kotak webcam dicek; pose terdeteksi stabil
- [ ] Timeline OCR divalidasi manual; 4 repetisi per gerakan (NGEED, AGEM KANAN, AGEM KIRI)
- [ ] Offset xcorr: puncak tunggal, |offset| ≤ 2 dtk, drift paruh-sesi < 0,2 dtk
- [ ] Offset divalidasi dengan transisi alpha Romberg (residual < 0,5 dtk)
- [ ] Fase aktual TURUN/TAHAN/NAIK diverifikasi manual untuk **semua** 12 repetisi; kode kepatuhan terisi
- [ ] Sampling rate = 100 Hz; filter 1–40 Hz; tanpa notch
- [ ] Kanal buruk dicatat & diinterpolasi (C3/C4 buruk → pertimbangkan eksklusi)
- [ ] Hanya komponen ICA mata yang dibuang, diverifikasi visual
- [ ] Jendela baseline tidak tumpang tindih dengan gerakan sebelumnya
- [ ] PSD Romberg EC menunjukkan puncak alpha oksipital
- [ ] Laporan QC HTML tersimpan (`mne.Report`) di `reports/`

---

## 14. Limitasi untuk Naskah

- **Tidak ada elektroda midline.** ERD sensorimotor diukur pada proksi C3/C4, dan theta
  frontal pada F3/F4, bukan Fz.
- **Sampling rate 100 Hz.** Analisis dibatasi ≤ 40 Hz, gamma tidak dapat dianalisis, dan
  notch 50 Hz tidak diterapkan.
- **Referensi telinga ipsilateral.** Membatasi interpretasi asimetri hemisfer.
- **Sinkronisasi EEG–video**: start manual oleh dua operator (aba-aba hitungan ke-3),
  lalu disempurnakan pasca-perekaman dengan korelasi silang sinyal gerak dan divalidasi
  dengan transisi alpha Romberg. Laporkan offset, r, drift, dan residual (rata-rata ± SD).
- **Onset gerakan dari video** (pose estimation + verifikasi manual), bukan dari sensor
  gerak/EMG. Resolusi temporal dibatasi frame rate (~30 fps) dan presisi sinkronisasi.
- **Kepatuhan instruksi bervariasi**: sebagian partisipan tidak mengikuti
  TURUN→TAHAN→NAIK dengan tepat. Laporkan jumlah repetisi per kode kepatuhan per grup,
  karena perbedaan kepatuhan antara penari dan non-penari sendiri adalah temuan.
- **Rentang usia sangat lebar.** Usia dikontrol sebagai kovariat, dan IAF individual
  dipertimbangkan.

---

## 15. Pertanyaan Terbuka yang Memblokir

Dari `CLAUDE.md` (jawaban pengguna 2026-09-23):

| # | Pertanyaan | Status / jawaban | Tahap |
|---|---|---|---|
| 1 | Mekanisme start EEG vs video | ✅ Dua device, start manual pada aba-aba hitungan ke-3 → prior offset ≈ 0, disempurnakan dengan xcorr (7.2) | 2 |
| 2 | Isi `Add_lead1` / `Add_lead2` | ⚠️ "Sepertinya lead referensi". Perlu verifikasi empiris (8.1.1) | 3 |
| 3 | Label HUD ngeed | ✅ `NGEED`, `AGEM KANAN`, `AGEM KIRI` | 1 |
| 4 | Urutan sub-fase | ✅ `TURUN → TAHAN → NAIK` untuk semua gerakan; kepatuhan dikonfirmasi dari video (9.1) | 4, 5 |
| 5 | Struktur folder untuk ke-38 partisipan (subfolder per grup? pre/post?) | ❓ Terbuka | 0 |
| 6 | Konfirmasi Python + MNE-Python | ❓ Terbuka (diasumsikan ya) | Semua |
| 7 | Posisi region webcam di frame video (untuk pose & sinyal gerak) | ❓ Baru: dicek dari frame sampel | 2, 4 |

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
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate.
  *Journal of the Royal Statistical Society B*, 57(1), 289–300.
