"""Sinkronisasi EEG↔video (Tahap 2): korelasi silang energi gerak video (area partisipan)
dengan envelope artefak gerak/otot EEG. t_eeg = t_video + offset."""
import numpy as np
import pandas as pd
from scipy.signal import correlate, correlation_lags


def to_grid(t, x, fs, t_end=None):
    t, x = np.asarray(t, float), np.asarray(x, float)
    ok = np.isfinite(x)
    grid = np.arange(0, (t_end if t_end is not None else t[ok][-1]), 1 / fs)
    return grid, np.interp(grid, t[ok], x[ok])


def eeg_envelope(raw, band, channels, fs):
    env = (raw.copy().pick(channels).filter(*band, verbose="error")
           .apply_hilbert(envelope=True).get_data().mean(axis=0))
    return to_grid(raw.times, env, fs)


def eeg_motion(raw, cfg):
    sc = cfg["sync"]
    return eeg_envelope(raw, sc["eeg_motion_band"], sc["eeg_motion_channels"], sc["fs"])


def pose_speed(pose):
    """Kecepatan batang tubuh (piksel/dtk) dari lintasan pose; celah diinterpolasi."""
    from scipy.ndimage import median_filter
    t = pose["t"]
    y = pd.Series(pose["trunk_y"]).interpolate(limit_direction="both").to_numpy()
    x = pd.Series(pose["x"]).interpolate(limit_direction="both").to_numpy()
    y, x = median_filter(y, 5), median_filter(x, 5)
    return t, np.hypot(np.gradient(y, t), np.gradient(x, t)), np.abs(np.gradient(y, t))


def xcorr_offset(v, e, fs, max_lag_sec):
    """Lag (dtk) yang memaksimalkan korelasi; positif = kejadian muncul lebih akhir di EEG."""
    z = lambda x: (x - x.mean()) / x.std()
    v, e = z(np.log1p(v)), z(np.log1p(e))
    cc = correlate(e, v, mode="full") / min(len(v), len(e))
    lags = correlation_lags(len(e), len(v), mode="full") / fs
    ok = np.abs(lags) <= max_lag_sec
    i = np.argmax(cc[ok])
    return float(lags[ok][i]), float(cc[ok][i]), lags[ok], cc[ok]


def coverage(onset_video, dur, offset, eeg_dur):
    """Fraksi segmen (waktu video) yang berada di dalam rekaman EEG."""
    a, b = onset_video + offset, onset_video + offset + dur
    inside = max(0.0, min(b, eeg_dur) - max(a, 0.0))
    return inside / dur if dur > 0 else 0.0


def hud_boxcar(timeline, t_end, fs):
    """Sinyal 1 selama repetisi gerakan (dari timeline HUD), 0 saat diam."""
    grid = np.arange(0, t_end, 1 / fs)
    box = np.zeros_like(grid)
    for _, r in timeline[timeline.subphase.notna()].iterrows():
        box[(grid >= r.start) & (grid < r.end)] = 1
    return grid, box


