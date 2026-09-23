"""Tahap 3: filter, kanal buruk, ICA (hanya komponen mata)."""
import mne
from mne.preprocessing import ICA


def filter_raw(raw, cfg):
    f = cfg["eeg"]["filter"]
    # TANPA notch: 50 Hz = Nyquist pada 100 Hz; perangkat sudah LP ≈ 35 Hz
    return raw.filter(f["l_freq"], f["h_freq"], picks="eeg", verbose="error")


def detect_bad_channels(raw_filt, rest=None, z_thr=3.0, flat_uv=1.0, win_sec=2.0):
    """Kanal buruk otomatis: z robust (median/MAD) dari log SD per jendela 2 dtk, dihitung
    pada segmen ISTIRAHAT (gerak menyamarkan kanal bising; P02: P3/P4 z 2,1–2,8 di seluruh
    rekaman tetapi +3,6 saat istirahat, ~4× kanal lain)."""
    import numpy as np
    x = raw_filt.copy().pick("eeg")
    if rest is not None:
        x.crop(*rest)
    d = x.get_data() * 1e6
    n = int(win_sec * x.info["sfreq"])
    w = d[:, : d.shape[1] // n * n].reshape(d.shape[0], -1, n)
    sd = np.median(w.std(axis=2), axis=1)
    lsd = np.log(np.maximum(sd, 1e-3))
    mad = 1.4826 * np.median(np.abs(lsd - np.median(lsd)))
    z = (lsd - np.median(lsd)) / mad if mad > 0 else lsd * 0
    bads = [c for c, zz, s in zip(x.ch_names, z, sd) if zz > z_thr or s < flat_uv]
    return bads, dict(zip(x.ch_names, [round(float(v), 2) for v in z]))


def fit_ica(raw_filt, bads=(), fit_span=None, random_state=97):
    """ICA di-fit pada segmen DIAM (fit_span, mis. ISTIRAHAT UTAMA): pada sesi penuh
    komponen didominasi artefak gerak seluruh tubuh dan kedipan tidak terpisah (P02)."""
    raw = raw_filt.copy()
    raw.info["bads"] = list(bads)
    fit_data = raw.copy().crop(*fit_span) if fit_span else raw
    n_eeg = len(mne.pick_types(raw.info, eeg=True, exclude="bads"))
    ica = ICA(n_components=n_eeg - 1, method="picard",
              fit_params=dict(extended=True, ortho=False), random_state=random_state,
              max_iter="auto", verbose="error")
    ica.fit(fit_data, picks="eeg", reject_by_annotation=True, verbose="error")
    return ica


def blink_components(ica, raw_filt, bads=(), max_comp=3, min_gain=0.10):
    """Pilih komponen kedipan secara serakah: tiap langkah pilih komponen yang paling
    menurunkan amplitudo rata-rata-terkunci-kedipan di Fp1+Fp2; berhenti bila penurunan
    tambahan < min_gain. P02: 209 kedipan (dominan Fp2)."""
    import numpy as np
    raw = raw_filt.copy()
    raw.info["bads"] = list(bads)
    ch = max(["Fp1", "Fp2"], key=lambda c: np.ptp(raw.copy().pick([c]).filter(
        1, 10, verbose="error").get_data()))
    ev = mne.preprocessing.find_eog_events(raw, ch_name=ch, l_freq=1, h_freq=10,
                                           verbose="error")
    if len(ev) < 10:
        return [], dict(n_blinks=len(ev), before=np.nan, after=np.nan)
    ep = mne.Epochs(raw, ev, tmin=-0.5, tmax=0.5, baseline=(-0.5, -0.3), picks="eeg",
                    preload=True, verbose="error")

    def blink_ptp(excl):
        ica.exclude = list(excl)
        e = ica.apply(ep.copy(), verbose="error").average().pick(["Fp1", "Fp2"])
        return float(np.ptp(e.data, axis=1).sum() * 1e6)

    chosen, cur = [], blink_ptp([])
    before = cur
    for _ in range(max_comp):
        cand = [(blink_ptp(chosen + [k]), k) for k in range(ica.n_components_)
                if k not in chosen]
        val, k = min(cand)
        if (cur - val) / before < min_gain:
            break
        chosen.append(k)
        cur = val
    ica.exclude = []
    return chosen, dict(n_blinks=len(ev), blink_channel=ch, before=round(before, 1),
                        after=round(cur, 1))


def clean(raw, cfg, bads=(), ica=None, exclude=()):
    raw = filter_raw(raw.copy(), cfg)
    raw.info["bads"] = list(bads)
    if raw.info["bads"]:
        raw.interpolate_bads(reset_bads=True, verbose="error")
    if ica is not None:
        ica.exclude = list(exclude)
        ica.apply(raw, verbose="error")
    return raw
