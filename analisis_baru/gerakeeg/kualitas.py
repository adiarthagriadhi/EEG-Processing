"""Tahap 1: inventaris kualitas sinyal per jendela observasi (tanpa mengubah data).

Sinyal:
- EDF mentah → penanda DATAR (SD < 0,5 µV dalam blok 0,2 dtk; reset/putus kanal KT88) dan clipping (|x| > 3000 µV).
- Bandpass 1–35 Hz (FIR fase-nol; perangkat sudah LP ≈ 35 Hz) → amplitudo dan spektrum.
Per jendela observasi × kanal, jendela dipotong per 1 dtk (geser 0,5 dtk; jendela < 1 dtk = satu potongan utuh):
    datar    ≥ 10% sampel potongan datar
    ekstrem  peak-to-peak > 150 µV
    tinggi   100–150 µV
    ok       sisanya
Ringkasan per jendela × kanal:
    layak_ketat : datar ≤ 10% jendela DAN peak-to-peak seluruh jendela ≤ 150 µV (aturan tolak konvensional);
                  hanya untuk fase repetisi (Gerak/Tahan/Naik/Berdiri), karena bergantung panjang jendela
    delta_db / emg_db : power 1–4 Hz / 20–34 Hz relatif median Istirahat kanal yang sama
Per jendela: korelasi rata-rata antar-kanal dalam belahan kiri, kanan, dan antar-belahan (kanal tidak datar),
penanda artefak bersama dari elektroda telinga A1/A2.
"""
import numpy as np
import pandas as pd
from scipy.signal import welch

from .istilah import BELAHAN, FASE_REPETISI, ISTIRAHAT, KANAL, KANAN, KIRI

DATAR_SD_UV, DATAR_BLOK_DTK, DATAR_BATAS = 0.5, 0.2, 0.10
EKSTREM_UV, TINGGI_UV, CLIP_UV = 150.0, 100.0, 3000.0
POT_DTK, GESER_DTK = 1.0, 0.5


def penanda_datar(x, sf):
    """x kanal × sampel (µV, mentah) → mask bool datar."""
    n = max(2, int(DATAR_BLOK_DTK * sf))
    k = x.shape[1] // n
    sd = x[:, :k * n].reshape(x.shape[0], k, n).std(axis=2)
    m = np.zeros(x.shape, bool)
    m[:, :k * n] = np.repeat(sd < DATAR_SD_UV, n, axis=1)
    return m


def sinyal(raw):
    """→ (x_mentah µV, x_1_35 µV, mask datar, sf)."""
    sf = raw.info["sfreq"]
    xm = raw.get_data() * 1e6
    xf = raw.copy().filter(1.0, 35.0, verbose="error").get_data() * 1e6
    return xm, xf, penanda_datar(xm, sf), sf


def _potongan(i0, i1, sf):
    n, g = int(POT_DTK * sf), int(GESER_DTK * sf)
    if i1 - i0 <= n:
        return [(i0, i1)]
    return [(a, a + n) for a in range(i0, i1 - n + 1, g)]


def _band(x, sf, lo, hi):
    f, p = welch(x, sf, nperseg=min(x.shape[-1], int(sf)))
    return p[:, (f >= lo) & (f <= hi)].mean(axis=1)


def _korelasi(x, ok):
    C = np.corrcoef(x)
    L = [i for i, c in enumerate(KANAL) if c in KIRI and ok[i]]
    R = [i for i, c in enumerate(KANAL) if c in KANAN and ok[i]]
    rata = lambda I, J: (np.nanmean([C[i, j] for i in I for j in J if i != j])
                         if len(I) and len(J) and (len(I) > 1 or I != J) else np.nan)
    return rata(L, L), rata(R, R), rata(L, R)


