"""Area-map: merangkum hasil spectral per area anatomis (frontal kiri+kanan, dll).
Acuan gabungan per partisipan (50% jendela 2-detik paling diam dari BERDIRI RILEKS + ISTIRAHAT UTAMA).
Fixed offset 0.85s, 12 segmen gabungan per fase, trim 0.25s dari edges."""
import numpy as np
import pandas as pd
from mne.time_frequency import psd_array_multitaper
from fooof import FOOOF

# Anatomical areas (left + right averaged)
AREAS = {
    "frontopolar": ["Fp1", "Fp2"],
    "frontal": ["F3", "F4"],
    "frontotemporal": ["F7", "F8"],
    "sentral": ["C3", "C4"],
    "temporal": ["T3", "T4"],
    "parietal": ["P3", "P4"],
    "temporo_posterior": ["T5", "T6"],
    "oksipital": ["O1", "O2"],
}

CHANNELS = ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "C3", "C4",
            "T3", "T4", "P3", "P4", "T5", "T6", "O1", "O2"]
GRID = np.arange(2, 30.01, 0.5)
BANDS = {"mu": (8, 13), "beta": (13, 30)}
PHASES = {"TURUN": ("act_turun", "act_tahan"),
          "TAHAN": ("act_tahan", "act_naik"),
          "NAIK": ("act_naik", "act_end")}


def _psd(x, sf):
    """Hitung power spectral density (per kanal atau rata-rata)."""
    if x.ndim == 1:
        x = x[np.newaxis, :]
    p, f = psd_array_multitaper(x, sf, fmin=1.5, fmax=31, bandwidth=2.5, verbose=False)
    return np.array([np.interp(GRID, f, pp) for pp in p])


def _psd_area_avg(x, sf, area_channels):
    """Hitung PSD rata-rata untuk suatu area (kanal kiri+kanan digabung)."""
    ch_idx = [CHANNELS.index(c) for c in area_channels if c in CHANNELS]
    if not ch_idx:
        return None
    psd = _psd(x[ch_idx], sf)  # shape: (n_channels, len(GRID))
    return psd.mean(axis=0)


def _fit_specparam(P):
    """Fit specparam: garis latar (aperiodik) + tonjolan (periodik) mu/beta."""
    fm = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4,
               aperiodic_mode="fixed", verbose=False)
    fm.fit(GRID, P, [2, 30])
    flat = np.log10(P) - fm._ap_fit
    return (fm.aperiodic_params_[0],  # garis latar intercept
            flat[(GRID >= 8) & (GRID < 13)].mean(),  # mu periodik
            flat[(GRID >= 13) & (GRID < 30)].mean())  # beta periodik


