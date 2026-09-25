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


def _normalize(t, y, smooth_sec, stand_until=None, low_pct=90):
    fps = 1 / np.median(np.diff(t))
    y = median_filter(y, size=max(3, int(smooth_sec * fps) | 1), mode="nearest")
    # level berdiri = median sebelum instruksi (bila diberikan); persentil-5 keliru bila
    # posisi setelah NAIK sedikit lebih tinggi dari awal (P10 NGEED rep2)
    pre = y[t <= stand_until] if stand_until is not None else []
    stand = np.median(pre) if len(pre) >= 5 else np.percentile(y, 5)
    low = np.percentile(y, low_pct)
    return (y - stand) / (low - stand) if low > stand else y * 0, low - stand, fps


def segment_phases(t, y, lo=0.1, hi=0.9, smooth_sec=0.5, min_run_sec=0.2, min_depth_px=15,
                   stand_until=None):
    """Level terendah = persentil-90 dan penghalusan 0,5 dtk: lonjakan pelacakan pada agem
    (P10) membuat persentil-95 berada di bawah plato sehingga TAHAN terpotong. P02 tidak
    berubah (12/12 ok)."""
    """t: waktu video (PTS); y: posisi vertikal batang tubuh (piksel, besar = bawah).
    Fase dari persilangan 10%/90% kedalaman gerak."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(y)
    nan = dict(act_turun=np.nan, act_tahan=np.nan, act_naik=np.nan, act_end=np.nan,
               depth_px=np.nan)
    if ok.sum() < 10:
        return nan
    t, y = t[ok], y[ok]
    z, depth, fps = _normalize(t, y, smooth_sec, stand_until)
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


def extrapolated_onset(t, y, smooth_sec=0.5, stand_until=None):
    """Onset TURUN presisi (untuk LRP): garis 10%→50% diekstrapolasi ke 0%."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(y)
    if ok.sum() < 10:
        return np.nan
    t, y = t[ok], y[ok]
    z, depth, fps = _normalize(t, y, smooth_sec, stand_until)
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


def detect_reps(timeline, pose_t, pose_y, cfg, wrists=None, confirmed=()):
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
        seg = segment_phases(pose_t[m], pose_y[m], min_depth_px=pc["min_depth_px"],
                             stand_until=hud_turun)
        yy = pose_y[m][np.isfinite(pose_y[m])]
        track_noise = float(np.median(np.abs(np.diff(yy)))) if len(yy) > 5 else np.nan
        row = dict(task=task, rep=int(rep), hud_turun=hud_turun, hud_tahan=hud["TAHAN"],
                   hud_naik=hud["NAIK"], hud_end=hud_end, ocr_protocol_dev=ocr_dev, **seg,
                   act_turun_extrap=extrapolated_onset(pose_t[m], pose_y[m], stand_until=hud_turun),
                   track_noise_px=track_noise,
                   pose_valid_frac=float(np.isfinite(pose_y[m]).mean()) if m.any() else 0.0)
        row["compliance"] = compliance(row, pc["late_sec"], pc["short_hold_sec"])
        row["phase_source"] = "video"
        # Percobaan ulang (2026-09-25): repetisi incomplete → ambang lo/hi longgar + jendela diperpanjang;
        # batas kedalaman diturunkan hanya untuk repetisi yang dikonfirmasi peneliti "turun" (tinjauan manual).
        rx = pc.get("relaxed")
        if rx and row["compliance"] == "incomplete":
            m2 = (pose_t >= w0) & (pose_t <= hud_end + rx["search_after_sec"])
            dmin = rx["min_depth_px_confirmed"] if (task, int(rep)) in confirmed else pc["min_depth_px"]
            seg2 = segment_phases(pose_t[m2], pose_y[m2], lo=rx["lo"], hi=rx["hi"], min_depth_px=dmin,
                                  stand_until=hud_turun)
            r2 = {**row, **seg2}
            c2 = compliance(r2, pc["late_sec"], pc["short_hold_sec"])
            if c2 != "incomplete" and np.isfinite(seg2["depth_px"]):
                row.update(seg2, compliance=c2, phase_source="video_longgar")
        # gerak lengan pertama: 8 dtk sebelum instruksi s.d. onset batang tubuh
        a = arm_onset(pose_t, wrists, hud_turun - pc["arm_search_sec"],
                      row["act_turun"] if np.isfinite(row["act_turun"]) else hud_turun + 3)
        row["act_arm"] = min(a, row["act_turun"]) if np.isfinite(a) else row["act_turun"]
        row["first_move"] = "lengan" if np.isfinite(a) and a < row["act_turun"] else "batang_tubuh"
        # jendela baseline ERD (relatif onset aktual) harus diam: rentang posisi batang tubuh
        # (dihaluskan 0,3 dtk) < baseline_max_frac × kedalaman gerak. Kecepatan mentah tidak
        # dipakai karena jitter pose saja sudah 30–45 px/dtk (P02).
        b0, b1 = cfg["erd"]["baseline"]
        row["baseline_range_frac"], row["baseline_still"] = np.nan, False
        if np.isfinite(row.get("act_arm", np.nan)) and np.isfinite(row["depth_px"]):
            mb = (pose_t >= row["act_arm"] + b0) & (pose_t <= row["act_arm"] + b1)
            yb = pose_y[mb]
            yb = yb[np.isfinite(yb)]
            if len(yb) > 5:
                yb = median_filter(yb, size=9, mode="nearest")
                frac = float((yb.max() - yb.min()) / row["depth_px"])
                row["baseline_range_frac"] = frac
                row["baseline_still"] = frac <= pc["baseline_max_frac"]
        rows.append(row)
    df = pd.DataFrame(rows)
    return hud_fallback(df, pc)


