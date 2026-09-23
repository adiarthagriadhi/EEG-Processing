"""Referensi rata-rata spektral (eksploratif). Per kanal × fase × gerakan:
specparam memisahkan garis latar (aperiodik) dan tonjolan osilasi (periodik).
- Indeks global = median perubahan garis latar per belahan (kiri: kanal -A1, kanan: -A2).
- Tonjolan relatif = perubahan tonjolan − median belahan (tafsiran RELATIF thd seluruh kepala).
- Batas ketelitian = "osilasi palsu" maksimum setelah noise 1/f global (+8 dB) disuntikkan
  ke jendela diam (uji P02/P10: 1,8–3,4 dB). Efek di bawah batas ini = belum dapat dipercaya.
Rujukan: Donoghue dkk. 2020 (specparam); Pfurtscheller (Laplacian, prinsip "lebih dari sekitar")."""
import numpy as np
import pandas as pd
from mne.filter import filter_data
from mne.time_frequency import psd_array_multitaper

LEFT = ["Fp1", "F3", "C3", "P3", "O1", "F7", "T3", "T5"]
RIGHT = ["Fp2", "F4", "C4", "P4", "O2", "F8", "T4", "T6"]
BANDS = {"theta": (4, 8), "mu": (8, 13), "beta": (13, 30)}
GRID = np.arange(2, 30.01, 0.5)


def _psd(x, sf):
    p, f = psd_array_multitaper(x, sf, fmin=1.5, fmax=31, bandwidth=2.5, verbose=False)
    return np.array([np.interp(GRID, f, pp) for pp in p])


def _fit(P):
    from fooof import FOOOF
    fm = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4, aperiodic_mode="fixed", verbose=False)
    fm.fit(GRID, P, [2, 30])
    flat = np.log10(P) - fm._ap_fit
    return (fm.aperiodic_params_[0], fm.aperiodic_params_[1],
            {b: flat[(GRID >= lo) & (GRID < hi)].mean() for b, (lo, hi) in BANDS.items()})


def _inject(x, rng, db=8.0):
    """Noise 1/f bersama per belahan (meniru artefak global/referensi)."""
    w = filter_data(np.cumsum(rng.normal(size=(2, x.shape[1])), 1), 100, 1, 35, verbose=False)
    y = x.copy()
    s = np.sqrt(10 ** (db / 10) - 1) * x.std() / w.std()
    y[:8] += s * w[0]
    y[8:] += s * w[1]
    return y


def analyze(epochs, pid, cfg, seed=0):
    rng = np.random.default_rng(seed)
    chs = LEFT + RIGHT
    X = epochs.get_data(picks=chs)
    t, sf = epochs.times, epochs.info["sfreq"]
    md = epochs.metadata.reset_index(drop=True)
    b0, b1 = cfg["erd"]["baseline"]
    rows, noise_floor = [], []
    for task in md.task.unique():
        spec = {}
        for i, m in md[md.task == task].iterrows():
            W = {"DIAM": (b0, b1), "PRA": tuple(cfg["erd"]["pre_window"]),
                 "TURUN": (m.rel_turun, m.rel_tahan), "TAHAN": (m.rel_tahan, m.rel_naik),
                 "NAIK": (m.rel_naik, m.rel_end),
                 "POST": (m.rel_end + cfg["erd"]["post_window"][0],
                          m.rel_end + cfg["erd"]["post_window"][1])}
            for ph, (a, b) in W.items():
                if not np.isfinite([a, b]).all() or b - a < 0.5 or b > t[-1]:
                    continue
                x = X[i][:, (t >= a) & (t < b)]
                spec.setdefault(ph, []).append(_psd(x, sf))
                if ph == "DIAM":
                    spec.setdefault("DIAM+NOISE", []).append(_psd(_inject(x, rng), sf))
        if "DIAM" not in spec:
            continue
        par = {ph: [_fit(np.mean(v, 0)[c]) for c in range(16)] for ph, v in spec.items()}
        for ph in par:
            if ph == "DIAM":
                continue
            off = 10 * np.array([par[ph][c][0] - par["DIAM"][c][0] for c in range(16)])
            exp_ = np.array([par[ph][c][1] - par["DIAM"][c][1] for c in range(16)])
            per = {b: 10 * np.array([par[ph][c][2][b] - par["DIAM"][c][2][b] for c in range(16)])
                   for b in BANDS}
            if ph == "DIAM+NOISE":
                noise_floor.append(float(np.max(np.abs(np.r_[per["mu"], per["beta"]]))))
                continue
            gl = {"kiri": np.median(off[:8]), "kanan": np.median(off[8:])}
            for c, ch in enumerate(chs):
                hemi = "kiri" if c < 8 else "kanan"
                sl = slice(0, 8) if c < 8 else slice(8, 16)
                r = dict(participant_id=pid, task=task, phase=ph, channel=ch, hemisphere=hemi,
                         n_windows=len(spec[ph]), offset_change_db=off[c],
                         exponent_change=exp_[c], global_offset_db=gl[hemi],
                         is_simulated=cfg["is_simulated"])
                for b in BANDS:
                    r[f"{b}_periodic_db"] = per[b][c]
                    r[f"{b}_relative_db"] = per[b][c] - np.median(per[b][sl])
                rows.append(r)
    df = pd.DataFrame(rows)
    floor = float(np.max(noise_floor)) if noise_floor else np.nan
    return df, floor
