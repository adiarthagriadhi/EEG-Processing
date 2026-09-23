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
    """Kasar: boxcar HUD vs EEG (±coarse_lag; pola blok istirahat 180 dtk mencegah salah
    periode 16 dtk). Hasil kasar = offset + waktu reaksi (gerak mulai ~0,8 dtk setelah HUD).
    Halus: kecepatan tubuh (pose) vs envelope artefak EEG, ±fine_lag di sekitar kasar,
    median atas beberapa kombinasi sinyal; sebarannya = ketidakpastian.
    Drift: offset halus per blok gerakan (dipisah ISTIRAHAT UTAMA).
    Hasil P02: semua kombinasi +0,65…+0,95 dtk (EEG_PROCESSING.md 7)."""
    sc = cfg["sync"]
    fs = sc["fs"]
    all_eeg = [c for c in raw.ch_names if c not in cfg["eeg"]["misc_channels"]]
    _, e_coarse = eeg_motion(raw, cfg)
    _, box = hud_boxcar(timeline, pose["t"][-1], fs)
    coarse, r_coarse, lags_c, cc_c = xcorr_offset(box + 0.01, e_coarse, fs, sc["coarse_lag_sec"])
    far = np.abs(lags_c - coarse) > 3
    r_second = float(cc_c[far].max()) if far.any() else np.nan

    t, speed, vy = pose_speed(pose)
    videos = {"speed": to_grid(t, speed, fs)[1], "vy": to_grid(t, vy, fs)[1]}
    eegs = {"1-4Hz_all": eeg_envelope(raw, (1, 4), all_eeg, fs)[1],
            "0.5-2Hz_all": eeg_envelope(raw, (0.5, 2), all_eeg, fs)[1],
            "emg": e_coarse if sc["fs"] == fs else eeg_motion(raw, cfg)[1]}
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

    # drift: offset lokal per repetisi (jendela di sekitar tiap TURUN HUD), lalu regresi
    # offset vs waktu. P02: SD 0,25 dtk, kemiringan tidak signifikan → offset konstan.
    from scipy import stats
    v, e = videos["speed"], eegs["1-4Hz_all"]
    lv = np.log1p(v)
    per_rep = []
    for t0 in timeline[timeline.subphase == "TURUN"].start:
        a, b = int((t0 - 3) * fs), int((t0 + 13) * fs)
        cands = []
        for lag in np.arange(offset - 1.0, offset + 1.0 + 1e-9, 1 / fs):
            k = int(round(lag * fs))
            if a + k < 0 or b + k > len(e) or b > len(v):
                continue
            cands.append((lag, np.corrcoef(lv[a:b], np.log1p(e[a + k:b + k]))[0, 1]))
        if cands:
            lag, r = max(cands, key=lambda c: c[1])
            per_rep.append((float(t0), float(lag), float(r)))
    pr = np.array(per_rep)
    if len(pr) >= 4:
        lr = stats.linregress(pr[:, 0], pr[:, 1])
        span = pr[:, 0].max() - pr[:, 0].min()
        drift, drift_p, rep_sd = float(lr.slope * span), float(lr.pvalue), float(pr[:, 1].std())
    else:
        drift, drift_p, rep_sd = 0.0, 1.0, np.nan
    return dict(offset_sec=round(offset, 2), coarse_sec=coarse, r_coarse=r_coarse,
                r_coarse_second=r_second, fine_sec=round(offset - coarse, 2),
                r_fine=main[1], spread_sec=float(offs.max() - offs.min()),
                combos={k: round(v[0], 2) for k, v in combos.items()},
                per_rep=[dict(t=t0, offset=o, r=r) for t0, o, r in per_rep],
                per_rep_sd=rep_sd, drift_sec=round(drift, 2), drift_p=drift_p,
                curves=dict(lags_coarse=lags_c, cc_coarse=cc_c, lags_fine=main[2] - coarse,
                            cc_fine=main[3]))


def qc(res, cfg):
    sc = cfg["sync"]
    problems = []
    if res["r_coarse"] - res["r_coarse_second"] < sc["min_peak_margin"]:
        problems.append(f"puncak kasar tidak tegas (r {res['r_coarse']:.2f} vs "
                        f"{res['r_coarse_second']:.2f})")
    if abs(res["offset_sec"]) > sc["prior_max_abs_sec"]:
        problems.append(f"|offset| {res['offset_sec']:.1f} dtk > prior hitungan-3 "
                        f"({sc['prior_max_abs_sec']} dtk)")
    if abs(res["drift_sec"]) > sc["max_drift_sec"] and res["drift_p"] < 0.05:
        problems.append(f"drift signifikan {res['drift_sec']:+.2f} dtk sepanjang sesi "
                        f"(p={res['drift_p']:.3f}) → pertimbangkan pemetaan linear")
    if res["r_fine"] < sc["min_r_fine"]:
        problems.append(f"korelasi halus rendah (r {res['r_fine']:.2f})")
    if res["spread_sec"] > sc["max_spread_sec"]:
        problems.append(f"kombinasi sinyal tidak sepakat (sebaran {res['spread_sec']:.2f} dtk)")
    return problems
