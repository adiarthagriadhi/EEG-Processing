"""Timestamp manual peneliti → timeline.csv + reps.csv format eegpipe (pengganti OCR + pose + sinkronisasi).

Sumber: data/manual_timestamps/PXX_timestamps.csv (kolom: urutan, waktu_detik, label[, nama_video]).
Label per repetisi, berurutan:
    N / AKA / AKI  mulai turun (NGEED / AGEM KANAN / AGEM KIRI)  → act_turun
    T              mulai menahan posisi                            → act_tahan
    N              (sesudah T) mulai naik                          → act_naik
    B              berdiri (gerak selesai)                         → act_end
    TT             mulai tutup mata (Romberg EC)
Waktu = detik EEG, offset EEG↔timestamp tetap (config manual_timestamps.offset_sec, baku 0).
Nomor repetisi mengikuti protokol: blok 1 = rep 1–2, blok 2 (sesudah ISTIRAHAT UTAMA) = rep 3–4, sehingga
blok yang tidak terekam tidak menggeser penomoran.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

START = {"N": "NGEED", "AKA": "AGEM KANAN", "AKI": "AGEM KIRI"}
TRANSITIONS = {"TURUN": "T", "TAHAN": "N", "NAIK": "B"}     # label berikut yang sah per keadaan


def manual_path(P) -> Path:
    d = P.cfg["_root"] / P.cfg["paths"].get("manual_timestamps", "data/manual_timestamps")
    return d / f"{P.pid}_timestamps.csv"


def exists(P) -> bool:
    return P.cfg.get("manual_timestamps", {}).get("enabled", True) and manual_path(P).exists()


def load(path) -> pd.DataFrame:
    return load_df(pd.read_csv(path), path)


def load_df(df: pd.DataFrame, path="timestamp") -> pd.DataFrame:
    df = df.copy()
    df["label"] = df["label"].astype(str).str.strip().str.upper()
    df["waktu_detik"] = pd.to_numeric(df["waktu_detik"], errors="raise")
    df = df.sort_values("urutan" if "urutan" in df else "waktu_detik").reset_index(drop=True)
    if not df.waktu_detik.is_monotonic_increasing:
        raise ValueError(f"{path}: waktu_detik tidak naik berurutan")
    bad = set(df.label) - set(START) - {"T", "B", "TT"}
    if bad:
        raise ValueError(f"{path}: label tidak dikenal {sorted(bad)}")
    return df


def parse(df: pd.DataFrame, block_gap_sec: float = 60.0):
    """→ (reps: list[dict], tt: float|None, problems: list[str]). Mesin keadaan per repetisi."""
    reps, problems, cur, tt = [], [], None, None
    for r in df.itertuples():
        lab, t = r.label, float(r.waktu_detik)
        if lab == "TT":
            tt = t
            continue
        if cur is not None and cur["state"] != "END" and lab == TRANSITIONS[cur["state"]]:
            key = {"TURUN": "act_tahan", "TAHAN": "act_naik", "NAIK": "act_end"}[cur["state"]]
            cur[key] = t
            cur["state"] = {"TURUN": "TAHAN", "TAHAN": "NAIK", "NAIK": "END"}[cur["state"]]
            continue
        if lab in START:
            if cur is not None and cur["state"] != "END":
                problems.append(f"repetisi {cur['task']} mulai {cur['act_turun']:.3f} dtk tidak lengkap "
                                f"(berhenti di {cur['state']})")
            cur = dict(task=START[lab], act_turun=t, act_tahan=np.nan, act_naik=np.nan, act_end=np.nan,
                       state="TURUN", urutan=int(r.urutan) if hasattr(r, "urutan") else r.Index + 1)
            reps.append(cur)
            continue
        problems.append(f"urutan {getattr(r, 'urutan', r.Index + 1)}: label {lab} pada {t:.3f} dtk "
                        f"tidak sesuai urutan N/AKA/AKI → T → N → B")
    if cur is not None and cur["state"] != "END":
        problems.append(f"repetisi {cur['task']} mulai {cur['act_turun']:.3f} dtk tidak lengkap")
    # blok: jeda > block_gap_sec antara akhir repetisi dan awal repetisi berikut = ISTIRAHAT UTAMA
    blk = 1
    for i, m in enumerate(reps):
        if i:
            prev = reps[i - 1]
            prev_t = prev["act_end"] if np.isfinite(prev["act_end"]) else prev["act_turun"]
            if m["act_turun"] - prev_t > block_gap_sec:
                blk += 1
        m["sesi"] = blk
    return reps, tt, problems


def build(df: pd.DataFrame, cfg: dict):
    """→ (timeline, reps, info). Kolom reps sama dengan keluaran tahap `phases` (sumber video)."""
    mt = cfg.get("manual_timestamps", {})
    rows, tt, problems = parse(df, mt.get("block_gap_sec", 60.0))
    for task in START.values():                      # rep 1–2 blok 1, rep 3–4 blok 2
        for blk in (1, 2):
            sel = [m for m in rows if m["task"] == task and m["sesi"] == blk]
            for k, m in enumerate(sel):
                m["rep"] = 2 * (blk - 1) + k + 1
    reps = pd.DataFrame(rows).drop(columns="state")
    ok = reps[["act_turun", "act_tahan", "act_naik", "act_end"]].notna().all(1)
    reps["compliance"] = np.where(ok, "ok", "incomplete")
    reps["act_arm"] = reps.act_turun                 # gerak pertama = onset turun yang ditandai
    reps["act_turun_extrap"] = reps.act_turun
    for c in ("hud_turun", "hud_tahan", "hud_naik", "hud_end"):   # tanpa HUD: latensi instruksi tak terukur
        reps[c] = np.nan
    reps["first_move"] = "manual"
    reps["phase_source"] = "manual_timestamp"
    reps["baseline_still"] = True
    reps = reps[["task", "rep", "sesi", "urutan", "compliance", "act_arm", "act_turun", "act_tahan",
                 "act_naik", "act_end", "act_turun_extrap", "hud_turun", "hud_tahan", "hud_naik",
                 "hud_end", "first_move", "phase_source", "baseline_still"]]

    # timeline (detik EEG): subfase gerak, BERDIRI RILEKS antar-repetisi, ISTIRAHAT UTAMA, Romberg
    br = mt.get("berdiri_start_sec", 2.0)            # sesudah jendela POST (akhir + 0,5…2 dtk)
    br_max = mt.get("berdiri_max_sec", 8.0)          # BERDIRI RILEKS protokol 8 dtk
    lead = mt.get("next_rep_lead_sec", 1.0)          # berhenti 1 dtk sebelum repetisi berikut (PRA 2 dtk)
    tl = []
    starts = reps.act_turun.tolist()
    for i, m in reps.iterrows():
        seq = [("TURUN", m.act_turun, m.act_tahan), ("TAHAN", m.act_tahan, m.act_naik),
               ("NAIK", m.act_naik, m.act_end)]
        for sub, a, b in seq:
            if np.isfinite(a) and np.isfinite(b):
                tl.append(dict(task=m.task, subphase=sub, start=a, end=b, rep=m.rep, sesi=m.sesi))
        if np.isfinite(m.act_end):
            nxt = min([s for s in starts if s > m.act_end], default=np.inf)
            a, b = m.act_end + br, min(m.act_end + br_max, nxt - lead)
            if b - a >= 1.0:
                tl.append(dict(task="BERDIRI RILEKS", subphase=None, start=a, end=b, rep=np.nan, sesi=m.sesi))
    for blk in sorted(reps.sesi.unique())[:-1]:
        end1 = reps[reps.sesi == blk][["act_end", "act_turun"]].max().max()
        start2 = reps[reps.sesi == blk + 1].act_turun.min()
        a, b = end1 + br_max, start2 - mt.get("rest_end_margin_sec", 5.0)   # BERSIAP 5 dtk
        if b - a > 20:
            tl.append(dict(task="ISTIRAHAT UTAMA", subphase=None, start=a, end=b, rep=np.nan, sesi=np.nan))
    if tt is not None:
        ec = mt.get("romberg_sec", 30.0)
        tl.append(dict(task=cfg["romberg"]["labels"]["EC"], subphase=None, start=tt, end=tt + ec,
                       rep=np.nan, sesi=np.nan))
        if mt.get("derive_eo", True):                # EO 30 dtk → BERDIRI ISTIRAHAT 15 dtk → EC (protokol)
            gap = mt.get("eo_gap_sec", 15.0)
            tl.append(dict(task=cfg["romberg"]["labels"]["EO"], subphase=None, start=tt - gap - ec,
                           end=tt - gap, rep=np.nan, sesi=np.nan, source="protokol (TT − 45…TT − 15 dtk)"))
    tl = pd.DataFrame(tl).sort_values("start").reset_index(drop=True)
    info = dict(n_rep=int(len(reps)), n_ok=int(ok.sum()), problems=problems,
                reps_per_task=reps.groupby("task").rep.apply(list).to_dict(),
                romberg_ec_onset=tt)
    return tl, reps, info
