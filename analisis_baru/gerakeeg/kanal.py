"""Tahap 3: kanal buruk & sinyal datar, di atas referensi A (rata-rata per belahan) dan epoch TE.

Varian (semuanya fungsi (x, fd) → (x', fd') per jendela; fd = fraksi datar per kanal, fd' = 1 → kanal hilang):
  A0_dasar      : referensi A apa adanya (hasil Tahap 2).
  A1_rekaman    : kanal buruk PER REKAMAN (z robust log-SD saat Istirahat > 3, atau datar > 50% rekaman) dibuang dari
                  referensi dan analisis di seluruh rekaman.
  A2_robust     : kanal buruk PER JENDELA — iteratif: referensi = rata-rata kanal baik di belahan; kanal yang
                  peak-to-peak-nya pencilan (z robust log-ptp > 3 DAN > 2× median belahan) dikeluarkan dari
                  referensi dan ditandai hilang di jendela itu; ulang sampai stabil (maks. 3 kali).
  A3_median     : referensi = MEDIAN kanal tidak-datar di belahan (kebal pencilan tanpa membuang kanal).
  A4_robust_int : A2 + interpolasi spline sferis di DALAM belahan untuk kanal hilang (datar/pencilan) bila
                  ≥ 5 dari 8 kanal belahan baik. Kanal hasil interpolasi ditandai (fd = TANDA_INTERP); isinya
                  turunan kanal tetangga, bukan informasi baru.
"""
import numpy as np

from .istilah import KANAL, KANAN, KIRI

IDX = {c: i for i, c in enumerate(KANAL)}
BELAHAN = [np.array([IDX[c] for c in KIRI]), np.array([IDX[c] for c in KANAN])]
DATAR = 0.10
VARIAN = ["A0_dasar", "A1_rekaman", "A2_robust", "A3_median", "A4_robust_int"]


def _z(v):
    med = np.median(v)
    mad = 1.4826 * np.median(np.abs(v - med))
    return (v - med) / mad if mad > 0 else np.zeros_like(v)


def rata_belahan(x, fd, buruk=()):
    y, fd = x.copy(), fd.copy()
    fd[list(buruk)] = 1.0
    for g in BELAHAN:
        gg = g[fd[g] < DATAR]
        if len(gg) >= 2:
            y[g] = x[g] - x[gg].mean(axis=0)
        else:
            fd[g] = 1.0
    return y, fd


def robust(x, fd, z_batas=3.0, iterasi=3):
    y, fd = x.copy(), fd.copy()
    for g in BELAHAN:
        baik = g[fd[g] < DATAR]
        for _ in range(iterasi):
            if len(baik) < 3:
                break
            r = x[baik].mean(axis=0)
            pp = np.ptp(x[baik] - r, axis=1)
            # pencilan = z robust > batas DAN > 2× median: MAD sangat kecil bila kanal tersisa seragam
            keluar = baik[(_z(np.log(pp + 1e-6)) > z_batas) & (pp > 2 * np.median(pp))]
            if not len(keluar):
                break
            baik = np.setdiff1d(baik, keluar)
        hilang = np.setdiff1d(g, baik)
        fd[hilang] = np.maximum(fd[hilang], 1.0)
        if len(baik) >= 2:
            y[g] = x[g] - x[baik].mean(axis=0)
        else:
            fd[g] = 1.0
    return y, fd


def median_belahan(x, fd):
    y, fd = x.copy(), fd.copy()
    for g in BELAHAN:
        gg = g[fd[g] < DATAR]
        if len(gg) >= 3:
            y[g] = x[g] - np.median(x[gg], axis=0)
        else:
            fd[g] = 1.0
    return y, fd


_MAT, _POS = {}, None
TANDA_INTERP = -0.01          # fd kanal hasil interpolasi (< 0: dianggap tidak datar, dapat dikenali)


def _matriks(dari, ke):
    key = (tuple(dari), tuple(ke))
    global _POS
    if key not in _MAT:
        import mne
        from mne.channels.interpolation import _make_interpolation_matrix
        if _POS is None:
            pos = mne.channels.make_standard_montage("standard_1020").get_positions()["ch_pos"]
            _POS = np.array([pos[c] for c in KANAL])
        _MAT[key] = _make_interpolation_matrix(_POS[list(dari)], _POS[list(ke)])
    return _MAT[key]


def robust_interp(x, fd):
    """A2 lalu interpolasi di dalam belahan. fd kanal terinterpolasi = TANDA_INTERP (dianggap tidak datar)."""
    y, fd2 = robust(x, fd)
    for g in BELAHAN:
        baik, hilang = g[fd2[g] < DATAR], g[fd2[g] >= DATAR]
        if len(hilang) and len(baik) >= 5:
            y[hilang] = _matriks(baik, hilang) @ y[baik]
            fd2[hilang] = TANDA_INTERP
    return y, fd2


def kanal_buruk_rekaman(xf, datar, sf, W, z_batas=3.0):
    """Kanal buruk per rekaman: z robust log-SD (jendela 2 dtk tidak-datar saat Istirahat) > z_batas, atau datar
    > 50% rekaman."""
    ist = W[W.fase == "Istirahat"]
    sd = []
    for w in ist.itertuples():
        for s in np.arange(w.mulai, w.selesai - 2, 2.0):
            i0 = int(s * sf)
            i1 = i0 + int(2 * sf)
            ok = datar[:, i0:i1].mean(axis=1) < DATAR
            sd.append(np.where(ok, xf[:, i0:i1].std(axis=1), np.nan))
    lsd = np.log(np.nanmedian(np.array(sd), axis=0))
    z = _z(lsd[np.isfinite(lsd)])
    zz = np.full(len(KANAL), np.nan)
    zz[np.isfinite(lsd)] = z
    buruk = [k for k in range(len(KANAL)) if (np.isfinite(zz[k]) and zz[k] > z_batas) or datar[k].mean() > 0.5]
    return buruk, zz


def pembuat(varian, buruk_rekaman=()):
    """→ fungsi (x, fd) → (x', fd') untuk dipakai epoch._potong."""
    if varian == "A0_dasar":
        return lambda x, fd: rata_belahan(x, fd)
    if varian == "A1_rekaman":
        return lambda x, fd: rata_belahan(x, fd, buruk_rekaman)
    if varian == "A2_robust":
        return robust
    if varian == "A3_median":
        return median_belahan
    if varian == "A4_robust_int":
        return robust_interp
    raise ValueError(varian)