def two_stage(timeline, pose, raw, cfg):
    """Kasar: kecepatan tubuh (pose) vs envelope EEG 1–4 Hz (±coarse_lag).
    Halus: kecepatan tubuh (pose) vs envelope artefak EEG, ±fine_lag di sekitar kasar,
    median atas beberapa kombinasi sinyal; sebarannya = ketidakpastian.
    Drift: offset halus per blok gerakan (dipisah ISTIRAHAT UTAMA).
    Hasil P02: semua kombinasi +0,65…+0,95 dtk (EEG_PROCESSING.md 7)."""
    sc = cfg["sync"]
    fs = sc["fs"]
    all_eeg = [c for c in raw.ch_names if c not in cfg["eeg"]["misc_channels"]]
    _, e_coarse = eeg_motion(raw, cfg)
    t, speed, vy = pose_speed(pose)
    videos = {"speed": to_grid(t, speed, fs)[1], "vy": to_grid(t, vy, fs)[1]}
    eegs = {"1-4Hz_all": eeg_envelope(raw, (1, 4), all_eeg, fs)[1],
            "0.5-2Hz_all": eeg_envelope(raw, (0.5, 2), all_eeg, fs)[1],
            "emg": e_coarse}
    # Kasar: kecepatan tubuh (gerak AKTUAL) vs envelope EEG 1–4 Hz, ±coarse_lag.
    # Boxcar HUD saja gagal pada P10 (EEG tanpa perbedaan power antar blok, r 0,09),
    # sedangkan gerak aktual tetap memberi puncak konsisten (+0,8 dtk, r 0,33).
    coarse, r_coarse, lags_c, cc_c = xcorr_offset(videos["speed"], eegs["1-4Hz_all"], fs,
                                                  sc["coarse_lag_sec"])
    far = np.abs(lags_c - coarse) > 3
    r_second = float(cc_c[far].max()) if far.any() else np.nan
    # diagnostik: boxcar HUD (kasar lama = offset + waktu reaksi)
    _, box = hud_boxcar(timeline, pose["t"][-1], fs)
    hud_lag, hud_r, _, _ = xcorr_offset(box + 0.01, e_coarse, fs, sc["coarse_lag_sec"])
    lo, hi = coarse - sc["fine_lag_sec"], coarse + sc["fine_lag_sec"]

    def best(v, e, a=0, b=None):
        b = b or min(len(v), len(e))
        _, _, lags, cc = xcorr_offset(v[a:b], e[a:b], fs, max(abs(lo), abs(hi)))
        m = (lags >= lo) & (lags <= hi)
        i = np.argmax(cc[m])
        return float(lags[m][i]), float(cc[m][i]), lags[m], cc[m]

    combos = {f"{vn}×{en}": best(v, e) for vn, v in videos.items() for en, e in eegs.items()}
    offs = np.array([c[0] for c in combos.values()])
    offset = float(np.median(offs))
    main = combos["speed×1-4Hz_all"]

    # Offset UTAMA = median offset lokal per repetisi (jendela di sekitar tiap TURUN HUD,
    # pencarian ±fine_lag di sekitar median kombinasi); ketidakpastian = SE median.
    # Kombinasi sinyal pada P01/P03/P04 tidak sepakat (IQR 0,5–1,6 dtk) walau 12 repetisi
    # konsisten (SE 0,18–0,23 dtk) → estimator per-repetisi lebih tahan terhadap satu
    # sinyal lemah. Regresi offset vs waktu = drift.
    from scipy import stats
    v, e = videos["speed"], eegs["1-4Hz_all"]
    lv = np.log1p(v)
    turun = timeline[timeline.subphase == "TURUN"].start

    def local(center, half):
        out = []
        for t0 in turun:
            a, b = int((t0 - 3) * fs), int((t0 + 13) * fs)
            cands = []
            for lag in np.arange(center - half, center + half + 1e-9, 1 / fs):
                k = int(round(lag * fs))
                if a + k < 0 or b + k > len(e) or b > len(v):
                    continue
                cands.append((lag, np.corrcoef(lv[a:b], np.log1p(e[a + k:b + k]))[0, 1]))
            if cands:
                lag, r = max(cands, key=lambda c: c[1])
                out.append((float(t0), float(lag), float(r)))
        return np.array(out)

    # Dua langkah: (1) lebar ±fine_lag di sekitar median kombinasi → memastikan LOKASI
    # (menempel batas = puncak kasar salah); (2) sempit ±rep_lag di sekitar median langkah 1
    # → presisi (jendela lebar menambah puncak sekunder: SE 0,28–0,34 vs 0,18–0,23 dtk).
    combo_offset = offset
    rep_se, edge_frac = np.nan, np.nan
    wide = local(combo_offset, sc["fine_lag_sec"])
    pr = wide
    if len(wide) >= 4:
        edge_frac = float(np.mean(np.abs(wide[:, 1] - combo_offset) >= sc["fine_lag_sec"] - 1 / fs))
        pr = local(float(np.median(wide[:, 1])), sc["rep_lag_sec"])
    if len(pr) >= 4:
        offset = float(np.median(pr[:, 1]))
        rep_se = float(1.2533 * pr[:, 1].std(ddof=1) / np.sqrt(len(pr)))
    per_rep = [tuple(x) for x in pr]
    if len(pr) >= 4:
        lr = stats.linregress(pr[:, 0], pr[:, 1])
        span = pr[:, 0].max() - pr[:, 0].min()
        drift, drift_p, rep_sd = float(lr.slope * span), float(lr.pvalue), float(pr[:, 1].std())
    else:
        drift, drift_p, rep_sd = 0.0, 1.0, np.nan
    return dict(offset_sec=round(offset, 2), offset_se_sec=round(rep_se, 3),
                n_rep=len(pr), rep_edge_frac=edge_frac, combo_offset_sec=round(combo_offset, 2),
                method="median_per_rep", coarse_sec=coarse, r_coarse=r_coarse,
                hud_boxcar_lag=hud_lag, hud_boxcar_r=hud_r,
                r_coarse_second=r_second, fine_sec=round(combo_offset - coarse, 2),
                r_fine=main[1], spread_sec=float(np.subtract(*np.percentile(offs, [75, 25]))),
                range_sec=float(offs.max() - offs.min()),
                combos={k: round(v[0], 2) for k, v in combos.items()},
                per_rep=[dict(t=t0, offset=o, r=r) for t0, o, r in per_rep],
                per_rep_sd=rep_sd, drift_sec=round(drift, 2), drift_p=drift_p,
                curves=dict(lags_coarse=lags_c, cc_coarse=cc_c, lags_fine=main[2] - coarse,
                            cc_fine=main[3]))


