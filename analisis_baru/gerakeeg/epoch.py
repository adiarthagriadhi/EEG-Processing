"""Perbandingan cara epoching (belum ada koreksi artefak; dinilai pada sinyal 1–35 Hz apa adanya).

T  epoch TERARAH 1,5 dtk di bagian fase yang paling informatif (hasil analisis bagian fase):
   Gerak & Naik = inisiasi [onset − 0,5, onset + 1,0] (sama dengan B); Tahan = 1,5 dtk di TENGAH fase
   (butuh Tahan ≥ 1,5 dtk); Berdiri = [akhir − 2,0, akhir − 0,5] dengan akhir = Gerak berikutnya atau B + 8
   (butuh Berdiri ≥ 2,0 dtk).

B  epoch tetap 1,5 dtk per fase: [onset − 0,5, onset + 1,0]. Fase < 1,0 dtk → epoch akan melewati batas fase
   → tidak dipakai (dicatat).
TE jendela geser E yang dibatasi pada bagian informatif (gabungan T + E): Gerak & Naik [onset − 0,5,
   onset + maks(1,0; durasi/3)]; Tahan [onset + durasi/3, onset berikut] (tengah + akhir); Berdiri
   [onset + durasi/3, akhir − 0,5] (tengah + akhir, sebelum pra-onset Gerak berikutnya).
E  jendela geser 1,0 dtk, geser 0,25 dtk, sepanjang rekaman. Jendela diberi label fase bila seluruhnya berada di
   dalam jendela observasi fase itu ([onset − 0,5, onset berikut]); jendela yang melintasi batas fase dibuang.
   Estimasi per repetisi × fase = rata-rata power jendela bersih di dalamnya.

Aturan bersih (sama untuk keduanya, per kanal): datar < 10% sampel DAN peak-to-peak ≤ 150 µV dalam epoch/jendela.
Power: Welch (Hann, segmen 1 dtk, geser 0,5 dtk), rata-rata bin pita theta 4–8, mu 8–13, beta 13–30 Hz,
dB relatif acuan Istirahat yang dipotong dengan cara yang sama (B: epoch 1,5 dtk tanpa tumpang tindih; E: jendela
geser 1 dtk) — hanya potongan bersih.
Unit independen = repetisi (jendela E yang saling tumpang tindih tidak dihitung sebagai sampel terpisah).
"""
import numpy as np
import pandas as pd
from scipy.signal import welch

from .istilah import FASE_REPETISI, ISTIRAHAT, KANAL
from .kualitas import DATAR_BATAS, EKSTREM_UV

PITA = {"theta": (4, 8), "mu": (8, 13), "beta": (13, 30)}
OTOT = (20, 34)                      # indeks kontaminasi otot (semua potongan tidak datar)
TOTAL4 = (4, 31)                     # penyebut M2b: power total 4–30 Hz (bin 1 Hz, tanpa delta)
B_PRA, B_PANJANG = 0.5, 1.5
E_PANJANG, E_GESER = 1.0, 0.25


