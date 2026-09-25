"""Bagian fase mana yang memberi gambaran EEG terbaik: pra-onset, awal, tengah, akhir.

Tiap fase repetisi [onset, onset berikut] dibagi tiga sama panjang (awal/tengah/akhir) + pra-onset
[onset − 0,5, onset]. Jendela pendek diletakkan sepanjang rekaman dan dimasukkan ke bagian menurut PUSATnya:
- kualitas : jendela 0,5 dtk, geser 0,125 dtk → % bersih (datar < 10% dan peak-to-peak ≤ 150 µV)
- spektrum : jendela 1,0 dtk, geser 0,25 dtk → power (dB relatif Istirahat):
    delta 1–4 Hz dan otot 20–34 Hz = indeks kontaminasi (semua jendela tidak datar, semua kanal);
    mu 8–13 Hz dan beta 13–30 Hz di C3/C4 = sinyal sensorimotor (hanya jendela bersih).
  Jendela 1 dtk melebar ±0,5 dtk di sekitar pusat → pada fase pendek (Naik ≈ 2 dtk) bagian bertetangga
  saling bercampur; tafsirkan sebagai profil kasar.
Konsistensi sinyal: rata-rata antar-repetisi / galat baku (t) per bagian, bila ≥ 3 repetisi.
Bias seleksi metode E: dari jendela E (1 dtk, seluruhnya di dalam jendela observasi fase), bandingkan porsi
jendela BERSIH per bagian dengan porsi SEMUA jendela per bagian.
"""
import numpy as np
import pandas as pd
from scipy.signal import welch

from .istilah import FASE_REPETISI, ISTIRAHAT, KANAL
from .kualitas import DATAR_BATAS, EKSTREM_UV

BAGIAN = ["pra-onset", "awal", "tengah", "akhir"]
SM = [KANAL.index("C3"), KANAL.index("C4")]
PITA = {"delta": (1, 4), "mu": (8, 13), "beta": (13, 30), "otot": (20, 34)}


def _bagian(c, mulai_obs, onset, selesai):
    if c < mulai_obs or c >= selesai:
        return None
    if c < onset:
        return "pra-onset"
    return BAGIAN[1 + min(2, int(3 * (c - onset) / (selesai - onset)))]


def _jendela(W, T, panjang, geser):
    """Semua jendela [s, s+panjang] yang pusatnya jatuh di jendela observasi fase repetisi → baris berlabel."""
    rows = []
    for w in W[W.fase.isin(FASE_REPETISI)].itertuples():
        s0 = np.arange(max(0.0, w.mulai - panjang / 2), min(T - panjang, w.selesai), geser)
        for s in s0:
            b = _bagian(s + panjang / 2, w.mulai, w.onset, w.selesai)
            if b:
                rows.append((w.gerakan, w.rep, w.fase, b, s, s >= w.mulai - 1e-9 and s + panjang <= w.selesai + 1e-9))
    return pd.DataFrame(rows, columns=["gerakan", "rep", "fase", "bagian", "mulai", "dalam_fase"])


def _bersih(xf, datar, i0, i1):
    return (datar[:, i0:i1].mean(axis=1) < DATAR_BATAS) & (np.ptp(xf[:, i0:i1], axis=1) <= EKSTREM_UV)


def _pw(x, sf):
    f, p = welch(x, sf, nperseg=x.shape[-1])
    return {b: p[:, (f >= lo) & (f < hi)].mean(axis=1) for b, (lo, hi) in PITA.items()}


