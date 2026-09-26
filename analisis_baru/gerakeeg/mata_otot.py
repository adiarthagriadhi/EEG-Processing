"""Tahap 5 (SEMENTARA, belum beku): artefak mata & otot di atas pipeline beku (ASR k 20 → referensi A2, epoch TE).

Varian:
  T5_dasar          : pipeline beku tanpa koreksi mata/otot.
  T5_ICA_mata       : ICA (Picard, 15 komponen) pada sinyal kontinu sesudah ASR (referensi telinga). Komponen kedipan =
                      z korelasi dengan Fp1/Fp2 (1–10 Hz) > 3 (MNE find_bads_eog). Dipasang pada sampel yang semua
                      kanalnya tidak datar; koreksi hanya diterapkan pada sampel tanpa kanal datar (di tempat lain
                      sinyal dibiarkan, karena sumber tidak dapat diestimasi bila ada kanal = 0).
  T5_ICA_mata_otot  : + komponen otot (MNE find_bads_muscle: kemiringan spektrum 7–34 Hz, letak tepi, kehalusan
                      topografi; ambang 0,5).
  T5_CCA_otot       : BSS-CCA per jendela analisis (sesudah A2, kanal tidak datar): komponen dengan autokorelasi rendah
                      dibuang bila rasio power 20–34 / 2–15 Hz-nya di atas persentil 95 komponen Istirahat partisipan
                      itu (maks. separuh komponen).
  T5_regresi_mata   : proksi EOG = rata-rata Fp1/Fp2 (1–7 Hz); koefisien regresi per kanal dari Istirahat; dikurangkan
                      dari kanal lain. Fp1/Fp2 lalu dikeluarkan dari analisis (menjadi kanal EOG).
  T5_ICAmata_CCAotot: T5_ICA_mata + T5_CCA_otot.
ICLabel tidak dipakai: dilatih pada ≥ 32 kanal 1–100 Hz; data ini 16 kanal, 100 Hz, LP perangkat ≈ 35 Hz.
"""
import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

from .istilah import KANAL
from .kualitas import DATAR_BATAS

VARIAN = ["T5_dasar", "T5_ICA_mata", "T5_ICA_mata_otot", "T5_CCA_otot", "T5_regresi_mata", "T5_ICAmata_CCAotot"]
FP = [KANAL.index("Fp1"), KANAL.index("Fp2")]


def _raw(x, sf):
    import mne
    info = mne.create_info(KANAL, sf, "eeg")
    r = mne.io.RawArray(x * 1e-6, info, verbose="error")
    r.set_montage("standard_1020", verbose="error")
    return r


def ica(xa, datar, sf, otot=False, seed=0):
    """→ (x terkoreksi, info). xa: µV kanal × sampel (sesudah ASR, referensi telinga)."""
    import mne
    from mne.preprocessing import ICA
    raw = _raw(xa, sf)
    semua_ok = ~datar.any(axis=0)
    # anotasi BAD pada sampel dengan kanal datar → tidak ikut fitting
    d = np.diff(np.r_[0, (~semua_ok).astype(int), 0])
    on, off = np.where(d == 1)[0], np.where(d == -1)[0]
    raw.set_annotations(mne.Annotations(on / sf, (off - on) / sf, ["BAD_datar"] * len(on)))
    m = ICA(n_components=15, method="picard", random_state=seed, max_iter=1000, verbose="error")
    m.fit(raw, reject=dict(eeg=400e-6), tstep=1.0, reject_by_annotation=True, verbose="error")
    eog, skor_eog = m.find_bads_eog(raw, ch_name=["Fp1", "Fp2"], threshold=3.0, verbose="error")
    buang = list(eog)
    info = dict(detik_fit=round(float(semua_ok.sum() / sf), 1), komponen_mata=list(map(int, eog)))
    if otot:
        mus, _ = m.find_bads_muscle(raw, threshold=0.5, l_freq=7, h_freq=34, verbose="error")
        buang = sorted(set(buang) | set(mus))
        info["komponen_otot"] = list(map(int, mus))
    raw.set_annotations(None)
    y = xa.copy()
    if buang:
        m.exclude = buang
        yc = m.apply(raw.copy(), verbose="error").get_data() * 1e6
        y[:, semua_ok] = yc[:, semua_ok]
    info["pct_waktu_dikoreksi"] = round(100 * float(semua_ok.mean()), 1)
    return y, info


