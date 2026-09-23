# Panduan Pemrosesan EEG–Video: Penari Bali vs Non-Penari

Panduan kerja langkah demi langkah untuk mengolah data mentah proyek ini
(`PXX_Baseline.EDF`, `PXX_Trial.EDF`, `motor_PXX_Trial_*.webm`) sampai menjadi
tabel ERD/ERS gerakan dan fitur Romberg yang siap dianalisis statistik.

- **Konteks ilmiah, fakta data, dan keputusan desain:** lihat [`CLAUDE.md`](CLAUDE.md).
  Dokumen ini adalah turunan teknisnya (bagaimana mengerjakannya).
- **Status:** potongan kode di bawah adalah **templat** yang belum diuji pada data
  nyata. Beberapa langkah bergantung pada jawaban [Pertanyaan Terbuka](#15-pertanyaan-terbuka-yang-memblokir)
  dan ditandai 🔒.

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
| `Add_lead1`, `Add_lead2` belum diketahui isinya 🔒 | Sementara diset tipe `misc` (tidak ikut filter, referensi, dan ICA). |
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
│   ├── timeline/                 # PXX_task_timeline.csv (Tahap 1)
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
            av pytesseract opencv-python rapidfuzz statsmodels pingouin pyyaml
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
Tahap 2  Anchor di EEG & video ─► sync_offset_sec ─► manifest   ⛔ gerbang validasi
   │
Tahap 3  EDF ─► rename/montage ─► filter 1–40 Hz ─► kanal buruk ─► ICA (mata saja)
   │
Tahap 4  timeline + offset ─► Annotations (waktu EEG) ─► Epochs per repetisi
   │
   ├─► Tahap 5   ERD/ERS mu & beta (C3/C4, P3/P4, O1/O2) ─► erd_ers_long.csv
   └─► Tahap 5b  Romberg EO/EC ─► romberg_features.csv (join dgn Stork Test)
   │
Tahap 6  Mixed model (ERD/ERS) & korelasi parsial (Romberg × Stork)
```

Semua parameter disimpan di satu file `config.yaml`, jangan ditulis langsung (*hardcode*) di skrip:

```yaml
sfreq_expected: 100
filter: {l_freq: 1.0, h_freq: 40.0}
hud_box: {x0: 960, y0: 250, x1: 1280, y1: 480}   # verifikasi per file
ocr_sample_sec: 0.2
bands: {theta: [4, 8], mu: [8, 13], beta: [13, 30]}
roi: [C3, C4, P3, P4, O1, O2]
erd:
  tmin: -2.0          # detik relatif onset (sesuaikan setelah durasi sub-fase diketahui)
  tmax: 4.0
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

VOCAB = [   # label HUD yang diketahui; tambahkan label NGEED setelah dikonfirmasi 🔒
    "AGEM KANAN TURUN", "AGEM KANAN TAHAN", "AGEM KANAN NAIK",
    "AGEM KIRI TURUN",  "AGEM KIRI TAHAN",  "AGEM KIRI NAIK",
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
    seg[["task", "subphase"]] = seg.label.str.extract(r"^(AGEM KANAN|AGEM KIRI)\s+(\w+)$")
    seg.task = seg.task.fillna(seg.label)
    return seg.reset_index(drop=True)
```

Output `data/timeline/PXX_task_timeline.csv` berisi kolom `label, task, subphase,
start_time_video_sec, end_time_video_sec`, ditambah nomor repetisi (hitung per task
secara berurutan).

**Validasi (wajib):** periksa manual 10–15% segmen dengan membandingkan waktu di
CSV terhadap video di pemutar (VLC menampilkan waktu presisi). Juga pastikan:

- Jumlah repetisi per gerakan = 4.
- Urutan sub-fase konsisten (🔒 tunggu konfirmasi apakah selalu TURUN→TAHAN→NAIK).
- Sampel `UNKNOWN` berturut-turut > 1 detik → periksa frame tersebut.

---

## 7. Tahap 2 — Sinkronisasi EEG↔Video

⛔ **Gerbang:** jangan lanjut ke Tahap 4 untuk partisipan yang `sync_validated = False`.

Definisi (disimpan di manifest):

```
t_eeg = t_video + sync_offset_sec
sync_offset_sec = t_anchor_EEG − t_anchor_video
```

### 7.1 Anchor utama (awal sesi)

🔒 Tergantung jawaban Pertanyaan 1. Jika tidak ada marker eksplisit, gunakan onset
gerakan agem pertama:

- **Video:** waktu awal segmen `AGEM … TURUN` pertama dari timeline, disempurnakan
  dengan mencari frame pertama saat tubuh mulai bergerak.
- **EEG:** lonjakan artefak gerak (amplitudo/EMG) di kanal frontal/temporal.

```python
import numpy as np
import mne

raw = mne.io.read_raw_edf("data/raw/P01/P01_Trial.EDF", preload=True)
env = raw.copy().pick(["F7-A1", "F8-A2", "T3-A1", "T4-A2"]) \
         .filter(20, 45).apply_hilbert(envelope=True).get_data().mean(axis=0)
t = raw.times
# Cari lonjakan di sekitar perkiraan (t_video_anchor ± 30 dtk), lalu verifikasi visual:
raw.plot(start=max(0, t_guess - 10), duration=20)
```

### 7.2 Anchor validasi (akhir sesi): transisi Romberg mata terbuka → tertutup

Saat mata tertutup, **alpha oksipital (O1/O2) naik dengan jelas** dan biasanya
diawali artefak kedip/tutup mata di Fp1/Fp2. Tanda ini terlihat objektif di EEG dan
waktunya diketahui dari HUD. Anchor ini dipakai untuk:

1. **Memvalidasi** offset dari anchor awal: selisih prediksi vs observasi harus
   < ~0,5 dtk.
2. **Mendeteksi drift clock**: jika selisihnya konsisten membesar seiring waktu,
   gunakan koreksi linear dengan dua titik (anchor awal dan akhir):
   `t_eeg = a · t_video + b`.

```python
alpha = raw.copy().pick(["O1-A1", "O2-A2"]).filter(8, 13) \
           .apply_hilbert(envelope=True).get_data().mean(axis=0)
# Plot alpha envelope di sekitar prediksi t_eeg transisi EO→EC
```

Catat di manifest: `sync_offset_sec`, `sync_method` (anchor apa), `sync_residual_sec`
(selisih pada anchor validasi), `sync_validated` (True/False).

---

## 8. Tahap 3 — Preprocessing EEG

```python
import mne

raw = mne.io.read_raw_edf(path_trial_edf, preload=True)
assert raw.info["sfreq"] == 100

# 1) Rename & tipe kanal
raw.rename_channels(lambda ch: ch.split("-")[0])          # "C3-A1" → "C3"
raw.set_channel_types({"Add_lead1": "misc", "Add_lead2": "misc"})   # 🔒 sementara
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
| Linked-ear matematis | **Hanya jika** ada sinyal A1–A2 terekam (🔒 apakah `Add_lead` berisi ini?) | `Ckiri_linked = Ckiri − ½(A2−A1)`, dst. |

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

```python
import pandas as pd
import mne

man = pd.read_csv("data/manifest.csv").set_index("participant_id")
row = man.loc[pid]
assert row.sync_validated, f"{pid}: sinkronisasi belum divalidasi"

tl = pd.read_csv(f"data/timeline/{pid}_task_timeline.csv")
onset_eeg = tl.start_time_video_sec + row.sync_offset_sec     # atau model linear a·t+b
dur = tl.end_time_video_sec - tl.start_time_video_sec
desc = (tl.task + "/" + tl.subphase.fillna("NA") + "/rep" + tl.rep.astype(str)) \
          .str.replace(" ", "_")

raw = mne.io.read_raw_fif(f"data/derivatives/{pid}_clean_raw.fif", preload=True)
raw.set_annotations(raw.annotations + mne.Annotations(onset_eeg, dur, desc))

# Onset gerakan = awal sub-fase TURUN (🔒 konfirmasi urutan sub-fase)
events, event_id = mne.events_from_annotations(raw, regexp=r"^AGEM_.*/TURUN/")
epochs = mne.Epochs(raw, events, event_id, tmin=-2.0, tmax=4.0,
                    baseline=None, reject_by_annotation=True, preload=True)
epochs.save(f"data/derivatives/{pid}_move-epo.fif", overwrite=True)
```

Catatan:

- Onset HUD ≠ onset gerakan riil (ada waktu reaksi). Jika diperlukan, sempurnakan onset
  dengan deteksi gerak dari video (selisih frame / optical flow / pose estimation)
  dalam jendela ±2 dtk dari onset HUD. Simpan kolom `onset_refined_video_sec`.
- Pastikan **jendela baseline** (mis. −2 s.d. −0,5 dtk) jatuh di segmen `BERDIRI RILEKS`
  atau istirahat, **bukan** di sisa gerakan sebelumnya. Periksa terhadap timeline.
- Target 4 repetisi × {ngeed 🔒, agem kanan, agem kiri}. Catat jumlah epoch yang bertahan.

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
active = (tfr.times >= 0.0) & (tfr.times <= 2.0)              # 🔒 sesuaikan dgn durasi sub-fase
rows = []
for i, ev in enumerate(epochs.events[:, 2]):
    cond = {v: k for k, v in epochs.event_id.items()}[ev]      # mis. "AGEM_KANAN/TURUN/rep1"
    for b, (lo, hi) in bands.items():
        fmask = (freqs >= lo) & (freqs < hi)
        vals = data[i][:, fmask][:, :, active].mean(axis=(1, 2))
        for ch, v in zip(roi, vals):
            rows.append(dict(participant_id=pid, condition=cond, band=b,
                             channel=ch, erd_pct=v))
pd.DataFrame(rows).to_csv(f"results/{pid}_erd_ers.csv", index=False)

# Visualisasi rata-rata
tfr.average().plot(picks=["C3", "C4"], title=f"{pid} %ERD/ERS")
```

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
df["movement"] = df.condition.str.split("/").str[0]

sub = df[(df.band == "mu") & (df.channel == "C3")]
m = smf.mixedlm("erd_pct ~ group * movement + age", sub,
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

| participant_id | sync_offset_sec | sync_residual_sec | ocr_manual_check_ok | bad_channels | n_ica_eye_removed | n_move_epochs_kept (/12) | n_romberg_epochs_EO/EC | include | notes |
|---|---|---|---|---|---|---|---|---|---|

**Checklist per partisipan**

- [ ] File lengkap (manifest tidak kosong)
- [ ] Kotak HUD dicek pada frame sampel
- [ ] Timeline OCR divalidasi manual; 4 repetisi per gerakan
- [ ] Offset sinkronisasi dihitung **dan** divalidasi dengan anchor Romberg (residual < 0,5 dtk)
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
- **Sinkronisasi EEG–video** dilakukan pasca-perekaman berbasis anchor. Laporkan metode
  dan residual sinkronisasi (rata-rata ± SD).
- **Onset berbasis instruksi HUD** (bukan sensor gerak), kecuali disempurnakan dengan
  analisis video.
- **Rentang usia sangat lebar.** Usia dikontrol sebagai kovariat, dan IAF individual
  dipertimbangkan.

---

## 15. Pertanyaan Terbuka yang Memblokir

Dari `CLAUDE.md`. Langkah bertanda 🔒 menunggu jawaban berikut:

| # | Pertanyaan | Memblokir |
|---|---|---|
| 1 | EEG & video dimulai oleh tombol/software yang sama? Ada anchor fisik (clap, tombol)? | Tahap 2 |
| 2 | Isi `Add_lead1` / `Add_lead2` (EOG? EMG? A1–A2?) | Tahap 3 (ICA, referensi) |
| 3 | Nama label HUD untuk gerakan **ngeed** dan posisinya dalam urutan task | Tahap 1, 4 |
| 4 | Urutan pasti sub-fase agem (TURUN→TAHAN→NAIK?) dan durasi tiap sub-fase | Tahap 4, 5 (jendela) |
| 5 | Struktur folder untuk ke-38 partisipan (subfolder per grup? pre/post?) | Tahap 0 |
| 6 | Konfirmasi Python + MNE-Python | Semua |

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