def get_baseline_psd_per_area(raw, tl, cfg, offset_sec=0.85):
    """Hitung PSD acuan gabungan per area: 50% jendela 2-detik paling diam
    dari BERDIRI RILEKS + ISTIRAHAT UTAMA (dari timeline video).

    Returns: dict {area_name -> mean_PSD_array}
    """
    sf = raw.info["sfreq"]
    eeg_raw = raw.get_data(picks=CHANNELS)
    eeg_filt = raw.copy().filter(1, 30, verbose="error").get_data(picks=CHANNELS)
    t_end = raw.times[-1]

    # Cari segmen istirahat dari timeline
    rest_segs = tl[tl.task.isin(["BERDIRI RILEKS", "ISTIRAHAT UTAMA"])]
    if rest_segs.empty:
        # Fallback: gunakan jendela baseline di ERD config
        b0, b1 = cfg["erd"]["baseline"]
        t = raw.times
        baseline_psd = _psd(eeg_raw[:, (t >= b0) & (t < b1)], sf).mean(axis=0)
        return {area: baseline_psd for area in AREAS}

    # Kumpulkan semua jendela 2-detik potensial dengan ketenangan
    windows = []
    for _, seg in rest_segs.iterrows():
        start_sec = seg.start + offset_sec
        end_sec = seg.end + offset_sec
        if start_sec < 0 or end_sec > t_end:
            continue
        # Langkah 0.5 detik (overlapping)
        for w_start_sec in np.arange(start_sec + 0.5, end_sec - 2.5, 0.5):
            w_end_sec = w_start_sec + 2.0
            if w_end_sec <= t_end:
                w_start_idx = int(w_start_sec * sf)
                w_end_idx = int(w_end_sec * sf)
                if w_end_idx - w_start_idx == 2 * sf:
                    # Ketenangan = median absolute value dalam 1-30 Hz (proxy artefak)
                    seg_filt = eeg_filt[:, w_start_idx:w_end_idx]
                    quietness = np.median(np.abs(seg_filt))
                    windows.append((quietness, w_start_idx, w_end_idx))

    if not windows:
        # Fallback
        b0, b1 = cfg["erd"]["baseline"]
        t = raw.times
        baseline_psd = _psd(eeg_raw[:, (t >= b0) & (t < b1)], sf).mean(axis=0)
        return {area: baseline_psd for area in AREAS}

    # Sort by ketenangan, pilih 50% paling diam
    windows.sort(key=lambda w: w[0])
    n_best = max(1, len(windows) // 2)
    best_windows = windows[:n_best]

    # Hitung mean PSD per area dari N jendela paling diam
    baseline_per_area = {}
    for area_name, area_channels in AREAS.items():
        psds = []
        for _, w_start_idx, w_end_idx in best_windows:
            psd = _psd_area_avg(eeg_raw[:, w_start_idx:w_end_idx], sf, area_channels)
            if psd is not None:
                psds.append(psd)
        if psds:
            baseline_per_area[area_name] = np.mean(psds, axis=0)
        else:
            # Fallback untuk area ini
            baseline_per_area[area_name] = np.zeros_like(GRID)

    return baseline_per_area


def analyze(clean, reps, tl, pid, cfg, offset_sec=0.85, trim_pct=0.25):
    """Analisis area-map: per area × fase (TURUN/TAHAN/NAIK).

    Parameters:
    -----------
    clean : Raw
        Rekaman EEG bersih (preprocess stage output)
    reps : DataFrame
        Hasil detect_reps (phases stage output)
    tl : DataFrame
        Timeline task dari OCR (ocr stage output)
    pid : str
        Participant ID
    cfg : dict
        Konfigurasi pipeline
    offset_sec : float
        Offset sinkronisasi tetap (default 0.85 dari audit)
    trim_pct : float
        Fraksi tepi fase untuk dipotong (default 0.25 = 25%)

    Returns:
    --------
    DataFrame
        Kolom: pid, area, phase, garis_latar_db, mu_periodic_db, beta_periodic_db, n_windows
    """
    sf = clean.info["sfreq"]
    x = clean.get_data(picks=CHANNELS)
    t_end = clean.times[-1]

    # Dapatkan baseline PSD per area
    baseline_per_area = get_baseline_psd_per_area(clean, tl, cfg, offset_sec)
    baseline_fit_per_area = {area: _fit_specparam(psd)
                              for area, psd in baseline_per_area.items()}

    rows = []

    # Iterasi per fase
    for phase_name, (start_col, end_col) in PHASES.items():
        segments = []

        # Kumpulkan semua segmen fase ini (hingga 12 segmen)
        for _, rep in reps.iterrows():
            start_val = rep.get(start_col)
            end_val = rep.get(end_col)

            if not np.isfinite([start_val, end_val]).all():
                continue
            dur = end_val - start_val
            if dur < 0.5:  # Skip terlalu pendek
                continue

            # Trim edges
            trim_sec = min(trim_pct * dur, 0.25)  # max 0.25s
            seg_start = start_val + trim_sec + offset_sec
            seg_end = end_val - trim_sec + offset_sec

            if seg_end - seg_start < 0.4 or seg_start < 0 or seg_end > t_end:
                continue

            # Ambil data
            idx_start = int(seg_start * sf)
            idx_end = int(seg_end * sf)
            if idx_start < 0 or idx_end > len(x[0]) or idx_end <= idx_start:
                continue

            segments.append(x[:, idx_start:idx_end])

        if not segments:
            continue  # Skip fase jika tidak ada segmen valid

        n_windows = len(segments)

        # Hitung PSD per area dari semua segmen fase ini
        for area_name, area_channels in AREAS.items():
            seg_psds = []
            for seg in segments:
                psd = _psd_area_avg(seg, sf, area_channels)
                if psd is not None:
                    seg_psds.append(psd)

            if not seg_psds:
                continue

            # Mean PSD for this phase × area
            mean_seg_psd = np.mean(seg_psds, axis=0)

            # Fit specparam
            fit_seg = _fit_specparam(mean_seg_psd)
            fit_base = baseline_fit_per_area[area_name]

            row = {
                "participant_id": pid,
                "area": area_name,
                "phase": phase_name,
                "n_windows": n_windows,
                "garis_latar_db": 10 * (fit_seg[0] - fit_base[0]),
                "mu_periodic_db": 10 * (fit_seg[1] - fit_base[1]),
                "beta_periodic_db": 10 * (fit_seg[2] - fit_base[2]),
                "is_simulated": cfg.get("is_simulated", False),
            }
            rows.append(row)

    return pd.DataFrame(rows)
