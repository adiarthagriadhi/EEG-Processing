"""Membaca EDF dan timestamp manual."""
from pathlib import Path

import mne
import numpy as np
import pandas as pd

from .istilah import GERAKAN, KANAL

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
TIMESTAMP = ROOT / "data" / "manual_timestamps"
SFREQ = 100.0


def muat_edf(pid):
    """EDF Trial → Raw MNE dengan 16 kanal EEG bernama 10-20 (tanpa '-A1'/'-A2'), satuan volt."""
    f = sorted((RAW / pid).glob("*Trial*.EDF")) + sorted((RAW / pid).glob("*Trial*.edf"))
    if len(f) != 1:
        raise FileNotFoundError(f"{pid}: harap tepat 1 EDF Trial di {RAW / pid}, ada {f}")
    raw = mne.io.read_raw_edf(f[0], preload=True, verbose="error")
    raw.rename_channels(lambda c: c.split("-")[0])
    raw.pick(KANAL)
    if raw.info["sfreq"] != SFREQ:
        raise ValueError(f"{pid}: sfreq {raw.info['sfreq']} ≠ {SFREQ}")
    raw.set_meas_date(None)                   # tanggal header KT88 tidak valid
    return raw


def offset_video_ke_eeg(pid):
    """Offset sinkronisasi repo (EEG = video + offset, dtk) dari hasil_analisis/per_partisipan/PXX/keputusan.yaml."""
    import yaml
    f = ROOT / "hasil_analisis" / "per_partisipan" / pid / "keputusan.yaml"
    return float(yaml.safe_load(f.read_text())["sync"]["offset_sec"])


def muat_timestamp(pid_or_path):
    """CSV timestamp (urutan, waktu_detik, label[, …]) → DataFrame bersih, berurutan waktu.
    Timestamp dibuat dari VIDEO (konfirmasi pengguna 2026-09-26). Offset ke waktu EEG: 0 (default) atau, bila
    GERAKEEG_OFFSET=repo, offset sinkronisasi repo per partisipan (sensitivitas)."""
    import os
    p = Path(pid_or_path)
    pid = None
    if not p.suffix:
        pid = str(pid_or_path)
        p = TIMESTAMP / f"{pid}_timestamps.csv"
    df = bersihkan_timestamp(pd.read_csv(p), str(p))
    if pid and os.environ.get("GERAKEEG_OFFSET") == "repo":
        df["waktu_detik"] = df.waktu_detik + offset_video_ke_eeg(pid)
    return df


def bersihkan_timestamp(df, sumber="timestamp"):
    df = df.copy()
    df["label"] = df["label"].astype(str).str.strip().str.upper()
    df["waktu_detik"] = pd.to_numeric(df["waktu_detik"], errors="raise").astype(float)
    if "urutan" not in df:
        df["urutan"] = np.arange(1, len(df) + 1)
    df = df.sort_values("urutan").reset_index(drop=True)
    if not df.waktu_detik.is_monotonic_increasing:
        raise ValueError(f"{sumber}: waktu_detik tidak naik sesuai urutan")
    tak_dikenal = set(df.label) - set(GERAKAN) - {"T", "B", "TT", "BM"}
    if tak_dikenal:
        raise ValueError(f"{sumber}: label tidak dikenal {sorted(tak_dikenal)}")
    kol = ["urutan", "waktu_detik", "label"]
    if "nilai" in df:                      # kualitas gerak per repetisi (0/1/2), diisi pada baris Gerak (N/AKA/AKI)
        df["nilai"] = pd.to_numeric(df["nilai"], errors="coerce")
        salah = df[df.nilai.notna() & ~df.nilai.isin([0, 1, 2])]
        if len(salah):
            raise ValueError(f"{sumber}: nilai harus 0/1/2, urutan {salah.urutan.tolist()}")
        kol.append("nilai")
    return df[kol]
