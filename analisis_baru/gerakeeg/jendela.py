"""Timestamp → repetisi (onset fase) → jendela observasi per fase.

Aturan (keputusan pengguna 2026-09-25):
- Waktu timestamp = waktu EEG (offset 0).
- Label berurutan per repetisi: N/AKA/AKI (Gerak) → T (Tahan) → N (Naik) → B (Berdiri). BM = Buka Mata (Romberg mata
  terbuka, opsional), TT = Tutup Mata.
- Jendela observasi fase = [onset fase − 0,5 dtk, onset fase berikutnya]. Durasi fase = onset berikut − onset.
- Berdiri berakhir pada onset Gerak berikutnya, paling lama 8 dtk sesudah B (akhir blok / sebelum Tutup Mata).
- Buka Mata: BM = label `BM` bila ada, bila tidak BM = TT − 45 dtk (protokol tetap, konfirmasi pengguna 2026-09-25).
  Jendela observasi [BM − 0,5, min(BM + 30, TT)]; analisis mulai maks(BM + 1, B terakhir + 8 dtk) karena TT − 45 jatuh
  0,1–2,3 dtk SEBELUM B terakhir (gerak terakhir belum selesai) dan agar tidak memakai ulang jendela Berdiri terakhir.
- Tutup Mata = [TT − 0,5, TT + 30].
- Istirahat (turunan, tanpa timestamp) = jeda panjang antar-blok: [B terakhir blok 1 + 8, Gerak pertama blok 2 − 5];
  dipakai hanya sebagai acuan kualitas (power 1–4 Hz dan 20–34 Hz).
- Repetisi dinomori per gerakan menurut blok protokol: blok 1 = rep 1–2, blok 2 = rep 3–4.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .istilah import BUKA_MATA, FASE_REPETISI, GERAKAN, ISTIRAHAT, TUTUP_MATA


@dataclass
class Aturan:
    maju_dtk: float = 0.5          # jendela dimulai sekian detik sebelum onset
    berdiri_maks_dtk: float = 8.0  # Berdiri paling lama sesudah B (protokol BERDIRI RILEKS 8 dtk)
    tutup_mata_dtk: float = 30.0
    bm_sebelum_tt_dtk: float = 45.0   # BM = TT − 45 dtk bila label BM tidak ada (buka mata 30 + istirahat 15 dtk)
    jeda_blok_dtk: float = 60.0    # jeda > ini = pergantian blok (istirahat utama)
    istirahat_awal_dtk: float = 8.0
    istirahat_akhir_dtk: float = 5.0


BERIKUT = {"Gerak": "T", "Tahan": "N", "Naik": "B"}


def repetisi(ts, aturan=Aturan()):
    """→ (DataFrame repetisi: onset tiap fase, blok, rep, lengkap; onset Tutup Mata; daftar masalah).
    Onset Buka Mata (label BM) disimpan di rep.attrs["BM"]."""
    rows, masalah, cur, tt, bm = [], [], None, None, None
    for r in ts.itertuples():
        lab, t = r.label, r.waktu_detik
        if lab == "TT":
            tt = t
            continue
        if lab == "BM":
            bm = t
            continue
        if cur is not None and cur["_fase"] in BERIKUT and lab == BERIKUT[cur["_fase"]]:
            nxt = {"Gerak": "Tahan", "Tahan": "Naik", "Naik": "Berdiri"}[cur["_fase"]]
            cur[f"onset_{nxt}"], cur["_fase"] = t, nxt
            continue
        if lab in GERAKAN:
            if cur is not None and cur["_fase"] != "Berdiri":
                masalah.append(f"{cur['gerakan']} mulai {cur['onset_Gerak']:.3f} dtk berhenti di fase {cur['_fase']}")
            cur = dict(gerakan=GERAKAN[lab], urutan=r.urutan, onset_Gerak=t, onset_Tahan=np.nan,
                       onset_Naik=np.nan, onset_Berdiri=np.nan, _fase="Gerak",
                       nilai=getattr(r, "nilai", np.nan))
            rows.append(cur)
            continue
        masalah.append(f"urutan {r.urutan}: label {lab} ({t:.3f} dtk) tidak sesuai urutan Gerak → T → N → B")
    if cur is not None and cur["_fase"] != "Berdiri":
        masalah.append(f"{cur['gerakan']} mulai {cur['onset_Gerak']:.3f} dtk berhenti di fase {cur['_fase']}")
    rep = pd.DataFrame(rows).drop(columns="_fase")
    akhir = rep[[f"onset_{f}" for f in FASE_REPETISI]].max(axis=1)
    rep["blok"] = 1 + np.r_[0, np.cumsum(rep.onset_Gerak.values[1:] - akhir.values[:-1] > aturan.jeda_blok_dtk)]
    rep["rep"] = rep.groupby(["gerakan", "blok"]).cumcount() + 1 + 2 * (rep.blok - 1)
    rep["lengkap"] = rep[[f"onset_{f}" for f in FASE_REPETISI]].notna().all(axis=1)
    for a, b in zip(FASE_REPETISI[:-1], FASE_REPETISI[1:]):
        rep[f"durasi_{a}"] = rep[f"onset_{b}"] - rep[f"onset_{a}"]
    nxt = rep.onset_Gerak.shift(-1)
    same = rep.blok.shift(-1) == rep.blok
    rep["durasi_Berdiri"] = np.where(same, nxt - rep.onset_Berdiri, np.nan)   # hanya bila repetisi berikut ada di blok sama
    if bm is not None and tt is not None and bm >= tt:
        masalah.append(f"BM ({bm:.3f} dtk) tidak sebelum TT ({tt:.3f} dtk)")
    rep.attrs["BM_sumber"] = "label BM" if bm is not None else None
    if bm is None and tt is not None:
        bm = tt - aturan.bm_sebelum_tt_dtk
        rep.attrs["BM_sumber"] = f"TT − {aturan.bm_sebelum_tt_dtk:g} dtk (tetap)"
    rep.attrs["BM"] = bm
    return rep, tt, masalah


def jendela(rep, tt, aturan=Aturan()):
    """→ DataFrame jendela observasi: gerakan, rep, blok, fase, mulai, selesai, onset, durasi_fase."""
    W = []
    starts = rep.onset_Gerak.values
    for _, m in rep.iterrows():
        on = [m[f"onset_{f}"] for f in FASE_REPETISI]
        for i, f in enumerate(FASE_REPETISI):
            if not np.isfinite(on[i]):
                continue
            if f == "Berdiri":
                nxt = starts[starts > on[i]]
                b = min(nxt[0] if len(nxt) else np.inf, on[i] + aturan.berdiri_maks_dtk)
            else:
                b = on[i + 1]
            if not np.isfinite(b) or b <= on[i]:
                continue
            W.append(dict(gerakan=m.gerakan, rep=m.rep, blok=m.blok, fase=f, onset=on[i],
                          mulai=on[i] - aturan.maju_dtk, selesai=b, durasi_fase=b - on[i]))
    bm = rep.attrs.get("BM")
    if bm is not None:
        akhir = bm + aturan.tutup_mata_dtk if tt is None or tt <= bm else min(bm + aturan.tutup_mata_dtk, tt)
        b_akhir = rep.onset_Berdiri.max()
        mulai_an = max(bm + 1.0, b_akhir + aturan.berdiri_maks_dtk) if np.isfinite(b_akhir) else bm + 1.0
        W.append(dict(gerakan="-", rep=0, blok=0, fase=BUKA_MATA, onset=bm, mulai=bm - aturan.maju_dtk,
                      selesai=akhir, durasi_fase=akhir - bm, mulai_analisis=mulai_an))
    if tt is not None:
        W.append(dict(gerakan="-", rep=0, blok=0, fase=TUTUP_MATA, onset=tt, mulai=tt - aturan.maju_dtk,
                      selesai=tt + aturan.tutup_mata_dtk, durasi_fase=aturan.tutup_mata_dtk))
    for b in sorted(rep.blok.unique())[:-1]:
        a = rep[rep.blok == b].onset_Berdiri.max() + aturan.istirahat_awal_dtk
        z = rep[rep.blok == b + 1].onset_Gerak.min() - aturan.istirahat_akhir_dtk
        if z - a > 20:
            W.append(dict(gerakan="-", rep=0, blok=b, fase=ISTIRAHAT, onset=a, mulai=a, selesai=z, durasi_fase=z - a))
    return pd.DataFrame(W)
