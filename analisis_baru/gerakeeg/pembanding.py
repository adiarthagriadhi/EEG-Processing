"""Jendela observasi versi analisis repo (eegpipe v2: fase dari video/pose, offset sinkronisasi repo, batas
dipangkas 0,25 dtk) — HANYA sebagai pembanding. Dibaca dari hasil_analisis/per_partisipan/PXX/."""
import numpy as np
import pandas as pd
import yaml

from .data import ROOT
from .istilah import ISTIRAHAT

REPO = ROOT / "hasil_analisis" / "per_partisipan"
NAMA = {"NGEED": "Ngeed", "AGEM KANAN": "Agem Kanan", "AGEM KIRI": "Agem Kiri"}
KOLOM = {"Gerak": ("act_turun", "act_tahan"), "Tahan": ("act_tahan", "act_naik"), "Naik": ("act_naik", "act_end")}


def offset_repo(pid):
    s = yaml.safe_load((REPO / pid / "keputusan.yaml").read_text())["sync"]
    return s.get("offset_blocks", s["offset_sec"])


def ke_eeg(t, off):
    if np.isscalar(off):
        return t + off
    o = off[0][1]
    for mulai, v in off:
        if t >= mulai:
            o = v
    return t + o


def repetisi_repo(pid):
    r = pd.read_csv(REPO / pid / "reps.csv")
    off = offset_repo(pid)
    r = r[r.get("reclass", pd.Series("", index=r.index)).fillna("") != "tanpa_turun"].copy()
    r["gerakan"] = r.task.map(NAMA)
    for c in ("act_arm", "act_turun", "act_tahan", "act_naik", "act_end"):
        r[c + "_eeg"] = [ke_eeg(t, off) if np.isfinite(t) else np.nan for t in r[c]]
    return r


def jendela_repo(pid, W_baru, trim=0.25, trim_frac=0.15, min_dtk=0.3):
    r = repetisi_repo(pid)
    W = []
    for _, m in r.iterrows():
        for f, (c0, c1) in KOLOM.items():
            a, b = m[c0 + "_eeg"], m[c1 + "_eeg"]
            if not np.isfinite([a, b]).all() or b <= a:
                continue
            tr = min(trim, trim_frac * (b - a))
            if b - a - 2 * tr < min_dtk:
                continue
            W.append(dict(gerakan=m.gerakan, rep=m.rep, blok=0, fase=f, onset=a, mulai=a + tr, selesai=b - tr,
                          durasi_fase=b - a))
    W = pd.DataFrame(W)
    return pd.concat([W, W_baru[W_baru.fase == ISTIRAHAT]], ignore_index=True)   # acuan spektrum yang sama


def selisih_onset(pid, rep_baru):
    """Onset fase: timestamp manual (detik EEG) − repo (video/pose + offset repo), per repetisi."""
    r = repetisi_repo(pid)
    m = rep_baru.merge(r, on=["gerakan", "rep"], how="inner")
    out = m[["gerakan", "rep"]].copy()
    out.insert(0, "participant_id", pid)
    out["selisih_Gerak_vs_lengan"] = m["onset_Gerak"] - m["act_arm_eeg"]      # repo: onset lengan (gerak pertama)
    for f, c in (("Gerak", "act_turun"), ("Tahan", "act_tahan"), ("Naik", "act_naik"), ("Berdiri", "act_end")):
        out[f"selisih_{f}"] = m[f"onset_{f}"] - m[c + "_eeg"]
    return out