def inventaris(pid, raw, W, sumber="timestamp_manual"):
    """W: DataFrame jendela (mulai, selesai dalam detik EEG). → (per_potongan, per_jendela_kanal, per_jendela)."""
    xm, xf, datar, sf = sinyal(raw)
    T = xm.shape[1] / sf
    pot, jk, jw = [], [], []
    for w in W.itertuples():
        a, b = max(w.mulai, 0.0), min(w.selesai, T)
        cakupan = max(0.0, b - a) / (w.selesai - w.mulai)
        if b - a < 0.3:
            jw.append(dict(participant_id=pid, sumber=sumber, gerakan=w.gerakan, rep=w.rep, fase=w.fase,
                           mulai=w.mulai, selesai=w.selesai, cakupan=round(cakupan, 3)))
            continue
        i0, i1 = int(round(a * sf)), int(round(b * sf))
        x, d = xf[:, i0:i1], datar[:, i0:i1]
        for p0, p1 in _potongan(i0, i1, sf):
            ptp = np.ptp(xf[:, p0:p1], axis=1)
            fd = datar[:, p0:p1].mean(axis=1)
            lab = np.where(fd >= DATAR_BATAS, "datar", np.where(ptp > EKSTREM_UV, "ekstrem",
                           np.where(ptp > TINGGI_UV, "tinggi", "ok")))
            for k, c in enumerate(KANAL):
                pot.append((pid, sumber, w.gerakan, w.rep, w.fase, round(p0 / sf, 2), c, round(ptp[k], 1), lab[k]))
        fd = d.mean(axis=1)
        ptp = np.ptp(x, axis=1)
        clip = (np.abs(xm[:, i0:i1]) > CLIP_UV).any(axis=1)
        delta, emg = _band(x, sf, 1, 4), _band(x, sf, 20, 34)
        for k, c in enumerate(KANAL):
            jk.append(dict(participant_id=pid, sumber=sumber, gerakan=w.gerakan, rep=w.rep, fase=w.fase,
                           kanal=c, belahan=BELAHAN[c], datar_frac=round(fd[k], 3), ptp_uv=round(ptp[k], 1),
                           clipping=bool(clip[k]),
                           layak_ketat=(bool(fd[k] <= DATAR_BATAS and ptp[k] <= EKSTREM_UV)
                                        if w.fase in FASE_REPETISI else np.nan),
                           p_delta=delta[k], p_emg=emg[k]))
        rl, rr, rlr = _korelasi(x, fd <= DATAR_BATAS)
        jw.append(dict(participant_id=pid, sumber=sumber, gerakan=w.gerakan, rep=w.rep, fase=w.fase,
                       mulai=w.mulai, selesai=w.selesai, cakupan=round(cakupan, 3),
                       r_kiri=rl, r_kanan=rr, r_antar=rlr))
    pot = pd.DataFrame(pot, columns=["participant_id", "sumber", "gerakan", "rep", "fase", "t0", "kanal",
                                     "ptp_uv", "label"])
    jk = pd.DataFrame(jk)
    acuan = jk[jk.fase == ISTIRAHAT].groupby("kanal")[["p_delta", "p_emg"]].median()
    if len(acuan):
        for q, col in (("p_delta", "delta_db"), ("p_emg", "emg_db")):
            jk[col] = 10 * np.log10(jk[q] / jk.kanal.map(acuan[q]))
    jk = jk.drop(columns=["p_delta", "p_emg"])
    return pot, jk, pd.DataFrame(jw)


def ringkas(pot, jk, jw, kunci=("participant_id", "sumber", "fase")):
    k = list(kunci)
    a = (pot.groupby(k).label.value_counts(normalize=True).unstack(fill_value=0) * 100)
    a = a.reindex(columns=["ok", "tinggi", "ekstrem", "datar"], fill_value=0).add_prefix("pct_")
    a["n_potongan_kanal"] = pot.groupby(k).size()
    a["ptp_median_uv"] = pot[pot.label != "datar"].groupby(k).ptp_uv.median()     # per potongan 1 dtk
    b = jk.groupby(k).agg(pct_layak_ketat=("layak_ketat", lambda s: 100 * s.astype(float).mean()),
                          delta_db=("delta_db", "median"), emg_db=("emg_db", "median"),
                          clipping=("clipping", "sum"))
    c = jw.assign(panjang=jw.selesai - jw.mulai).groupby(k).agg(
                          n_jendela=("mulai", "size"), panjang_median_dtk=("panjang", "median"),
                          cakupan=("cakupan", "mean"),
                          r_kiri=("r_kiri", "median"), r_kanan=("r_kanan", "median"), r_antar=("r_antar", "median"))
    return a.join(b).join(c).reset_index()
