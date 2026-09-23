import mne


def load_edf(path, cfg):
    """Baca EDF KT88: nama kanal 'C3-A1' → 'C3', Add_lead → misc, montage 10-20."""
    raw = mne.io.read_raw_edf(path, preload=True, verbose="error")
    if raw.info["sfreq"] != cfg["eeg"]["sfreq"]:
        raise ValueError(f"{path}: sfreq {raw.info['sfreq']} ≠ {cfg['eeg']['sfreq']}")
    raw.rename_channels(lambda ch: ch.split("-")[0])
    misc = [c for c in cfg["eeg"]["misc_channels"] if c in raw.ch_names]
    raw.set_channel_types({c: "misc" for c in misc}, verbose="error")
    raw.set_montage(cfg["eeg"]["montage"], verbose="error")
    # Tanggal header EDF KT88 tidak valid (default perangkat) → jangan dipakai
    raw.set_meas_date(None)
    return raw