def qc(res, cfg):
    """Mengembalikan (masalah, peringatan). Masalah = BERHENTI; peringatan = dicatat saja.
    Kriteria utama: offset median per-repetisi dengan SE ≤ max_se_sec dari ≥ min_reps
    repetisi, tidak menempel batas pencarian. Ketidaksepakatan kombinasi sinyal dan puncak
    kasar yang tidak tegas menjadi peringatan bila kriteria utama terpenuhi."""
    sc = cfg["sync"]
    problems, warnings = [], []
    se, n = res.get("offset_se_sec", np.nan), res.get("n_rep", 0)
    if n < sc["min_reps"] or not np.isfinite(se):
        problems.append(f"repetisi terukur terlalu sedikit ({n} < {sc['min_reps']})")
    elif se > sc["max_se_sec"]:
        problems.append(f"offset per-repetisi tidak konsisten (SE {se:.2f} > {sc['max_se_sec']} dtk)")
    if res.get("rep_edge_frac", 0) > 0.25:
        problems.append(f"{res['rep_edge_frac']:.0%} repetisi menempel batas pencarian "
                        "→ puncak kasar kemungkinan salah")
    if abs(res["offset_sec"]) > sc["prior_max_abs_sec"]:
        problems.append(f"|offset| {res['offset_sec']:.1f} dtk > prior hitungan-3 "
                        f"({sc['prior_max_abs_sec']} dtk)")
    if abs(res["drift_sec"]) > sc["max_drift_sec"] and res["drift_p"] < 0.05:
        problems.append(f"drift signifikan {res['drift_sec']:+.2f} dtk sepanjang sesi "
                        f"(p={res['drift_p']:.3f}) → pertimbangkan pemetaan linear")
    if res["r_coarse"] - res["r_coarse_second"] < sc["min_peak_margin"]:
        warnings.append(f"puncak kasar tidak tegas (r {res['r_coarse']:.2f} vs "
                        f"{res['r_coarse_second']:.2f})")
    if res["r_fine"] < sc["min_r_fine"]:
        warnings.append(f"korelasi halus rendah (r {res['r_fine']:.2f})")
    if res["spread_sec"] > sc["max_spread_sec"]:
        warnings.append(f"kombinasi sinyal tidak sepakat (IQR {res['spread_sec']:.2f} dtk)")
    return problems, warnings