def hud_fallback(df, pc):
    """Repetisi dengan pelacakan pose tidak andal (track_noise > batas; P10: pengamat
    duduk tepat di belakang partisipan → MediaPipe menggabungkan dua orang saat agem)
    diberi fase dari PROTOKOL HUD digeser latensi median partisipan (dari repetisi yang
    bersih). Ditandai phase_source='hud_fallback' agar bisa dikecualikan di analisis."""
    if "phase_source" not in df:
        df["phase_source"] = "video"
    good = df.compliance.isin(["ok", "late"]) & (df.track_noise_px <= pc["max_track_noise_px"])
    lat = float((df.act_turun - df.hud_turun)[good].median()) if good.any() else pc["default_latency_sec"]
    bad = df.track_noise_px > pc["max_track_noise_px"]
    df.loc[bad, "act_arm"] = df.loc[bad, "hud_turun"] + lat
    for c, h in [("act_turun", "hud_turun"), ("act_tahan", "hud_tahan"),
                 ("act_naik", "hud_naik"), ("act_end", "hud_end")]:
        df.loc[bad, c] = df.loc[bad, h] + lat
    df.loc[bad, "act_turun_extrap"] = np.nan
    df.loc[bad, "compliance"] = "hud_fallback"
    df.loc[bad, "phase_source"] = "hud_fallback"
    df["fallback_latency_sec"] = lat
    return df


def arm_onset(t, wrists, t_search0, t_search1, min_px=15.0, k_mad=5.0, run_sec=0.2):
    """Gerak PERTAMA lengan (pergelangan kiri/kanan) dalam [t_search0, t_search1].
    Referensi diam = median posisi pada 2 dtk pertama jendela; onset = awal run ≥ run_sec
    dengan jarak > max(min_px, k_mad × MAD). Dipakai untuk mengunci fase PRA (bukan
    batang tubuh: lengan agem bergerak lebih dulu)."""
    m = (t >= t_search0) & (t <= t_search1)
    if m.sum() < 10 or wrists is None:
        return np.nan
    tt, w = t[m], wrists[m]
    fps = 1 / np.median(np.diff(tt))
    w = median_filter(np.nan_to_num(w, nan=np.nanmedian(w, axis=0)), size=(5, 1), mode="nearest")
    ref = tt <= tt[0] + 2.0
    d = np.max([np.hypot(w[:, 0] - np.median(w[ref, 0]), w[:, 1] - np.median(w[ref, 1])),
                np.hypot(w[:, 2] - np.median(w[ref, 2]), w[:, 3] - np.median(w[ref, 3]))], axis=0)
    thr = max(min_px, k_mad * 1.4826 * np.median(np.abs(d[ref] - np.median(d[ref]))))
    i = first_run(d > thr, int(ref.sum()), max(2, int(run_sec * fps)))
    return float(tt[i]) if i is not None else np.nan
