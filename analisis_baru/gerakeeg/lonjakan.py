"""Tahap 4: lonjakan artefak gerak (di atas epoch TE + referensi A2 robust).

Varian:
  T4_tandai     : tanpa koreksi. Potongan > 150 µV hanya ditandai tidak bersih (hasil Tahap 3).
  T4_ASR{k}     : Artifact Subspace Reconstruction pada sinyal kontinu 1–35 Hz, SEBELUM referensi A2, per belahan
                  (8 kanal). Dikalibrasi dari potongan Istirahat 1 dtk yang semua 8 kanalnya tidak datar dan ≤ 150 µV
                  (minimal 20 dtk; bila kurang, belahan itu tidak dikoreksi).
                  k = batas simpangan baku (5 agresif … 20 konservatif). Implementasi sendiri (asr_kalibrasi /
                  asr_proses) mengikuti asr_calibrate/asr_process (Kothe & Mullen) TANPA filter pembobot spektral:
                  meegkit 0.2 mengubah data kalibrasi yang bersih (r 0,54–0,91) dan mengabaikan k pada 100 Hz.
  T4_adaptif    : tanpa koreksi, tetapi ambang tolak per partisipan × kanal = median + 3 MAD dari log peak-to-peak
                  potongan 1 dtk Istirahat (sesudah A2), dibatasi 50–300 µV, menggantikan 150 µV tetap.
Penanda datar selalu diambil dari EDF mentah, sehingga rekonstruksi ASR pada kanal datar tidak dihitung sebagai data.
"""
import numpy as np

from .istilah import KANAL, KANAN, KIRI
from .kualitas import DATAR_BATAS, EKSTREM_UV

IDX = {c: i for i, c in enumerate(KANAL)}
BELAHAN = [np.array([IDX[c] for c in KIRI]), np.array([IDX[c] for c in KANAN])]
ASR_K = [20, 10, 5]
VARIAN = ["T4_tandai"] + [f"T4_ASR{k}" for k in ASR_K] + ["T4_adaptif"]


MIN_KALIBRASI_DTK = 20      # 8 kanal: ≥ 80 jendela 0,5 dtk untuk statistik ambang (EEGLAB menyarankan ≥ 30 dtk)


def data_kalibrasi(xf, datar, sf, W, g, panjang=1.0):
    """Gabungan potongan Istirahat 1 dtk yang semua kanal belahan g tidak datar dan ≤ 150 µV."""
    seg = []
    for w in W[W.fase == "Istirahat"].itertuples():
        for s in np.arange(w.mulai, w.selesai - panjang + 1e-9, panjang):
            i0, i1 = int(round(s * sf)), int(round((s + panjang) * sf))
            x = xf[g, i0:i1]
            if (datar[g, i0:i1].mean(axis=1) < DATAR_BATAS).all() and np.ptp(x, axis=1).max() <= EKSTREM_UV:
                seg.append(x)
    return np.concatenate(seg, axis=1) if seg else np.empty((len(g), 0))


def asr_kalibrasi(cal, sf, k, win=0.5):
    """→ (M, T): matriks pencampur (akar kovarians kalibrasi) dan ambang di ruang komponen."""
    C = cal @ cal.T / cal.shape[1]
    s, U = np.linalg.eigh(C)
    M = U @ np.diag(np.sqrt(np.maximum(s, 1e-12))) @ U.T
    D, V = np.linalg.eigh(M)
    Y = V.T @ cal
    n = int(win * sf)
    rms = np.array([np.sqrt((Y[:, a:a + n] ** 2).mean(axis=1)) for a in range(0, Y.shape[1] - n + 1, n // 2)])
    mu = np.median(rms, axis=0)
    sig = 1.4826 * np.median(np.abs(rms - mu), axis=0)
    T = np.diag(mu + k * sig) @ V.T
    return M, T


def asr_proses(x, sf, M, T, win=0.5, maxdims=0.66):
    """Rekonstruksi per jendela `win` (geser win/2) dengan peralihan kosinus antar-matriks rekonstruksi."""
    C, N = x.shape
    n = int(win * sf)
    h = n // 2
    y = x.copy()
    Rp = np.eye(C)
    selalu = np.arange(C) < C - int(round(maxdims * C))       # komponen terkecil selalu dipertahankan
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(h) / h)
    n_rekon = 0
    for c in range(0, N, h):
        a, b = max(0, c - h), min(N, c + h)
        xs = x[:, a:b]
        D, V = np.linalg.eigh(xs @ xs.T / max(1, xs.shape[1]))
        keep = (D < np.sum((T @ V) ** 2, axis=0)) | selalu
        if keep.all():
            R = np.eye(C)
        else:
            R = M @ np.linalg.pinv(keep[:, None] * (V.T @ M)) @ V.T
            n_rekon += 1
        s0, s1 = c, min(N, c + h)
        w = ramp[:s1 - s0]
        seg = x[:, s0:s1]
        y[:, s0:s1] = w * (R @ seg) + (1 - w) * (Rp @ seg)
        Rp = R
    return y, n_rekon * h / N


def asr(xf, datar, sf, W, k):
    """→ (xf terkoreksi, info). Per belahan; belahan tanpa kalibrasi ≥ 30 dtk dibiarkan."""
    y = xf.copy()
    info = {}
    for nama, g in zip(("kiri", "kanan"), BELAHAN):
        cal = data_kalibrasi(xf, datar, sf, W, g)
        info[f"kalibrasi_{nama}_dtk"] = round(cal.shape[1] / sf, 1)
        if cal.shape[1] < MIN_KALIBRASI_DTK * sf:
            info[f"asr_{nama}"] = f"dilewati (kalibrasi < {MIN_KALIBRASI_DTK} dtk)"
            continue
        M, T = asr_kalibrasi(cal, sf, k)
        y[g], frac = asr_proses(xf[g], sf, M, T)
        info[f"asr_{nama}"] = "ok"
        info[f"pct_waktu_direkonstruksi_{nama}"] = round(100 * frac, 1)
    return y, info


def ambang_adaptif(xf, datar, sf, W, rujuk, lo=50.0, hi=300.0):
    """Ambang per kanal dari Istirahat (sesudah referensi `rujuk`)."""
    lp = []
    for w in W[W.fase == "Istirahat"].itertuples():
        for s in np.arange(w.mulai, w.selesai - 1.0 + 1e-9, 0.5):
            i0 = int(round(s * sf))
            x, fd = rujuk(xf[:, i0:i0 + int(sf)], datar[:, i0:i0 + int(sf)].mean(axis=1))
            lp.append(np.where(fd < DATAR_BATAS, np.log(np.ptp(x, axis=1) + 1e-6), np.nan))
    lp = np.array(lp)
    med = np.nanmedian(lp, axis=0)
    mad = 1.4826 * np.nanmedian(np.abs(lp - med), axis=0)
    return np.clip(np.exp(med + 3 * mad), lo, hi)