def regresi_mata(xa, datar, sf, W):
    """→ (x terkoreksi, datar baru dengan Fp1/Fp2 = datar penuh, info)."""
    sos = butter(4, [1, 7], btype="band", fs=sf, output="sos")
    fpok = ~datar[FP]                                    # 2 × sampel
    fpf = sosfiltfilt(sos, xa[FP], axis=1)
    n_ok = fpok.sum(axis=0)
    e = np.where(n_ok > 0, (fpf * fpok).sum(axis=0) / np.maximum(n_ok, 1), 0.0)
    ist = np.zeros(xa.shape[1], bool)
    for w in W[W.fase == "Istirahat"].itertuples():
        ist[int(w.mulai * sf):int(w.selesai * sf)] = True
    y = xa.copy()
    b = np.zeros(len(KANAL))
    for k in range(len(KANAL)):
        if k in FP:
            continue
        m = ist & ~datar[k] & (n_ok > 0)
        if m.sum() > 10 * sf:
            b[k] = np.dot(xa[k, m], e[m]) / np.dot(e[m], e[m])
            y[k] -= b[k] * e
    d2 = datar.copy()
    d2[FP] = True                                        # Fp1/Fp2 menjadi kanal EOG, tidak dianalisis
    return y, d2, dict(koef_median=round(float(np.median(np.abs(b[b != 0]))), 3) if (b != 0).any() else 0.0)


def _cca(x):
    """BSS-CCA: → (W unmixing k×k, rho menurun). x: kanal × sampel."""
    Y, Z = x[:, 1:], x[:, :-1]
    Y = Y - Y.mean(axis=1, keepdims=True)
    Z = Z - Z.mean(axis=1, keepdims=True)
    n = Y.shape[1]
    Cyy, Czz, Cyz = Y @ Y.T / n, Z @ Z.T / n, Y @ Z.T / n
    reg = 1e-6 * np.trace(Cyy) / len(Cyy)
    iy = np.linalg.inv(Cyy + reg * np.eye(len(Cyy)))
    iz = np.linalg.inv(Czz + reg * np.eye(len(Czz)))
    ev, V = np.linalg.eig(iy @ Cyz @ iz @ Cyz.T)
    o = np.argsort(-ev.real)
    return V[:, o].real, np.sqrt(np.clip(ev.real[o], 0, 1))


def _rasio_otot(s, sf):
    f, p = welch(s, sf, nperseg=s.shape[-1])
    return p[:, (f >= 20) & (f <= 34)].mean(axis=1) / (p[:, (f >= 2) & (f <= 15)].mean(axis=1) + 1e-12)


def cca_ambang(xa, datar, sf, W, rujuk):
    """Persentil 95 rasio otot komponen CCA pada jendela Istirahat 1 dtk (sesudah `rujuk`)."""
    r = []
    for w in W[W.fase == "Istirahat"].itertuples():
        for s in np.arange(w.mulai, w.selesai - 1.0 + 1e-9, 1.0):
            i0 = int(round(s * sf))
            x, fd = rujuk(xa[:, i0:i0 + int(sf)], datar[:, i0:i0 + int(sf)].mean(axis=1))
            g = np.where(fd < DATAR_BATAS)[0]
            if len(g) >= 4:
                Wm, _ = _cca(x[g])
                r += list(_rasio_otot(Wm.T @ x[g], sf))
    return float(np.percentile(r, 95)) if r else np.inf


def cca_otot(x, fd, sf, ambang):
    """Buang komponen CCA mirip otot dari kanal tidak-datar satu jendela."""
    g = np.where(fd < DATAR_BATAS)[0]
    if len(g) < 4 or not np.isfinite(ambang):
        return x
    Wm, _ = _cca(x[g])
    S = Wm.T @ x[g]
    rr = _rasio_otot(S, sf)
    buang = np.where(rr > ambang)[0]
    buang = buang[np.argsort(-rr[buang])][:len(g) // 2]
    if not len(buang):
        return x
    A = np.linalg.pinv(Wm.T)
    S[buang] = 0
    y = x.copy()
    y[g] = A @ S
    return y


def rujuk_dengan_cca(rujuk, sf, ambang):
    def f(x, fd):
        y, fd2 = rujuk(x, fd)
        return cca_otot(y, fd2, sf, ambang), fd2
    return f
