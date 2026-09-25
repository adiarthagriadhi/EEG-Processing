"""Ubah timestamp video manual → timeline.csv + reps.csv format eegpipe.

Sumber: data/manual_timestamps/PXX_fase_gerakan.csv
Pemetaan: Ngeed/AKA/AKI=TURUN, Tahan=TAHAN, Naik=NAIK, Berdiri=END,
Tutup Mata=BERDIRI MATA TERTUTUP. Jeda sesi=ISTIRAHAT UTAMA.
Offset EEG default 0. act_* = onset asli; win_* = onset minus overlap.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TASK = {"NTNB": "NGEED", "AKA TNB": "AGEM KANAN", "AKI TNB": "AGEM KIRI"}


def manual_path(P) -> Path:
    root = P.cfg["_root"]
    d = root / P.cfg.get("paths", {}).get("manual_timestamps", "data/manual_timestamps")
    return d / f"{P.pid}_fase_gerakan.csv"


def exists(P) -> bool:
    return manual_path(P).exists()


def _overlap(cfg, fase: str) -> float:
    mt = cfg.get("manual_timestamps", {})
    if fase == "Naik":
        return float(mt.get("overlap_naik_pre_sec", 0.5))
    return float(mt.get("overlap_pre_sec", 1.0))


def load_fase(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["waktu_detik"] = pd.to_numeric(df["waktu_detik"], errors="coerce")
    df["nama_fase"] = df["nama_fase"].astype(str).str.strip()
    df["kode_paket"] = df["kode_paket"].astype(str).str.strip()
    return df


def timeline_from_fase(df: pd.DataFrame, eeg_dur: float | None = None) -> pd.DataFrame:
    rows = []
    moves = df[df.kode_paket != "TT"].copy()
    for (sesi, paket), g in moves.groupby(["sesi", "paket_ke"], sort=True):
        g = g.sort_values("fase_ke")
        task = TASK[g.kode_paket.iloc[0]]
        times = {r.nama_fase: float(r.waktu_detik) for _, r in g.iterrows()}
        order = []
        if "Ngeed" in times or "Agem Kanan" in times or "Agem Kiri" in times:
            t0 = times.get("Ngeed") or times.get("Agem Kanan") or times.get("Agem Kiri")
            order.append(("TURUN", t0))
        if "Tahan" in times:
            order.append(("TAHAN", times["Tahan"]))
        if "Naik" in times:
            order.append(("NAIK", times["Naik"]))
        if "Berdiri" in times:
            order.append(("END", times["Berdiri"]))
        for i, (sub, t0) in enumerate(order):
            t1 = order[i + 1][1] if i + 1 < len(order) else t0 + 3.0
            if sub == "END":
                continue
            rows.append(dict(task=task, subphase=sub, start=t0, end=t1,
                             n=1, rep=int(paket), sesi=int(sesi)))
    by_sesi = moves.groupby("sesi").waktu_detik.agg(["min", "max"])
    if len(by_sesi) >= 2:
        s1_end = float(by_sesi.loc[1, "max"])
        s2_start = float(by_sesi.loc[2, "min"])
        if s2_start - s1_end > 30:
            rows.append(dict(task="ISTIRAHAT UTAMA", subphase=None,
                             start=s1_end + 8, end=s2_start - 8,
                             n=1, rep=float("nan"), sesi=float("nan")))
            rows.append(dict(task="BERDIRI RILEKS", subphase=None,
                             start=s1_end + 8, end=s2_start - 8,
                             n=1, rep=float("nan"), sesi=float("nan")))
    tt = df[df.kode_paket == "TT"]
    if len(tt):
        t0 = float(tt.waktu_detik.iloc[0])
        t1 = eeg_dur if eeg_dur else t0 + 20
        rows.append(dict(task="BERDIRI MATA TERTUTUP", subphase=None,
                         start=t0, end=min(t0 + 30, t1), n=1, rep=float("nan"),
                         sesi=int(tt.sesi.iloc[0])))
    return pd.DataFrame(rows)


def reps_from_fase(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    moves = df[df.kode_paket != "TT"].copy()
    counters = {}
    for (sesi, paket), g in moves.groupby(["sesi", "paket_ke"], sort=True):
        g = g.sort_values("fase_ke")
        task = TASK[g.kode_paket.iloc[0]]
        counters[task] = counters.get(task, 0) + 1
        times = {r.nama_fase: float(r.waktu_detik) for _, r in g.iterrows()}
        turun = times.get("Ngeed") or times.get("Agem Kanan") or times.get("Agem Kiri")
        tahan, naik, end = times.get("Tahan"), times.get("Naik"), times.get("Berdiri")
        if any(v is None for v in (turun, tahan, naik, end)):
            continue
        ov_t, ov_n, ov_u = _overlap(cfg, "Tahan"), _overlap(cfg, "Naik"), _overlap(cfg, "Ngeed")
        rows.append(dict(
            task=task, rep=int(counters[task]), sesi=int(sesi), paket_ke=int(paket),
            kode_paket=g.kode_paket.iloc[0],
            hud_turun=turun, hud_tahan=tahan, hud_naik=naik, hud_end=end,
            ocr_protocol_dev=0.0,
            act_turun=turun, act_tahan=tahan, act_naik=naik, act_end=end,
            act_turun_extrap=turun, act_arm=turun, first_move="manual",
            win_turun=turun - ov_u, win_tahan=tahan - ov_t,
            win_naik=naik - ov_n, win_end=end,
            depth_px=float("nan"), track_noise_px=0.0, pose_valid_frac=1.0,
            baseline_range_frac=0.0, baseline_still=True,
            compliance="ok", phase_source="manual_video", fallback_latency_sec=0.0,
        ))
    return pd.DataFrame(rows)


def dummy_pose(t_end: float = 430.0, fs: float = 15.0) -> dict:
    t = np.arange(0, t_end, 1 / fs)
    y = np.full_like(t, np.nan, dtype=float)
    return dict(t=t, trunk_y=y, hip_y=y, select_mode=np.array("manual"))


def ingest(P, cfg, eeg_dur: float | None = None, write: bool = True):
    path = manual_path(P)
    if not path.exists():
        raise FileNotFoundError(path)
    df = load_fase(path)
    tl = timeline_from_fase(df, eeg_dur)
    reps = reps_from_fase(df, cfg)
    pose = dummy_pose((eeg_dur or 430.0) + 2)
    if write:
        P.out("timeline.csv").parent.mkdir(parents=True, exist_ok=True)
        tl.to_csv(P.out("timeline.csv"), index=False)
        reps.to_csv(P.out("reps.csv"), index=False)
        np.savez(P.out("pose.npz"), **pose)
        P.out("sync.json").write_text(
            '{"offset_sec": 0.0, "method": "manual", "r_coarse": 1.0,'
            ' "spread_sec": 0.0, "n_rep": %d, "problems": [], "warnings": []}\n' % len(reps)
        )
        dec = P.decisions()
        dec["sync"] = dict(
            offset_sec=0.0, method="manual", accepted=True,
            basis="timestamp video manual; start bersama (uji RMS P08/P09)",
        )
        dec["phase_source"] = "manual_video"
        P.save_decisions(dec)
    return tl, reps, pose
