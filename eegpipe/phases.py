"""Fase gerak aktual (TURUN/TAHAN/NAIK) dari lintasan vertikal batang tubuh (Tahap 4.1).
Diuji pada spektrum/lintasan sintetis: galat onset ≈ 0,03–0,06 dtk (EEG_PROCESSING.md 9.1)."""
import numpy as np
import pandas as pd
from scipy.ndimage import median_filter

PHASE_COLS = ["act_turun", "act_tahan", "act_naik", "act_end"]


def first_run(mask, start=0, min_len=6):
    """Indeks awal run True pertama (≥ min_len sampel berturut-turut) mulai dari `start`."""
    run = 0
    for i in range(start, len(mask)):
        run = run + 1 if mask[i] else 0
        if run >= min_len:
            return i - min_len + 1
    return None


def _normalize(t, y, smooth_sec):
    fps = 1 / np.median(np.diff(t))
    y = median_filter(y, size=max(3, int(smooth_sec * fps) | 1), mode="nearest")
    stand, low = np.percentile(y, 5), np.percentile(y, 95)
    return (y - stand) / (low - stand) if low > stand else y * 0, low - stand, fps


def segment_phases(t, y, lo=0.1, hi=0.9, smooth_sec=0.3, min_run_sec=0.2, min_depth_px=15):
    """t: waktu video (PTS); y: posisi vertikal batang tubuh (piksel, besar = bawah).
    Fase dari persilangan 10%/90% kedalaman gerak."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(y)
    nan = dict(act_turun=np.nan, act_tahan=np.nan, act_naik=np.nan, act_end=np.nan,
               depth_px=np.nan)
    if ok.sum() < 10:
        return nan
    t, y = t[ok], y[ok]
    z, depth, fps = _normalize(t, y, smooth_sec)
    nan["depth_px"] = depth
    if depth < min_depth_px:
        return nan
    n = max(2, int(min_run_sec * fps))
    # Onset TURUN = saat TERAKHIR di bawah 10% sebelum tubuh mencapai 90%. Persilangan 10%
    # PERTAMA keliru bila ada gerak persiapan kecil (lengan agem menggeser bahu; P02 AGEM
    # KANAN rep1–2 terdeteksi 1–2 dtk terlalu awal).
    i_tahan = first_run(z > hi, 0, n)
    i_turun = None
    if i_tahan is not None:
        below = np.where(z[:i_tahan] <= lo)[0]
        i_turun = int(below[-1]) + 1 if len(below) else None
    if i_turun is None:
        i_tahan = None
    i_naik = first_run(z < hi, i_tahan, n) if i_tahan is not None else None
    i_end = first_run(z < lo, i_naik, n) if i_naik is not None else None
    pick = lambda i: t[i] if i is not None else np.nan
    return dict(act_turun=pick(i_turun), act_tahan=pick(i_tahan), act_naik=pick(i_naik),
                act_end=pick(i_end), depth_px=depth)


def extrapolated_onset(t, y, smooth_sec=0.3):
    """Onset TURUN presisi (untuk LRP): garis 10%→50% diekstrapolasi ke 0%."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(y)
    if ok.sum() < 10:
        return np.nan
    t, y = t[ok], y[ok]
    z, depth, fps = _normalize(t, y, smooth_sec)
    n = max(2, int(0.2 * fps))
    i50 = first_run(z > 0.5, 0, n)
    if i50 is None:
        return np.nan
    below = np.where(z[:i50] <= 0.1)[0]           # 10% terakhir sebelum 50% (lihat di atas)
    if not len(below):
        return np.nan
    i10 = int(below[-1]) + 1
    return t[i10] - 0.1 * (t[i50] - t[i10]) / 0.4


def compliance(row, late_sec=1.5, short_hold_sec=1.0):
    acts = [row[c] for c in PHASE_COLS]
    if np.isnan(row["depth_px"]) or not np.isfinite(acts).all():
        return "incomplete" if np.isfinite(row["depth_px"]) else "no_video"
    if not np.all(np.diff(acts) > 0):
        return "incomplete"
    if row["act_naik"] - row["act_tahan"] < short_hold_sec:
        return "short_hold"
    if row["act_turun"] - row["hud_turun"] > late_sec:
        return "late"
    return "ok"


def detect_reps(timeline, pose_t, pose_y, cfg):
    """Satu baris per repetisi gerakan: onset HUD, fase aktual, kepatuhan.
    Waktu dalam detik VIDEO (dikonversi ke EEG di tahap epoching)."""
    pc = cfg["phases"]
    moves = timeline[timeline.subphase.notna()]
    rows = []
    proto = pc["hud_protocol"]
    for (task, rep), g in moves.groupby(["task", "rep"], sort=False):
        g = g.groupby("subphase").agg(start=("start", "min"), end=("end", "max"))
        if "TURUN" not in g.index:
            continue
        hud_turun = g.start["TURUN"]
        hud = {k: hud_turun + v for k, v in proto.items()}
        # cek OCR vs protokol (selisih > 0,5 dtk → ditandai untuk ditinjau)
        ocr_dev = max(abs(g.start.get(k, np.nan) - hud[k]) for k in ("TAHAN", "NAIK"))
        hud_end = hud["END"]
        w0, w1 = hud_turun - pc["search_before_sec"], hud_end + pc["search_after_sec"]
        m = (pose_t >= w0) & (pose_t <= w1)
        seg = segment_phases(pose_t[m], pose_y[m], min_depth_px=pc["min_depth_px"])
        row = dict(task=task, rep=int(rep), hud_turun=hud_turun, hud_tahan=hud["TAHAN"],
                   hud_naik=hud["NAIK"], hud_end=hud_end, ocr_protocol_dev=ocr_dev, **seg,
                   act_turun_extrap=extrapolated_onset(pose_t[m], pose_y[m]),
                   pose_valid_frac=float(np.isfinite(pose_y[m]).mean()) if m.any() else 0.0)
        row["compliance"] = compliance(row, pc["late_sec"], pc["short_hold_sec"])
        # jendela baseline ERD (relatif onset aktual) harus diam: rentang posisi batang tubuh
        # (dihaluskan 0,3 dtk) < baseline_max_frac × kedalaman gerak. Kecepatan mentah tidak
        # dipakai karena jitter pose saja sudah 30–45 px/dtk (P02).
        b0, b1 = cfg["erd"]["baseline"]
        row["baseline_range_frac"], row["baseline_still"] = np.nan, False
        if np.isfinite(row["act_turun"]) and np.isfinite(row["depth_px"]):
            mb = (pose_t >= row["act_turun"] + b0) & (pose_t <= row["act_turun"] + b1)
            yb = pose_y[mb]
            yb = yb[np.isfinite(yb)]
            if len(yb) > 5:
                yb = median_filter(yb, size=9, mode="nearest")
                frac = float((yb.max() - yb.min()) / row["depth_px"])
                row["baseline_range_frac"] = frac
                row["baseline_still"] = frac <= pc["baseline_max_frac"]
        rows.append(row)
    return pd.DataFrame(rows)