def _power(x, sf):
    """x kanal × sampel → dict pita → power (kanal)."""
    f, p = welch(x, sf, nperseg=int(sf), noverlap=int(sf) // 2)
    return {b: p[:, (f >= lo) & (f < hi)].mean(axis=1) for b, (lo, hi) in {**PITA, "otot": OTOT, "total4": TOTAL4}.items()}


def _bersih(xf, datar, i0, i1):
    return (datar[:, i0:i1].mean(axis=1) < DATAR_BATAS) & (np.ptp(xf[:, i0:i1], axis=1) <= EKSTREM_UV)


def _potong(xf, datar, i0, i1, skema, ambang=None):
    """Potongan [i0, i1) dengan skema referensi (None = asli). → (x, tidak_datar, bersih)."""
    x, fd = xf[:, i0:i1], datar[:, i0:i1].mean(axis=1)
    if callable(skema):                                   # Tahap 3: fungsi (x, fd) → (x', fd')
        x, fd = skema(x, fd)
    elif skema is not None:
        from .referensi import terapkan
        x, fd = terapkan(skema, x, fd)
    nd = fd < DATAR_BATAS
    return x, nd, nd & (np.ptp(x, axis=1) <= (EKSTREM_UV if ambang is None else ambang))


def potong_B(W):
    """Epoch B dari jendela observasi fase repetisi."""
    out = []
    for w in W[W.fase.isin(FASE_REPETISI)].itertuples():
        a = w.onset - B_PRA
        out.append(dict(gerakan=w.gerakan, rep=w.rep, fase=w.fase, mulai=a, selesai=a + B_PANJANG,
                        muat=w.durasi_fase >= B_PANJANG - B_PRA))
    return pd.DataFrame(out)


def potong_T(W):
    """Epoch terarah (lihat docstring modul)."""
    out = []
    for w in W[W.fase.isin(FASE_REPETISI)].itertuples():
        d = w.durasi_fase
        if w.fase in ("Gerak", "Naik"):
            a, muat = w.onset - B_PRA, d >= B_PANJANG - B_PRA
        elif w.fase == "Tahan":
            a, muat = w.onset + d / 2 - B_PANJANG / 2, d >= B_PANJANG
        else:                                   # Berdiri: berakhir 0,5 dtk sebelum Gerak berikutnya / B + 8
            a, muat = w.selesai - 0.5 - B_PANJANG, d >= B_PANJANG + 0.5
        out.append(dict(gerakan=w.gerakan, rep=w.rep, fase=w.fase, mulai=a, selesai=a + B_PANJANG, muat=muat))
    return pd.DataFrame(out)


def rentang_terarah(w):
    d = w.durasi_fase
    if w.fase in ("Gerak", "Naik"):
        return w.onset - B_PRA, w.onset + max(1.0, d / 3)
    if w.fase == "Tahan":
        return w.onset + d / 3, w.selesai
    return w.onset + d / 3, w.selesai - 0.5


def potong_TE(W, T):
    t = np.arange(0, T - E_PANJANG + 1e-9, E_GESER)
    out = []
    for w in W[W.fase.isin(FASE_REPETISI)].itertuples():
        a, b = rentang_terarah(w)
        k = t[(t >= a - 1e-9) & (t + E_PANJANG <= b + 1e-9)]
        out += [dict(gerakan=w.gerakan, rep=w.rep, fase=w.fase, mulai=x, selesai=x + E_PANJANG) for x in k]
    return pd.DataFrame(out)


# Skema TR (jendela berdasar rujukan, 2026-09-26; RUJUKAN.md bagian B):
# - Pra-Gerak [onset − 2, onset]: ERD mu mulai ±2 dtk, beta ±1,5 dtk sebelum onset (Pfurtscheller & Lopes da Silva
#   1999). Fase tersendiri, bukan digabung ke Gerak: pilot menunjukkan penggabungan mengencerkan ERD eksekusi.
# - Gerak   [onset − 0,5, onset + maks(1; durasi/3)]: sama dengan TE; awal eksekusi paling informatif (Erbil &
#   Ungan 2007). Bertumpang 0,5 dtk dengan Pra-Gerak.
# - Tahan   [onset + durasi/3, Naik]: sama dengan TE (beta tonik saat menahan; Kilavik dkk. 2013).
# - Naik    [onset − 0,5, onset + maks(1; durasi/3)]: sama dengan TE. Tidak dimajukan 2 dtk karena akan memakan
#   jendela Tahan (persiapan Naik terjadi di dalam Tahan).
# - Pasca-Naik [B + 0,5, B + 2,5]: rebound beta sesudah gerak berhenti (Kilavik dkk. 2013).
# - Berdiri [B + 2,5, akhir − 2]: sesudah rebound dan sebelum persiapan Gerak berikutnya (tanpa tumpang tindih).
TR_PRA_GERAK = 2.0
TR_REBOUND = (0.5, 2.5)
PRA_GERAK, PASCA_NAIK = "Pra-Gerak", "Pasca-Naik"
FASE_TR = [PRA_GERAK, "Gerak", "Tahan", "Naik", PASCA_NAIK, "Berdiri"]


def rentang_rujukan(w):
    d = w.durasi_fase
    if w.fase in ("Gerak", "Naik"):
        return w.onset - B_PRA, w.onset + max(1.0, d / 3)
    if w.fase == "Tahan":
        return w.onset + d / 3, w.selesai
    return w.onset + TR_REBOUND[1], w.selesai - TR_PRA_GERAK


def potong_TR(W, T):
    """Jendela 1 dtk geser 0,25 dtk menurut skema TR. Kolom `relatif` = awal jendela − onset fase (dtk)."""
    t = np.arange(0, T - E_PANJANG + 1e-9, E_GESER)
    out = []
    for w in W[W.fase.isin(FASE_REPETISI)].itertuples():
        bag = [(w.fase, *rentang_rujukan(w))]
        if w.fase == "Gerak":
            bag.append((PRA_GERAK, w.onset - TR_PRA_GERAK, w.onset))
        if w.fase == "Berdiri":
            bag.append((PASCA_NAIK, w.onset + TR_REBOUND[0], min(w.onset + TR_REBOUND[1], w.selesai)))
        for f, a, b in bag:
            k = t[(t >= a - 1e-9) & (t + E_PANJANG <= b + 1e-9)]
            out += [dict(gerakan=w.gerakan, rep=w.rep, fase=f, mulai=x, selesai=x + E_PANJANG, relatif=x - w.onset)
                    for x in k]
    return pd.DataFrame(out)


POTONG = {"TE": potong_TE, "TR": potong_TR}


def potong_E(W, T):
    """Jendela geser E; label fase bila jendela seluruhnya di dalam satu jendela observasi."""
    F = W[W.fase.isin(FASE_REPETISI)].sort_values("mulai")
    t = np.arange(0, T - E_PANJANG + 1e-9, E_GESER)
    out, lintas = [], 0
    for w in F.itertuples():
        k = t[(t >= w.mulai - 1e-9) & (t + E_PANJANG <= w.selesai + 1e-9)]
        out += [dict(gerakan=w.gerakan, rep=w.rep, fase=w.fase, mulai=s, selesai=s + E_PANJANG) for s in k]
    return pd.DataFrame(out)


def acuan(xf, datar, sf, W, panjang, geser, skema=None, ambang=None):
    """Power acuan per kanal (rata-rata potongan bersih Istirahat)."""
    ist = W[W.fase == ISTIRAHAT]
    P = {b: [] for b in list(PITA) + ["otot", "total4"]}
    M = []
    for w in ist.itertuples():
        for s in np.arange(w.mulai, w.selesai - panjang + 1e-9, geser):
            i0, i1 = int(round(s * sf)), int(round((s + panjang) * sf))
            if i1 > xf.shape[1]:
                break
            x, _, ok = _potong(xf, datar, i0, i1, skema, ambang)
            pw = _power(x, sf)
            for b in P:
                P[b].append(np.where(ok, pw[b], np.nan))
            M.append(ok)
    return {b: np.nanmean(np.array(v), axis=0) for b, v in P.items()}, np.array(M).mean(axis=0)


def estimasi(xf, datar, sf, epochs, ref, metode, skema=None, ambang=None):
    """Per epoch/jendela: bersih per kanal + power dB relatif acuan. → baris panjang (repetisi × fase × kanal)."""
    rows = []
    for e in epochs.itertuples():
        i0, i1 = int(round(e.mulai * sf)), int(round(e.selesai * sf))
        if i0 < 0 or i1 > xf.shape[1]:
            continue
        x, nd, ok = _potong(xf, datar, i0, i1, skema, ambang)
        pw = _power(x, sf)
        from .referensi import nama
        for k, c in enumerate(nama(skema) if skema else KANAL):
            r = dict(metode=metode, gerakan=e.gerakan, rep=e.rep, fase=e.fase, mulai=e.mulai, kanal=c,
                     bersih=bool(ok[k]), muat=getattr(e, "muat", True),
                     otot_db=10 * np.log10(pw["otot"][k] / ref["otot"][k]) if nd[k] else np.nan)
            for b in list(PITA) + ["total4"]:
                r[f"{b}_db"] = 10 * np.log10(pw[b][k] / ref[b][k]) if ok[k] else np.nan
            rows.append(r)
    return pd.DataFrame(rows)


def per_repetisi(est):
    """Satu nilai per repetisi × fase × kanal. E: rata-rata power (linear) jendela bersih; B: epoch itu sendiri."""
    d = est[est.muat & est.bersih].copy()
    g = d.groupby(["metode", "gerakan", "rep", "fase", "kanal"])
    lin = {f"{b}_db": g[f"{b}_db"].apply(lambda v: 10 * np.log10(np.mean(10 ** (v / 10)))) for b in PITA}
    out = pd.DataFrame(lin)
    out["n_potongan"] = g.size()
    return out.reset_index()


def ringkas(pid, W, epochs, est, rep):
    """Ukuran per metode × fase: hasil (yield), cakupan fase, kontaminasi otot, presisi, reliabilitas belah-dua.
    epochs: {"B": df, "T": df, "E": df} (B/T = epoch tetap 1,5 dtk; E = jendela geser)."""
    rows = []
    kan = list(dict.fromkeys(est.kanal))
    for m, ep in epochs.items():
        for f in FASE_REPETISI:
            e = est[(est.metode == m) & (est.fase == f)]
            r = rep[(rep.metode == m) & (rep.fase == f)]
            wf = W[W.fase == f]
            n_rep = len(wf)
            obs = (wf.selesai - wf.mulai).values
            if m not in ("E", "TE"):
                muat = ep[ep.fase == f].muat.mean() * 100
                cak = np.median(np.minimum(B_PANJANG / obs, 1.0))
                detik_bersih = e[e.muat].groupby("kanal").bersih.sum().median() * B_PANJANG
            else:
                g = ep[ep.fase == f].groupby(["gerakan", "rep"])
                muat = 100 * g.ngroups / max(n_rep, 1)
                span = (g.selesai.max() - g.mulai.min()).reindex(pd.MultiIndex.from_frame(wf[["gerakan", "rep"]]))
                cak = np.median(np.nan_to_num(span.values / obs))
                det = []
                for c, gg in e[e.bersih].groupby("kanal"):
                    tot, end = 0.0, -np.inf
                    for a in np.sort(gg.mulai.values):
                        tot += (a + E_PANJANG) - max(a, end)
                        end = a + E_PANJANG
                    det.append(tot)
                detik_bersih = np.median(det + [0.0] * (len(kan) - len(det)))
            n_valid = r.groupby("kanal").size().reindex(kan, fill_value=0)
            se = []
            for (c,), g2 in r.groupby(["kanal"]):
                for b in PITA:
                    v = g2[f"{b}_db"].dropna()
                    if len(v) >= 3:
                        se.append(v.std(ddof=1) / np.sqrt(len(v)))
            rows.append(dict(participant_id=pid, metode=m, fase=f, n_repetisi=n_rep,
                             pct_repetisi_terpakai=round(muat, 1),
                             cakupan_fase_median=round(float(cak), 2),
                             pct_kanal_epoch_bersih=round(100 * e[e.muat].bersih.mean(), 1) if len(e) else np.nan,
                             otot_db_median=round(float(e[e.muat].otot_db.median()), 2) if len(e) else np.nan,
                             detik_bersih_median_kanal=round(detik_bersih, 1),
                             n_rep_valid_median_kanal=float(n_valid.median()),
                             pct_kanal_rep_valid_ge3=round(100 * (n_valid >= 3).mean(), 1),
                             se_db_median=round(float(np.median(se)), 2) if se else np.nan,
                             reliabilitas_belah_dua=_belah_dua(r)))
    return pd.DataFrame(rows)


def _belah_dua(r):
    """Korelasi pola kanal × pita antara repetisi ganjil vs genap (urut waktu), dikoreksi Spearman-Brown."""
    if r.empty:
        return np.nan
    key = r[["gerakan", "rep"]].drop_duplicates().reset_index(drop=True)
    key["setengah"] = np.arange(len(key)) % 2
    d = r.merge(key, on=["gerakan", "rep"])
    h = d.groupby(["setengah", "kanal"])[[f"{b}_db" for b in PITA]].mean()
    if h.index.get_level_values(0).nunique() < 2:
        return np.nan
    a, b = h.loc[0].stack(), h.loc[1].stack()
    j = pd.concat([a, b], axis=1).dropna()
    if len(j) < 10:
        return np.nan
    rr = np.corrcoef(j.iloc[:, 0], j.iloc[:, 1])[0, 1]
    return round(float(2 * rr / (1 + rr)), 2) if rr > -1 else np.nan
