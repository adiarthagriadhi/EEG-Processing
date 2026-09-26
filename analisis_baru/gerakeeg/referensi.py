"""Tahap 2: skema referensi. Diterapkan PER JENDELA (1 dtk TE / acuan), sehingga kanal yang datar di jendela itu
(reset/putus KT88; ≥ 10% sampel datar) tidak ikut membentuk referensi dan tidak ada loncatan di dalam jendela.

D_telinga  : asli — kanal kiri − A1, kanan − A2 (referensi telinga ipsilateral).
A_belahan  : tiap kanal − rata-rata kanal tidak-datar di BELAHANNYA sendiri. Menghapus komponen yang sama di satu
             belahan (termasuk artefak A1/A2), tetapi juga aktivitas otak yang tersebar merata di belahan itu.
B_rata16   : tiap kanal − rata-rata semua kanal tidak-datar (common average). Tanpa kanal garis tengah; artefak A1 dan
             A2 hanya terhapus sebagian (masing-masing masuk ke separuh kanal).
C_bipolar  : 16 turunan bipolar longitudinal di dalam belahan (rantai tetangga). Referensi telinga hilang sepenuhnya;
             yang diukur menjadi beda potensial lokal.
"""
import numpy as np

from .istilah import KANAL, KANAN, KIRI

BIPOLAR = [("Fp1", "F3"), ("F3", "C3"), ("C3", "P3"), ("P3", "O1"), ("Fp1", "F7"), ("F7", "T3"), ("T3", "T5"),
           ("T5", "O1"),
           ("Fp2", "F4"), ("F4", "C4"), ("C4", "P4"), ("P4", "O2"), ("Fp2", "F8"), ("F8", "T4"), ("T4", "T6"),
           ("T6", "O2")]
SKEMA = ["D_telinga", "A_belahan", "B_rata16", "C_bipolar"]
IDX = {c: i for i, c in enumerate(KANAL)}
IL, IR = [IDX[c] for c in KIRI], [IDX[c] for c in KANAN]


def nama(skema):
    return [f"{a}-{b}" for a, b in BIPOLAR] if skema == "C_bipolar" else list(KANAL)


def belahan(skema):
    """Belahan tiap turunan (urutan sama dengan nama())."""
    return ["kiri"] * 8 + ["kanan"] * 8


def terapkan(skema, x, fd, batas=0.10):
    """x: 16 × n (µV, urutan KANAL), fd: fraksi datar per kanal. → (x', fd') dengan 16 turunan."""
    ok = fd < batas
    if skema == "D_telinga":
        return x, fd
    if skema == "C_bipolar":
        a = [IDX[p] for p, _ in BIPOLAR]
        b = [IDX[q] for _, q in BIPOLAR]
        return x[a] - x[b], np.maximum(fd[a], fd[b])
    y = x.copy()
    groups = [IL, IR] if skema == "A_belahan" else [IL + IR]
    for g in groups:
        g = np.array(g)
        gg = g[ok[g]]
        if len(gg) >= 2:
            y[g] = x[g] - x[gg].mean(axis=0)
        else:                                   # < 2 kanal tidak-datar: referensi tidak terdefinisi
            fd = fd.copy()
            fd[g] = 1.0
    return y, fd


OKSIPITAL = {"C_bipolar": ["P3-O1", "T5-O1", "P4-O2", "T6-O2"]}


def evaluasi_tambahan(pid, xf, datar, sf, W, eTE, skema, ref):
    """Per fase: korelasi dalam/antar belahan dan % bersih per belahan (jendela TE); efek Berger (alpha oksipital
    Tutup Mata vs Istirahat)."""
    import pandas as pd

    from .epoch import _potong, _power
    from .istilah import TUTUP_MATA
    nm, bl = nama(skema), np.array(belahan(skema))
    rows = []
    for e in eTE.itertuples():
        i0, i1 = int(round(e.mulai * sf)), int(round(e.selesai * sf))
        if i1 > xf.shape[1]:
            continue
        x, nd, ok = _potong(xf, datar, i0, i1, skema)
        L, R = np.where(nd & (bl == "kiri"))[0], np.where(nd & (bl == "kanan"))[0]
        C = np.corrcoef(x) if nd.sum() >= 2 else None
        rata = lambda I, J: (np.nanmean([C[i, j] for i in I for j in J if i != j])
                             if C is not None and len(I) and len(J) and len(set(I) | set(J)) > 1 else np.nan)
        rows.append(dict(participant_id=pid, skema=skema, fase=e.fase, r_kiri=rata(L, L), r_kanan=rata(R, R),
                         r_antar=rata(L, R), bersih_kiri=ok[bl == "kiri"].mean(), bersih_kanan=ok[bl == "kanan"].mean()))
    kor = pd.DataFrame(rows).groupby(["participant_id", "skema", "fase"]).median().reset_index()
    # Berger: alpha 8–13 Hz oksipital, Tutup Mata (TT + 1 … TT + 30) vs acuan Istirahat
    occ = [nm.index(c) for c in OKSIPITAL.get(skema, ["O1", "O2"])]
    tm = W[W.fase == TUTUP_MATA]
    rel = lambda P, k: P["mu"][k] / ((4 * P["theta"][k] + 5 * P["mu"][k] + 17 * P["beta"][k]) / 26)
    vals, vrel = [], []
    for w in tm.itertuples():
        for s in np.arange(w.onset + 1.0, min(w.selesai, xf.shape[1] / sf) - 1.0 + 1e-9, 0.25):
            i0 = int(round(s * sf))
            x, nd, ok = _potong(xf, datar, i0, i0 + int(sf), skema)
            P = _power(x, sf)
            v = [10 * np.log10(P["mu"][k] / ref["mu"][k]) for k in occ if ok[k]]
            if v:
                vals.append(np.mean(v))
                vrel.append(np.mean([10 * np.log10(rel(P, k) / rel(ref, k)) for k in occ if ok[k]]))
    # t memakai n efektif = n/4 (jendela 1 dtk bergeser 0,25 dtk saling tumpang tindih)
    tt = lambda v: np.mean(v) / (np.std(v, ddof=1) / np.sqrt(len(v) / 4)) if len(v) > 8 else np.nan
    ber = dict(participant_id=pid, skema=skema, berger_alpha_occ_db=np.mean(vals) if vals else np.nan,
               berger_alpha_rel_db=np.mean(vrel) if vrel else np.nan, berger_n_jendela=len(vals),
               berger_t=tt(vals), berger_rel_t=tt(vrel))
    return kor, ber
