"""Tahap 5b: fitur Romberg (EO/EC) dengan aturan cakupan dan NaN."""
import mne
import numpy as np


def seg_psd(raw, onset, dur, pad):
    a, b = onset + pad, min(onset + dur - pad, raw.times[-1])
    if b - a < 2.0:
        return None, None, 0.0
    seg = raw.copy().crop(a, b)
    ep = mne.make_fixed_length_epochs(seg, duration=2.0, overlap=1.0, preload=True,
                                      verbose="error")
    ep.drop_bad(reject=dict(eeg=150e-6), verbose="error")
    if len(ep) == 0:
        return None, None, 0.0
    sp = ep.compute_psd(method="welch", fmin=1, fmax=40, n_fft=200, picks="eeg",
                        verbose="error")
    psd, f = sp.get_data(return_freqs=True)
    clean_sec = len(ep) * 1.0 + 1.0          # epoch 2 dtk, overlap 1 dtk
    return (psd.mean(axis=0), sp.ch_names), f, clean_sec


def bp(spec, f, picks, lo, hi, relative=True):
    psd, chs = spec
    idx = [chs.index(c) for c in picks]
    m = (f >= lo) & (f < hi)
    band = np.trapezoid(psd[idx][:, m], f[m], axis=-1)
    if relative:
        tot = (f >= 1) & (f < 35)            # bandwidth efektif perangkat
        band = band / np.trapezoid(psd[idx][:, tot], f[tot], axis=-1)
    return float(band.mean())


def iaf(spec, f, picks, min_peak_db=3.0, k_noise=3.0):
    """IAF hanya jika ada puncak nyata di atas tren 1/f (lihat EEG_PROCESSING.md 11)."""
    psd, chs = spec
    s = psd[[chs.index(c) for c in picks]].mean(axis=0)
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


def features(raw, segments, pid, cfg):
    """segments: {'EO': (onset_eeg, dur, coverage), 'EC': (...)}."""
    rc = cfg["romberg"]
    out = dict(participant_id=pid, is_simulated=cfg["is_simulated"])
    specs = {}
    for cond in ("EO", "EC"):
        if cond not in segments:
            out[f"coverage_{cond}"] = 0.0
            out[f"clean_sec_{cond}"] = 0.0
            continue
        onset, dur, cov = segments[cond]
        spec, f, clean_sec = seg_psd(raw, onset, dur, rc["pad_sec"])
        out[f"coverage_{cond}"] = round(cov, 3)
        out[f"clean_sec_{cond}"] = clean_sec
        if spec is not None and clean_sec >= rc["min_clean_sec"]:
            specs[cond] = spec
    nan = np.nan
    eo, ec = specs.get("EO"), specs.get("EC")
    out.update(
        alpha_occ_EC=bp(ec, f, ["O1", "O2"], 8, 13) if ec else nan,
        alpha_reactivity_EC_EO=(bp(ec, f, ["O1", "O2"], 8, 13, False) /
                                bp(eo, f, ["O1", "O2"], 8, 13, False)) if ec and eo else nan,
        mu_sm_EC=bp(ec, f, ["C3", "C4"], 8, 13) if ec else nan,
        mu_sm_EO=bp(eo, f, ["C3", "C4"], 8, 13) if eo else nan,
        theta_front_EC=bp(ec, f, ["F3", "F4"], 4, 8) if ec else nan,
        iaf_occ_EC=iaf(ec, f, ["O1", "O2"]) if ec else nan,
        iaf_par_EC=iaf(ec, f, ["P3", "P4"]) if ec else nan,
        beta_sm_EO=bp(eo, f, ["C3", "C4"], 13, 30) if eo else nan,
        beta_sm_EC=bp(ec, f, ["C3", "C4"], 13, 30) if ec else nan,
        alpha_par_EC=bp(ec, f, ["P3", "P4"], 8, 13) if ec else nan,
        theta_alpha_ratio_EC=(bp(ec, f, ["F3", "F4"], 4, 8, False) /
                              bp(ec, f, ["O1", "O2"], 8, 13, False)) if ec else nan,
    )
    return out
