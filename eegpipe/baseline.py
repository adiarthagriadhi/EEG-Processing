"""Tahap baseline: rekaman istirahat terpisah PXX_Baseline.EDF (berdiri tenang ±60 dtk,
direkam SEBELUM Trial, di luar video; dikonfirmasi pengguna 2026-09-23).
Dipakai TERPISAH, tidak disambung ke Trial (impedansi/filter perangkat mulai ulang;
sambungan tidak kontinu: lompatan 2–3× langkah sampel khas pada P02–P10).
1. Fitur istirahat: power relatif per wilayah, IAF (hanya bila puncak nyata), eksponen
   aperiodik (specparam), laju kedipan (indikasi mata terbuka/tertutup).
2. Uji sensitivitas ERD: power jendela fase (multitaper) relatif (a) DIAM di dalam Trial
   dan (b) Baseline.EDF — metode spektral sama agar perbedaan hanya berasal dari acuan."""
import mne
import numpy as np
import pandas as pd
from mne.time_frequency import psd_array_multitaper

from .romberg import bp, iaf, seg_epochs

REGIONS = {"occ": ["O1", "O2"], "par": ["P3", "P4"], "sm": ["C3", "C4"], "front": ["F3", "F4"]}
BANDS = {"theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}


def blink_rate(raw):
    ch = max(["Fp1", "Fp2"], key=lambda c: np.ptp(raw.copy().pick([c]).get_data()))
    ev = mne.preprocessing.find_eog_events(raw, ch_name=ch, l_freq=1, h_freq=10,
                                           verbose="error")
    return len(ev) / (raw.times[-1] / 60)


def features(raw_clean, raw_filt, pid, cfg, pad=2.0):
    rej = cfg["romberg"]["reject_uv"]
    S = seg_epochs(raw_clean, 0.0, raw_clean.times[-1], pad)
    out = dict(participant_id=pid, is_simulated=cfg["is_simulated"],
               baseline_sec=round(raw_clean.times[-1], 1),
               blink_per_min=round(blink_rate(raw_filt), 1))
    for rn, chs in REGIONS.items():
        for bn, (lo, hi) in BANDS.items():
            out[f"rest_{bn}_{rn}"], n = bp(S, chs, lo, hi, rej, True)
        out[f"rest_n_win_{rn}"] = n
    out["rest_theta_alpha_ratio"] = (bp(S, ["F3", "F4"], 4, 8, rej, False)[0] /
                                     bp(S, ["O1", "O2"], 8, 13, rej, False)[0])
    out["iaf_occ_rest"] = iaf(S, ["O1", "O2"], rej)
    out["iaf_par_rest"] = iaf(S, ["P3", "P4"], rej)
    try:
        from fooof import FOOOF
        for rn, chs in REGIONS.items():
            idx = [S["chs"].index(c) for c in chs]
            ok = (S["ptp"][:, idx] <= rej).all(axis=1)
            if ok.any():
                fm = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4, aperiodic_mode="fixed",
                           verbose=False)
                fm.fit(S["f"], S["psd"][ok][:, idx].mean(axis=(0, 1)), [2, 30])
                out[f"rest_exponent_{rn}"] = float(fm.aperiodic_params_[1])
    except ImportError:
        pass
    return out, S


def _band_power(x, sf, bands):
    p, f = psd_array_multitaper(x, sf, fmin=2, fmax=31, bandwidth=2.5, verbose=False)
    return {b: p[..., (f >= lo) & (f < hi)].mean(-1) for b, (lo, hi) in bands.items()}


def erd_sensitivity(epochs, raw_base, pid, cfg, roi=("C3", "C4", "P3", "P4", "O1", "O2")):
    """%ERD/ERS per repetisi × fase × kanal terhadap dua acuan (multitaper)."""
    ec, sf = cfg["erd"], epochs.info["sfreq"]
    bands = ec["bands"]                       # theta / mu / beta, sama dengan ERD utama
    roi = [c for c in roi if c in epochs.ch_names]
    X, t = epochs.get_data(picks=roi), epochs.times
    # acuan (b): rata-rata power jendela 2 dtk Baseline.EDF yang lolos batas amplitudo
    B = raw_base.copy().pick(roi).get_data()
    w = int(2 * sf)
    segs = [B[:, i:i + w] for i in range(int(2 * sf), B.shape[1] - w - int(2 * sf), w // 2)]
    segs = [s for s in segs if np.ptp(s, axis=1).max() * 1e6 <= cfg["romberg"]["reject_uv"]]
    if not segs:
        return pd.DataFrame()
    pb = _band_power(np.stack(segs), sf, bands)
    ref_base = {b: v.mean(0) for b, v in pb.items()}
    rows = []
    for i, m in epochs.metadata.reset_index(drop=True).iterrows():
        W = {"DIAM": tuple(ec["baseline"]), "PRA": tuple(ec["pre_window"]),
             "TURUN": (m.rel_turun, m.rel_tahan), "TAHAN": (m.rel_tahan, m.rel_naik),
             "NAIK": (m.rel_naik, m.rel_end),
             "POST": (m.rel_end + ec["post_window"][0], m.rel_end + ec["post_window"][1])}
        if m.compliance == "short_hold":
            W.pop("TAHAN")
        pw = {}
        for ph, (a, b) in W.items():
            if np.isfinite([a, b]).all() and b - a >= ec["min_phase_sec"] and b <= t[-1]:
                pw[ph] = _band_power(X[i][:, (t >= a) & (t < b)], sf, bands)
        if "DIAM" not in pw:
            continue
        for ph, p in pw.items():
            if ph == "DIAM":
                continue
            for b in bands:
                for c, ch in enumerate(roi):
                    rows.append(dict(participant_id=pid, task=m.task, rep=m.rep, phase=ph,
                                     band=b, channel=ch,
                                     erd_ref_trial_pct=100 * (p[b][c] / pw["DIAM"][b][c] - 1),
                                     erd_ref_restEDF_pct=100 * (p[b][c] / ref_base[b][c] - 1),
                                     is_simulated=cfg["is_simulated"]))
    return pd.DataFrame(rows)