def profil(pid, xf, datar, sf, W):
    T = xf.shape[1] / sf
    # acuan Istirahat: jendela 1 dtk bersih
    ref = {b: [] for b in PITA}
    for w in W[W.fase == ISTIRAHAT].itertuples():
        for s in np.arange(w.mulai, w.selesai - 1.0, 0.25):
            i0, i1 = int(round(s * sf)), int(round((s + 1) * sf))
            ok = _bersih(xf, datar, i0, i1)
            p = _pw(xf[:, i0:i1], sf)
            for b in PITA:
                ref[b].append(np.where(ok, p[b], np.nan))
    ref = {b: np.nanmean(np.array(v), axis=0) for b, v in ref.items()}

    # kualitas: 0,5 dtk
    q = _jendela(W, T, 0.5, 0.125)
    Q = []
    for r in q.itertuples():
        i0 = int(round(r.mulai * sf))
        Q.append(_bersih(xf, datar, i0, i0 + int(0.5 * sf)).mean())
    q["pct_bersih"] = 100 * np.array(Q)

    # spektrum: 1 dtk
    s = _jendela(W, T, 1.0, 0.25)
    rows = []
    for r in s.itertuples():
        i0 = int(round(r.mulai * sf))
        i1 = i0 + int(sf)
        ok = _bersih(xf, datar, i0, i1)
        nd = datar[:, i0:i1].mean(axis=1) < DATAR_BATAS
        p = _pw(xf[:, i0:i1], sf)
        db = {b: 10 * np.log10(p[b] / ref[b]) for b in PITA}
        rows.append(dict(delta_db=np.nanmedian(np.where(nd, db["delta"], np.nan)),
                         otot_db=np.nanmedian(np.where(nd, db["otot"], np.nan)),
                         mu_sm_db=np.nanmean(np.where(ok[SM], db["mu"][SM], np.nan)),
                         beta_sm_db=np.nanmean(np.where(ok[SM], db["beta"][SM], np.nan)),
                         pct_kanal_bersih=100 * ok.mean(), sm_bersih=bool(ok[SM].any())))
    s = pd.concat([s.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    return q.assign(participant_id=pid), s.assign(participant_id=pid)


def ringkas(Q, S):
    k = ["participant_id", "fase", "bagian"]
    a = Q.groupby(k).pct_bersih.mean().rename("pct_bersih_05dtk")
    b = S.groupby(k)[["delta_db", "otot_db"]].median()
    # sinyal sensorimotor: per repetisi (rata-rata linear jendela bersih), lalu antar-repetisi
    lin = lambda v: 10 * np.log10(np.nanmean(10 ** (v / 10))) if np.isfinite(v).any() else np.nan
    per_rep = S[S.sm_bersih].groupby(k + ["gerakan", "rep"])[["mu_sm_db", "beta_sm_db"]].agg(lin).reset_index()

    def _t(v):
        v = v.dropna()
        return v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) >= 3 and v.std(ddof=1) > 0 else np.nan
    c = per_rep.groupby(k).agg(mu_sm_db=("mu_sm_db", "mean"), mu_sm_t=("mu_sm_db", _t),
                               beta_sm_db=("beta_sm_db", "mean"), beta_sm_t=("beta_sm_db", _t),
                               n_rep_sm=("mu_sm_db", lambda v: v.notna().sum()))
    # bias seleksi E: porsi bersih vs porsi semua, di antara jendela E (seluruhnya di dalam jendela observasi)
    e = S[S.dalam_fase]
    semua = e.groupby(k).size() / e.groupby(["participant_id", "fase"]).size()
    bersih = (e.assign(w=e.pct_kanal_bersih / 100).groupby(k).w.sum()
              / e.assign(w=e.pct_kanal_bersih / 100).groupby(["participant_id", "fase"]).w.sum())
    d = pd.DataFrame({"porsi_E_semua": 100 * semua, "porsi_E_bersih": 100 * bersih})
    out = pd.concat([a, b, c, d], axis=1).reset_index()
    out["bagian"] = pd.Categorical(out.bagian, BAGIAN, ordered=True)
    out["fase"] = pd.Categorical(out.fase, FASE_REPETISI, ordered=True)
    return out.sort_values(["participant_id", "fase", "bagian"])
