# Panduan Pemrosesan Data EEG Mentah (Raw EEG)

Panduan ini adalah alur kerja langkah demi langkah untuk mengolah data EEG mentah
hingga siap dianalisis (spektral/band power, ERP, dan waktu-frekuensi). Implementasi
menggunakan **Python + [MNE-Python](https://mne.tools)**, dengan catatan khusus untuk
perekaman dalam konteks olahraga/aktivitas fisik.

> Isi bagian **0. Profil Data** terlebih dahulu. Parameter pada langkah-langkah
> berikutnya (filter, referensi, epoch) harus disesuaikan dengan profil tersebut.

---

## Daftar Isi

0. [Profil Data](#0-profil-data)
1. [Struktur Folder Proyek](#1-struktur-folder-proyek)
2. [Instalasi Lingkungan](#2-instalasi-lingkungan)
3. [Gambaran Umum Pipeline](#3-gambaran-umum-pipeline)
4. [Langkah 1 — Memuat Data](#4-langkah-1--memuat-data)
5. [Langkah 2 — Inspeksi Visual](#5-langkah-2--inspeksi-visual)
6. [Langkah 3 — Montage (Posisi Elektroda)](#6-langkah-3--montage-posisi-elektroda)
7. [Langkah 4 — Filtering](#7-langkah-4--filtering)
8. [Langkah 5 — Resampling](#8-langkah-5--resampling)
9. [Langkah 6 — Kanal Buruk (Bad Channels)](#9-langkah-6--kanal-buruk-bad-channels)
10. [Langkah 7 — Re-referensi](#10-langkah-7--re-referensi)
11. [Langkah 8 — ICA untuk Artefak](#11-langkah-8--ica-untuk-artefak)
12. [Langkah 9 — Segmentasi (Epoching)](#12-langkah-9--segmentasi-epoching)
13. [Langkah 10 — Penolakan Epoch Buruk](#13-langkah-10--penolakan-epoch-buruk)
14. [Langkah 11 — Analisis](#14-langkah-11--analisis)
15. [Catatan Khusus EEG Olahraga](#15-catatan-khusus-eeg-olahraga)
16. [Kontrol Kualitas (QC) & Checklist](#16-kontrol-kualitas-qc--checklist)
17. [Pelaporan Metode](#17-pelaporan-metode)
18. [Troubleshooting](#18-troubleshooting)
19. [Referensi](#19-referensi)

---

## 0. Profil Data

Lengkapi tabel ini untuk setiap dataset sebelum memulai.

| Item                         | Nilai (isi)                                  |
|------------------------------|----------------------------------------------|
| Perangkat / amplifier        | _mis. BrainProducts, Emotiv, OpenBCI, Muse_  |
| Format file                  | _.edf / .bdf / .vhdr / .set / .cnt / .csv_   |
| Jumlah kanal EEG             |                                              |
| Kanal tambahan               | _EOG / ECG / EMG / akselerometer_            |
| Sampling rate (Hz)           |                                              |
| Referensi saat perekaman     | _mis. Cz, mastoid, CMS/DRL_                  |
| Satuan data mentah           | _µV atau V_                                  |
| Frekuensi listrik lokal      | **50 Hz** (Indonesia)                        |
| Desain / kondisi             | _istirahat mata terbuka/tertutup, pre/post latihan, tugas kognitif_ |
| Marker/event                 | _ada/tidak; kode trigger_                    |
| Durasi per kondisi           |                                              |
| Jumlah partisipan            |                                              |

---

## 1. Struktur Folder Proyek

Disarankan mengikuti gaya [BIDS](https://bids.neuroimaging.io/) agar rapi dan mudah
direproduksi.

```
EEG-Processing/
├── EEG_PROCESSING.md          # panduan ini
├── data/
│   ├── raw/                   # data asli — JANGAN diubah
│   │   └── sub-01/
│   │       └── sub-01_task-rest_eeg.edf
│   ├── derivatives/           # hasil pemrosesan (.fif)
│   └── participants.tsv       # data demografis/metadata
├── scripts/
│   ├── 01_preprocess.py
│   ├── 02_epoch_clean.py
│   └── 03_analysis.py
├── reports/                   # gambar QC, laporan HTML
└── results/                   # tabel hasil (CSV) untuk statistik
```

Prinsip: **data mentah tidak pernah ditimpa**. Setiap langkah menyimpan hasil baru di
`data/derivatives/`.

---

## 2. Instalasi Lingkungan

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install mne mne-icalabel autoreject python-picard \
            numpy scipy pandas matplotlib edfio
```

Cek instalasi:

```python
import mne
mne.sys_info()
```

---

## 3. Gambaran Umum Pipeline

```
Raw EEG
  │
  ├─ 1. Muat data & cek satuan (Volt)
  ├─ 2. Inspeksi visual (plot, PSD)
  ├─ 3. Set montage 10-20
  ├─ 4. Filter: notch 50 Hz, band-pass (mis. 1–40 Hz)
  ├─ 5. Resample (opsional, mis. 250 Hz)
  ├─ 6. Tandai & interpolasi kanal buruk
  ├─ 7. Re-referensi (average / mastoid)
  ├─ 8. ICA → buang komponen mata, otot, jantung
  ├─ 9. Epoching (berbasis event atau fixed-length)
  ├─ 10. Tolak epoch buruk (threshold / autoreject)
  └─ 11. Analisis: band power, ERP, time-frequency
          └─ Ekspor ke CSV → statistik
```

**Urutan penting:** tandai kanal buruk **sebelum** re-referensi rata-rata dan ICA,
karena satu kanal rusak akan "menular" ke semua kanal lain.

---

## 4. Langkah 1 — Memuat Data

```python
import mne
from pathlib import Path

raw_path = Path("data/raw/sub-01/sub-01_task-rest_eeg.edf")

# Pilih fungsi sesuai format:
raw = mne.io.read_raw_edf(raw_path, preload=True)          # .edf
# raw = mne.io.read_raw_bdf(raw_path, preload=True)        # .bdf (BioSemi)
# raw = mne.io.read_raw_brainvision("x.vhdr", preload=True) # BrainVision
# raw = mne.io.read_raw_eeglab("x.set", preload=True)      # EEGLAB
# raw = mne.io.read_raw_cnt("x.cnt", preload=True)         # Neuroscan

print(raw.info)
print(raw.ch_names)
```

### Data CSV (OpenBCI, Muse, dsb.)

MNE mengharapkan satuan **Volt**. Kebanyakan perangkat konsumen menyimpan µV,
sehingga perlu dikalikan `1e-6`.

```python
import numpy as np
import pandas as pd

df = pd.read_csv("data/raw/sub-01/recording.csv")
ch_names = ["Fp1", "Fp2", "C3", "C4", "P7", "P8", "O1", "O2"]  # sesuaikan
sfreq = 250.0                                                    # sesuaikan

data = df[ch_names].to_numpy().T * 1e-6   # µV → V, bentuk (n_kanal, n_sampel)
info = mne.create_info(ch_names, sfreq, ch_types="eeg")
raw = mne.io.RawArray(data, info)
```

### Atur tipe kanal non-EEG

```python
raw.set_channel_types({"VEOG": "eog", "HEOG": "eog", "ECG": "ecg"})  # jika ada
```

### Cek satuan

Amplitudo EEG normal berkisar puluhan µV. Jika `raw.get_data().std()` bernilai
sekitar 10–100 (bukan ~1e-5), data kemungkinan masih dalam µV dan perlu dikonversi.

---

## 5. Langkah 2 — Inspeksi Visual

Selalu **lihat data** sebelum memproses.

```python
raw.plot(duration=20, n_channels=len(raw.ch_names), scalings=dict(eeg=100e-6))
raw.compute_psd(fmax=100).plot()
```

Yang dicari:

- Kanal datar (flat) atau sangat bising.
- Puncak 50 Hz (dan harmonik 100 Hz) pada PSD.
- Kedipan mata (defleksi besar di Fp1/Fp2), gerakan kepala, burst otot (EMG).
- Pergeseran lambat (drift) akibat keringat.
- Puncak alfa (~8–12 Hz) di oksipital saat mata tertutup → tanda data sehat.

Catat segmen buruk sebagai anotasi (klik-tarik di jendela plot, beri label
`BAD_...`), atau lewat kode:

```python
raw.annotations.append(onset=120.0, duration=5.0, description="BAD_movement")
```

---

## 6. Langkah 3 — Montage (Posisi Elektroda)

```python
montage = mne.channels.make_standard_montage("standard_1020")
raw.set_montage(montage, on_missing="warn")
raw.plot_sensors(show_names=True)
```

Jika nama kanal berbeda (mis. `EEG Fp1-REF`), ubah dulu:

```python
raw.rename_channels(lambda name: name.replace("EEG ", "").replace("-REF", ""))
```

---

## 7. Langkah 4 — Filtering

| Filter       | Nilai umum             | Keterangan                                              |
|--------------|------------------------|---------------------------------------------------------|
| Notch        | 50 Hz (+100 Hz)        | Interferensi listrik PLN                                |
| High-pass    | 0,5–1 Hz               | 1 Hz untuk resting-state/band power; 0,1 Hz untuk ERP   |
| Low-pass     | 40–45 Hz               | Naikkan (mis. 80–100 Hz) jika meneliti gamma            |

```python
raw.notch_filter(freqs=[50, 100])
raw.filter(l_freq=1.0, h_freq=40.0)   # FIR zero-phase (default MNE)
```

> Untuk **ERP**, high-pass > 0,3 Hz dapat mendistorsi komponen lambat (mis. P300).
> Gunakan 0,1 Hz untuk data yang dipakai analisis ERP, dan salinan 1 Hz khusus ICA
> (lihat Langkah 8).

---

## 8. Langkah 5 — Resampling

Opsional; mempercepat komputasi. Lakukan **setelah** low-pass filter.
Sampling rate baru minimal ~3–4× frekuensi tertinggi yang dianalisis.

```python
raw.resample(250)
```

Jika ada event/trigger, resample setelah events diekstraksi atau resample Epochs,
agar waktu trigger tetap presisi.

---

## 9. Langkah 6 — Kanal Buruk (Bad Channels)

Tandai kanal buruk berdasarkan inspeksi visual (klik nama kanal di `raw.plot()`),
lalu interpolasi (spherical spline).

```python
raw.info["bads"] = ["T7", "Fp2"]      # contoh
raw.interpolate_bads(reset_bads=True)
```

Pedoman praktis:

- Kanal datar, amplitudo sangat besar, atau korelasi rendah dengan tetangganya.
- Jika > ~10–15% kanal buruk, pertimbangkan mengeluarkan partisipan/sesi.
- Pada headset dengan sedikit kanal (mis. 4–8 kanal), interpolasi kurang akurat —
  lebih baik sesi tersebut dieksklusi atau kanal dikeluarkan dari analisis.
- Catat kanal yang diinterpolasi untuk setiap partisipan (untuk laporan).

---

## 10. Langkah 7 — Re-referensi

```python
raw.set_eeg_reference("average", projection=False)   # rata-rata semua kanal
# atau mastoid terhubung:
# raw.set_eeg_reference(["M1", "M2"])
```

- **Average reference**: cocok untuk ≥ ~32 kanal dengan cakupan kepala merata.
- **Mastoid / linked-ear**: umum untuk sedikit kanal atau mengikuti literatur ERP tertentu.
- Gunakan referensi yang **sama** di seluruh partisipan dan konsisten dengan studi rujukan.

---

## 11. Langkah 8 — ICA untuk Artefak

ICA memisahkan sinyal menjadi komponen independen; komponen artefak (kedip mata,
gerakan mata, otot, jantung) dibuang lalu sinyal direkonstruksi.

```python
from mne.preprocessing import ICA
from mne_icalabel import label_components

# 1. Salinan khusus ICA: high-pass 1 Hz membuat ICA lebih stabil
raw_for_ica = raw.copy().filter(l_freq=1.0, h_freq=100.0 if raw.info["sfreq"] > 200 else None)

# 2. Fit ICA (buang segmen BAD_ secara otomatis)
ica = ICA(
    n_components=0.99,            # atau angka < jumlah kanal - kanal interpolasi
    method="picard",
    fit_params=dict(extended=True, ortho=False),   # setara extended-Infomax
    random_state=97,
    max_iter="auto",
)
ica.fit(raw_for_ica, reject_by_annotation=True)

# 3. Klasifikasi otomatis dengan ICLabel
labels = label_components(raw_for_ica, ica, method="iclabel")
exclude = [
    i for i, (lab, prob) in enumerate(zip(labels["labels"], labels["y_pred_proba"]))
    if lab not in ("brain", "other") and prob > 0.80
]
print("Komponen dibuang:", exclude, [labels["labels"][i] for i in exclude])

# 4. Verifikasi visual — WAJIB
ica.plot_components()
ica.plot_sources(raw_for_ica)
ica.plot_properties(raw_for_ica, picks=exclude)

# 5. Terapkan pada data utama
ica.exclude = exclude
ica.apply(raw)
```

Catatan:

- ICLabel dilatih pada data dengan **average reference** dan filter **1–100 Hz**.
- Jika tersedia kanal EOG/ECG, gunakan juga `ica.find_bads_eog(raw_for_ica)` dan
  `ica.find_bads_ecg(raw_for_ica)`.
- Jumlah komponen dibatasi oleh *rank* data: re-referensi rata-rata dan interpolasi
  masing-masing mengurangi rank.
- Laporkan jumlah komponen yang dibuang per partisipan (rata-rata ± SD).

---

## 12. Langkah 9 — Segmentasi (Epoching)

### a) Resting-state / kondisi kontinu (pre vs post latihan)

```python
epochs = mne.make_fixed_length_epochs(
    raw, duration=2.0, overlap=1.0, reject_by_annotation=True, preload=True
)
```

Jika rekaman berisi beberapa kondisi dalam satu file, potong dahulu:

```python
raw_pre  = raw.copy().crop(tmin=0,   tmax=180)   # detik; sesuaikan
raw_post = raw.copy().crop(tmin=600, tmax=780)
```

### b) Berbasis event (ERP / tugas kognitif)

```python
events, event_id = mne.events_from_annotations(raw)
# atau: events = mne.find_events(raw, stim_channel="STI 014")

epochs = mne.Epochs(
    raw, events, event_id=event_id,
    tmin=-0.2, tmax=0.8,
    baseline=(None, 0),
    reject_by_annotation=True,
    preload=True,
)
```

---

## 13. Langkah 10 — Penolakan Epoch Buruk

### Opsi A — Threshold amplitudo sederhana

```python
epochs.drop_bad(reject=dict(eeg=150e-6), flat=dict(eeg=1e-6))
epochs.plot_drop_log()
```

### Opsi B — `autoreject` (data-driven, direkomendasikan)

```python
from autoreject import AutoReject

ar = AutoReject(random_state=42, n_jobs=-1)
epochs_clean, reject_log = ar.fit_transform(epochs, return_log=True)
reject_log.plot("horizontal")
```

Pedoman: bila > ~25–30% epoch terbuang, periksa kembali langkah sebelumnya atau
pertimbangkan eksklusi partisipan. Pastikan jumlah epoch **seimbang** antar kondisi
(`mne.epochs.equalize_epoch_counts`) bila membandingkan kondisi.

Simpan hasil:

```python
epochs_clean.save("data/derivatives/sub-01/sub-01_task-rest_proc-clean_epo.fif",
                  overwrite=True)
```

---

## 14. Langkah 11 — Analisis

### a) Power spektral & band power

| Band   | Rentang (Hz) |
|--------|--------------|
| Delta  | 1–4          |
| Theta  | 4–8          |
| Alpha  | 8–13         |
| Beta   | 13–30        |
| Gamma  | 30–40 (sesuai low-pass) |

```python
import numpy as np
import pandas as pd

spectrum = epochs_clean.compute_psd(method="welch", fmin=1, fmax=40,
                                    n_fft=int(2 * epochs_clean.info["sfreq"]))
psds, freqs = spectrum.get_data(return_freqs=True)   # (epoch, kanal, frekuensi)
psd_mean = psds.mean(axis=0)                          # rata-rata antar epoch

bands = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13),
         "beta": (13, 30), "gamma": (30, 40)}

total = np.trapezoid(psd_mean, freqs, axis=-1)
rows = []
for band, (fmin, fmax) in bands.items():
    mask = (freqs >= fmin) & (freqs < fmax)
    abs_power = np.trapezoid(psd_mean[:, mask], freqs[mask], axis=-1)
    for ch, a, r in zip(epochs_clean.ch_names, abs_power, abs_power / total):
        rows.append(dict(subject="sub-01", condition="pre", channel=ch, band=band,
                         abs_power_uV2=a * 1e12, rel_power=r))

pd.DataFrame(rows).to_csv("results/sub-01_bandpower.csv", index=False)
```

- **Absolute power** (µV²) sensitif terhadap impedansi & ketebalan tengkorak;
  **relative power** (band / total) lebih robust antar individu.
- Untuk rasio/indeks umum: theta/beta, alpha asymmetry frontal
  (`ln(F4) − ln(F3)` pada alpha), individual alpha frequency (IAF).
- Pertimbangkan memisahkan komponen aperiodik (1/f) dengan paket
  [`specparam`/FOOOF](https://fooof-tools.github.io/) bila membandingkan pre–post
  latihan, karena perubahan 1/f dapat menyamar sebagai perubahan band power.

Visualisasi topografi:

```python
spectrum.plot_topomap(bands={"Alpha (8-13 Hz)": (8, 13)}, ch_type="eeg")
```

### b) ERP

```python
evoked = epochs_clean["target"].average()
evoked.plot(gfp=True)
evoked.plot_joint()

# Contoh: amplitudo rata-rata P300 di Pz, jendela 300–500 ms
p300 = evoked.copy().pick("Pz").crop(0.3, 0.5).data.mean() * 1e6   # µV
```

### c) Time-frequency (TFR)

```python
freqs = np.arange(4, 40, 1)
tfr = epochs_clean.compute_tfr(method="morlet", freqs=freqs, n_cycles=freqs / 2,
                               return_itc=False, average=True)
tfr.plot(picks="Cz", baseline=(-0.2, 0), mode="logratio")
```

### d) Statistik

Ekspor nilai (band power / amplitudo ERP) per partisipan × kondisi × kanal ke CSV,
lalu analisis dengan uji yang sesuai (paired t-test / Wilcoxon, ANOVA pengukuran
berulang, atau linear mixed model). Untuk perbandingan banyak kanal/frekuensi,
gunakan koreksi multiple comparison (FDR) atau cluster-based permutation test
(`mne.stats.permutation_cluster_test`).

---

## 15. Catatan Khusus EEG Olahraga

Perekaman sebelum/selama/setelah latihan fisik memiliki artefak khas:

| Artefak                     | Ciri                                    | Penanganan                                         |
|-----------------------------|-----------------------------------------|----------------------------------------------------|
| Keringat                    | Drift sangat lambat (< 0,5 Hz)          | High-pass 1 Hz; keringkan kulit; ruang sejuk       |
| Otot (EMG) rahang/leher     | Aktivitas broadband > 20 Hz, temporal   | ICA (label *muscle*); hati-hati menafsirkan beta/gamma |
| Gerakan kepala/kabel        | Lonjakan besar serentak                 | Anotasi `BAD_`, autoreject, fiksasi kabel          |
| Langkah (treadmill/sepeda)  | Periodik sesuai irama gerak             | Akselerometer sebagai referensi; ASR; ICA          |
| Jantung (ECG)               | Kompleks QRS periodik, HR tinggi pasca latihan | `ica.find_bads_ecg`                         |

Rekomendasi:

- Rekam resting-state **pre** dan **post** dengan durasi & kondisi (mata terbuka/tertutup)
  yang identik; beri jeda stabilisasi (mis. 5 menit) pasca latihan bila sesuai desain.
- Catat HR, RPE, suhu ruang, dan waktu pengukuran di metadata.
- Cek dan catat **impedansi** sebelum dan sesudah sesi.
- Untuk data selama gerak, pertimbangkan Artifact Subspace Reconstruction (ASR),
  mis. paket `asrpy`, sebelum ICA.

---

## 16. Kontrol Kualitas (QC) & Checklist

Buat laporan QC otomatis per partisipan:

```python
report = mne.Report(title="sub-01 QC")
report.add_raw(raw, title="Raw (setelah preprocessing)", psd=True)
report.add_ica(ica, title="ICA", inst=raw_for_ica)
report.add_epochs(epochs_clean, title="Epochs bersih")
report.save("reports/sub-01_qc.html", overwrite=True)
```

**Checklist per partisipan**

- [ ] Profil data (Bagian 0) terisi
- [ ] Satuan data sudah Volt
- [ ] Montage terpasang, nama kanal sesuai 10-20
- [ ] Notch 50 Hz & band-pass diterapkan (nilai dicatat)
- [ ] Kanal buruk ditandai & diinterpolasi (daftar dicatat)
- [ ] Re-referensi diterapkan
- [ ] Komponen ICA dibuang diverifikasi visual (jumlah & jenis dicatat)
- [ ] Persentase epoch dibuang dicatat
- [ ] PSD akhir wajar (tidak ada puncak 50 Hz, ada puncak alfa)
- [ ] Hasil disimpan di `data/derivatives/` dan `results/`

Contoh log QC (`results/qc_log.csv`):

| subject | bad_channels | n_ica_removed | ica_types        | epochs_total | epochs_dropped_% | include |
|---------|--------------|---------------|------------------|--------------|------------------|---------|
| sub-01  | T7           | 3             | eye, eye, muscle | 179          | 8,4              | yes     |

---

## 17. Pelaporan Metode

Laporkan di bagian Metode (mengacu pada pedoman COBIDAS MEEG, Pernet et al., 2020):

- Perangkat, jumlah & lokasi elektroda, referensi & ground perekaman, sampling rate,
  impedansi.
- Software & versi (mis. MNE-Python v1.x, Python 3.x).
- Semua parameter filter (tipe, frekuensi cut-off, orde/panjang).
- Kriteria & jumlah kanal buruk yang diinterpolasi, metode interpolasi.
- Referensi yang digunakan untuk analisis.
- Algoritma ICA, kriteria penolakan komponen, jumlah rata-rata komponen dibuang.
- Panjang epoch, baseline, kriteria & persentase epoch yang ditolak.
- Metode estimasi spektral (Welch: panjang window, overlap), definisi band.
- Uji statistik & koreksi multiple comparison.

Contoh paragraf:

> Data EEG diproses menggunakan MNE-Python (v1.x). Data difilter notch pada 50 Hz dan
> band-pass 1–40 Hz (FIR zero-phase), di-resample ke 250 Hz, dan direferensikan ulang ke
> rata-rata semua elektroda. Kanal buruk (rata-rata X ± Y per partisipan) diinterpolasi
> dengan spherical spline. Artefak okular, otot, dan jantung dihapus menggunakan ICA
> (extended Infomax via Picard) dengan klasifikasi ICLabel (probabilitas > 0,80) dan
> verifikasi visual (rata-rata X ± Y komponen dibuang). Data disegmentasi menjadi epoch
> 2 detik (overlap 50%), dan epoch buruk ditolak menggunakan autoreject (rata-rata X%).
> Power spektral diestimasi dengan metode Welch...

---

## 18. Troubleshooting

| Masalah                                         | Kemungkinan penyebab / solusi                                   |
|-------------------------------------------------|-----------------------------------------------------------------|
| Plot kosong / garis lurus                       | Satuan salah (µV dibaca sebagai V) → kalikan `1e-6`             |
| `set_montage` gagal: kanal tidak ditemukan      | Nama kanal tidak standar → `rename_channels`                    |
| ICA tidak konvergen                             | Naikkan `max_iter`, pastikan high-pass 1 Hz, kurangi `n_components` |
| Error rank pada ICA                             | `n_components` > rank data (akibat average ref/interpolasi)     |
| Masih ada puncak 50 Hz                          | Tambahkan harmonik (100 Hz), cek grounding saat perekaman       |
| Terlalu banyak epoch dibuang                    | Threshold terlalu ketat, atau artefak belum dibersihkan ICA     |
| Tidak ada puncak alfa saat mata tertutup        | Cek kanal oksipital, referensi, dan kualitas kontak elektroda   |

---

## 19. Referensi

- Gramfort, A., et al. (2013). MEG and EEG data analysis with MNE-Python.
  *Frontiers in Neuroscience*, 7, 267.
- Pion-Tonachini, L., Kreutz-Delgado, K., & Makeig, S. (2019). ICLabel: An automated
  electroencephalographic independent component classifier. *NeuroImage*, 198, 181–197.
- Jas, M., et al. (2017). Autoreject: Automated artifact rejection for MEG and EEG data.
  *NeuroImage*, 159, 417–429.
- Pernet, C., et al. (2020). Issues and recommendations from the OHBM COBIDAS MEEG
  committee for reproducible EEG and MEG research. *Nature Neuroscience*, 23, 1473–1483.
- Donoghue, T., et al. (2020). Parameterizing neural power spectra into periodic and
  aperiodic components. *Nature Neuroscience*, 23, 1655–1665.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.).
  MIT Press.
- Dokumentasi MNE-Python: <https://mne.tools/stable/auto_tutorials/index.html>
