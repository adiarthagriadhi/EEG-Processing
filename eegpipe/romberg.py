"""Tahap 5b: fitur Romberg (EO/EC). Penolakan artefak PER FITUR: jendela hanya ditolak
bila kanal yang dipakai fitur itu melewati batas (P02: gangguan kanal kiri/A1 tidak
membuang alpha O1/O2 yang bersih). Segmen terpotong dipakai sejauh tersedia."""
import mne
import numpy as np


def seg_epochs(raw, onset, dur, pad):
    a, b = onset + pad, min(onset + dur - pad, raw.times[-1] - 0.01)
    if b - a < 1.5:
        return None
    win = 2.0 if b - a >= 2.0 else b - a        # segmen terpotong → satu jendela
    seg = raw.copy().crop(a, b)
    ep = mne.make_fixed_length_epochs(seg, duration=win, overlap=win / 2 if win == 2.0 else 0,
                                      preload=True, verbose="error").pick("eeg")
    n = len(ep.times)
    sp = ep.compute_psd(method="welch", fmin=1, fmax=40, n_fft=200, n_per_seg=min(200, n),
                        verbose="error")
    psd, f = sp.get_data(return_freqs=True)                 # epoch × kanal × frek
    ptp = np.ptp(ep.get_data(), axis=2) * 1e6               # epoch × kanal (µV)
    return dict(psd=psd, f=f, ptp=ptp, chs=ep.ch_names, win=win, step=win / 2 if win == 2 else win)


def _clean_mean(S, picks, reject_uv):
    idx = [S["chs"].index(c) for c in picks]
    ok = (S["ptp"][:, idx] <= reject_uv).all(axis=1)
    if not ok.any():
        return None, 0
    return S["psd"][ok][:, idx].mean(axis=0), int(ok.sum())


def bp(S, picks, lo, hi, reject_uv, relative=True):
    if S is None:
        return np.nan, 0
    psd, n = _clean_mean(S, picks, reject_uv)
    if psd is None:
        return np.nan, 0
    f = S["f"]
    m = (f >= lo) & (f < hi)
    band = np.trapezoid(psd[:, m], f[m], axis=-1)
    if relative:
        tot = (f >= 1) & (f < 35)            # bandwidth efektif perangkat
        band = band / np.trapezoid(psd[:, tot], f[tot], axis=-1)
    return float(band.mean()), n


def iaf(S, picks, reject_uv, min_peak_db=3.0, k_noise=3.0):
    """IAF hanya jika ada puncak nyata di atas tren 1/f (EEG_PROCESSING.md 11)."""
    if S is None:
        return np.nan
    psd, _ = _clean_mean(S, picks, reject_uv)
    if psd is None:
        return np.nan
    f = S["f"]
    s = psd.mean(axis=0)
    fit = ((f >= 2) & (f < 7)) | ((f > 14) & (f <= 30))
    coef = np.polyfit(np.log10(f[fit]), np.log10(s[fit]), 1)
    resid = 10 * (np.log10(s) - np.polyval(coef, np.log10(f)))
    smooth = np.convolve(resid, np.ones(3) / 3, mode="same")
    m = (f >= 7) & (f <= 14)
    i = np.argmax(smooth[m])
    if smooth[m][i] < max(min_peak_db, k_noise * np.std(smooth[fit])) or i in (0, m.sum() - 1):
        return np.nan
    pk = f[m][i]
    w = (f >= pk - 2) & (f <= pk + 2)
    ex = np.clip(10 ** (resid[w] / 10) - 1, 0, None)
    return float((f[w] * ex).sum() / ex.sum())


FEATURES = {   # nama: (kondisi, kanal, lo, hi, relatif)
    "alpha_occ_EC": ("EC", ["O1", "O2"], 8, 13, True),
    "mu_sm_EC": ("EC", ["C3", "C4"], 8, 13, True),
    "mu_sm_EO": ("EO", ["C3", "C4"], 8, 13, True),
    "theta_front_EC": ("EC", ["F3", "F4"], 4, 8, True),
    "beta_sm_EO": ("EO", ["C3", "C4"], 13, 30, True),
    "beta_sm_EC": ("EC", ["C3", "C4"], 13, 30, True),
    "alpha_par_EC": ("EC", ["P3", "P4"], 8, 13, True),
}


def features(raw, segments, pid, cfg):
    """segments: {'EO': (onset_eeg, dur, coverage), 'EC': (...)}."""
    rc = cfg["romberg"]
    rej = rc["reject_uv"]
    out = dict(participant_id=pid, is_simulated=cfg["is_simulated"])
    S = {}
    for cond in ("EO", "EC"):
        out[f"coverage_{cond}"] = round(segments[cond][2], 3) if cond in segments else 0.0
        S[cond] = seg_epochs(raw, segments[cond][0], segments[cond][1], rc["pad_sec"]) \
            if cond in segments else None
        s = S[cond]
        out[f"sec_available_{cond}"] = 0.0 if s is None else round(
            s["win"] + (len(s["ptp"]) - 1) * s["step"], 1)
        if s is not None:
            med = np.median(s["ptp"], axis=0)
            out[f"ptp_median_{cond}"] = ";".join(f"{c}:{v:.0f}" for c, v in zip(s["chs"], med))
    for name, (cond, picks, lo, hi, rel) in FEATURES.items():
        out[name], out[f"{name}_n_win"] = bp(S[cond], picks, lo, hi, rej, rel)
    ec_a, n1 = bp(S["EC"], ["O1", "O2"], 8, 13, rej, False)
    eo_a, n2 = bp(S["EO"], ["O1", "O2"], 8, 13, rej, False)
    out["alpha_reactivity_EC_EO"] = ec_a / eo_a if np.isfinite(ec_a * eo_a) else np.nan
    th, n3 = bp(S["EC"], ["F3", "F4"], 4, 8, rej, False)
    out["theta_alpha_ratio_EC"] = th / ec_a if np.isfinite(th * ec_a) else np.nan
    out["iaf_occ_EC"] = iaf(S["EC"], ["O1", "O2"], rej)
    out["iaf_par_EC"] = iaf(S["EC"], ["P3", "P4"], rej)
    return out
