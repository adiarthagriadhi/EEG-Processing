"""Tahap 3: filter, kanal buruk, ICA (hanya komponen mata)."""
import mne
from mne.preprocessing import ICA


def filter_raw(raw, cfg):
    f = cfg["eeg"]["filter"]
    # TANPA notch: 50 Hz = Nyquist pada 100 Hz; perangkat sudah LP ≈ 35 Hz
    return raw.filter(f["l_freq"], f["h_freq"], picks="eeg", verbose="error")


def fit_ica(raw, bads=(), random_state=97):
    raw = raw.copy()
    raw.info["bads"] = list(bads)
    n_eeg = len(mne.pick_types(raw.info, eeg=True, exclude="bads"))
    ica = ICA(n_components=n_eeg - 1, method="picard",
              fit_params=dict(extended=True, ortho=False), random_state=random_state,
              max_iter="auto", verbose="error")
    ica.fit(raw, picks="eeg", reject_by_annotation=True, verbose="error")
    eog_idx, scores = ica.find_bads_eog(raw, ch_name=["Fp1", "Fp2"], verbose="error")
    return ica, [int(i) for i in eog_idx]


def clean(raw, cfg, bads=(), ica=None, exclude=()):
    raw = filter_raw(raw.copy(), cfg)
    raw.info["bads"] = list(bads)
    if raw.info["bads"]:
        raw.interpolate_bads(reset_bads=True, verbose="error")
    if ica is not None:
        ica.exclude = list(exclude)
        ica.apply(raw, verbose="error")
    return raw
