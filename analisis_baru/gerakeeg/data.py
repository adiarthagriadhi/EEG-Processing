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


def muat_timestamp(pid_or_path):
    """CSV timestamp (urutan, waktu_detik, label[, …]) → DataFrame bersih, berurutan waktu."""
    p = Path(pid_or_path)
    if not p.suffix:
        p = TIMESTAMP / f"{pid_or_path}_timestamps.csv"
    return bersihkan_timestamp(pd.read_csv(p), str(p))


def bersihkan_timestamp(df, sumber="timestamp"):
    df = df.copy()
    df["label"] = df["label"].astype(str).str.strip().str.upper()
    df["waktu_detik"] = pd.to_numeric(df["waktu_detik"], errors="raise").astype(float)
    if "urutan" not in df:
        df["urutan"] = np.arange(1, len(df) + 1)
    df = df.sort_values("urutan").reset_index(drop=True)
    if not df.waktu_detik.is_monotonic_increasing:
        raise ValueError(f"{sumber}: waktu_detik tidak naik sesuai urutan")
    tak_dikenal = set(df.label) - set(GERAKAN) - {"T", "B", "TT"}
    if tak_dikenal:
        raise ValueError(f"{sumber}: label tidak dikenal {sorted(tak_dikenal)}")
    return df[["urutan", "waktu_detik", "label"]]
