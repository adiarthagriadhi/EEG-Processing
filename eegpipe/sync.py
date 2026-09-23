"""Sinkronisasi EEG↔video (Tahap 2): korelasi silang energi gerak video (area partisipan)
dengan envelope artefak gerak/otot EEG. t_eeg = t_video + offset."""
import numpy as np
from scipy.signal import correlate, correlation_lags


def to_grid(t, x, fs, t_end=None):
    t, x = np.asarray(t, float), np.asarray(x, float)
    ok = np.isfinite(x)
    grid = np.arange(0, (t_end if t_end is not None else t[ok][-1]), 1 / fs)
    return grid, np.interp(grid, t[ok], x[ok])


def eeg_motion(raw, cfg):
    sc = cfg["sync"]
    env = (raw.copy().pick(sc["eeg_motion_channels"])
           .filter(*sc["eeg_motion_band"], verbose="error")
           .apply_hilbert(envelope=True).get_data().mean(axis=0))
    return to_grid(raw.times, env, sc["fs"])


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


def two_stage(timeline, video_t, video_motion, raw, cfg):
    """Kasar: boxcar HUD vs EEG (±coarse_lag, tahan pola blok istirahat panjang).
    Halus: energi gerak video vs EEG dalam ±fine_lag di sekitar hasil kasar.
    Menghasilkan offset (t_eeg = t_video + offset) dan metrik QC."""
    sc = cfg["sync"]
    fs = sc["fs"]
    _, e = eeg_motion(raw, cfg)
    _, box = hud_boxcar(timeline, video_t[-1], fs)
    coarse, r_coarse, lags_c, cc_c = xcorr_offset(box + 0.01, e, fs, sc["coarse_lag_sec"])
    # puncak kedua (di luar ±3 dtk dari puncak utama): pembeda terhadap periodisitas 16 dtk
    far = np.abs(lags_c - coarse) > 3
    r_second = float(cc_c[far].max()) if far.any() else np.nan
    _, v = to_grid(video_t, video_motion, fs)
    # geser sinyal EEG sebesar offset kasar, lalu cari lag halus di sekitar 0
    shift = int(round(coarse * fs))
    e_shift = e[shift:] if shift >= 0 else np.concatenate([np.full(-shift, np.median(e)), e])
    fine, r_fine, lags_f, cc_f = xcorr_offset(v, e_shift, fs, sc["fine_lag_sec"])
    offset = coarse + fine
    # drift: lag halus per paruh sesi
    n = min(len(v), len(e_shift))
    half = []
    for a, b in [(0, n // 2), (n // 2, n)]:
        o, rr, _, _ = xcorr_offset(v[a:b], e_shift[a:b], fs, sc["fine_lag_sec"])
        half.append(o)
    return dict(offset_sec=round(offset, 2), coarse_sec=coarse, r_coarse=r_coarse,
                r_coarse_second=r_second, fine_sec=fine, r_fine=r_fine,
                drift_sec=round(half[1] - half[0], 2),
                curves=dict(lags_coarse=lags_c, cc_coarse=cc_c, lags_fine=lags_f,
                            cc_fine=cc_f))


def qc(res, cfg):
    sc = cfg["sync"]
    problems = []
    if res["r_coarse"] - res["r_coarse_second"] < sc["min_peak_margin"]:
        problems.append(f"puncak kasar tidak tegas (r {res['r_coarse']:.2f} vs "
                        f"{res['r_coarse_second']:.2f})")
    if abs(res["offset_sec"]) > sc["prior_max_abs_sec"]:
        problems.append(f"|offset| {res['offset_sec']:.1f} dtk > prior hitungan-3 "
                        f"({sc['prior_max_abs_sec']} dtk)")
    if abs(res["drift_sec"]) > sc["max_drift_sec"]:
        problems.append(f"drift {res['drift_sec']:+.2f} dtk antar paruh sesi")
    if res["r_fine"] < sc["min_r_fine"]:
        problems.append(f"korelasi halus rendah (r {res['r_fine']:.2f})")
    return problems
