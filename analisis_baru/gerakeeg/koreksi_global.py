"""Koreksi kenaikan power menyeluruh (pasca-pilot; tanpa Baseline.EDF). Pipeline beku sampai Tahap 6 (ASR k 20 → A2,
epoch TE, bersih, R1 cakupan ≥ 75%). Yang dibandingkan hanya cara menyatakan power pita:

  M0_absolut   : 10·log10(power pita / power pita Istirahat)             (cara sekarang)
  M1_specparam : puncak periodik (log-spektrum − garis latar aperiodik, 2–30 Hz) dikurangi puncak periodik Istirahat
  M2_relatif   : (power pita / power total 2–30 Hz) relatif Istirahat
  M3_berdiri   : seperti M0, acuan = akhir Berdiri di dalam tugas (jendela TE Berdiri, semua repetisi)
  M4_otot      : M0 dikurangi b·otot (b = kemiringan regresi dB pita ~ dB otot 20–34 Hz per partisipan × pita)

Kriteria pemilihan (ditetapkan sebelum melihat hasil; tanpa perbedaan grup):
  (a) kenaikan menyeluruh — rata-rata semua kanal per fase gerak — mendekati 0;
  (b) lateralisasi Tahan (mu, kontra − ipsi) tetap negatif;
  (c) reliabilitas belah-dua pola kanal × pita tidak turun.
ERD sentral hanya dilaporkan, tidak dipakai memilih.
"""
import numpy as np
import pandas as pd
from scipy.signal import welch

from . import data, epoch, jendela, kanal, kualitas, lonjakan
from .istilah import FASE_REPETISI, KANAL

F = np.arange(1, 35)                      # bin 1 Hz
PITA = {"theta": (4, 8), "mu": (8, 13), "beta": (13, 30)}
METODE = ["M0_absolut", "M1_specparam", "M2_relatif", "M3_berdiri", "M4_otot"]


def _psd(x, sf):
    f, p = welch(x, sf, nperseg=int(sf))
    return p[:, np.isin(f, F)]


def _band(P, lo, hi):
    return P[..., (F >= lo) & (F < hi)].mean(axis=-1)


def spektrum_jendela(pid):
    """PSD 1–34 Hz per jendela × kanal (TE + Istirahat), pipeline beku. → (meta DataFrame, psd [n, 16, 34], ok [n, 16])."""
    raw = data.muat_edf(pid)
    rp, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
    W = jendela.jendela(rp, tt)
    _, xf, datar, sf = kualitas.sinyal(raw)
    T = xf.shape[1] / sf
    xa, _ = lonjakan.asr(xf, datar, sf, W, 20)
    ep = epoch.potong_TE(W, T)
    ist = W[W.fase == "Istirahat"]
    ep_i = pd.DataFrame([dict(gerakan="-", rep=0, fase="Istirahat", mulai=s, selesai=s + 1.0)
                         for w in ist.itertuples() for s in np.arange(w.mulai, w.selesai - 1.0 + 1e-9, 0.25)])
    ep = pd.concat([ep, ep_i], ignore_index=True)
    meta, P, OK = [], [], []
    for e in ep.itertuples():
        i0, i1 = int(round(e.mulai * sf)), int(round(e.selesai * sf))
        if i0 < 0 or i1 > xa.shape[1]:
            continue
        x, _, ok = epoch._potong(xa, datar, i0, i1, kanal.robust)
        meta.append(dict(participant_id=pid, gerakan=e.gerakan, rep=e.rep, fase=e.fase, mulai=e.mulai))
        P.append(_psd(x, sf))
        OK.append(ok)
    return pd.DataFrame(meta), np.array(P), np.array(OK)


def _fooof(p):
    from fooof import FOOOF
    m = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4, aperiodic_mode="fixed", verbose=False)
    sel = (F >= 2) & (F <= 30)
    m.fit(F[sel].astype(float), p[sel], [2, 30])
    flat = np.log10(p[sel]) - m._ap_fit
    ff = F[sel]
    return {b: 10 * flat[(ff >= lo) & (ff < hi)].mean() for b, (lo, hi) in PITA.items()}, 10 * m.aperiodic_params_[0]


def nilai(meta, P, OK, c_min=0.75):
    """Nilai repetisi × fase × kanal untuk tiap metode (hanya repetisi yang lolos R1 cakupan)."""
    pid = meta.participant_id.iloc[0]
    ist = (meta.fase == "Istirahat").values
    ref = np.array([P[ist & OK[:, k], k].mean(axis=0) for k in range(len(KANAL))])       # 16 × 34
    ber = (meta.fase == "Berdiri").values
    ref_b = np.array([P[ber & OK[:, k], k].mean(axis=0) if (ber & OK[:, k]).any() else np.full(len(F), np.nan)
                      for k in range(len(KANAL))])
    ref_fo = [(_fooof(ref[k]) if np.isfinite(ref[k]).all() else None) for k in range(len(KANAL))]
    tot = lambda p: _band(p, 2, 31)
    rows = []
    for (g, r, f), idx in meta[~ist].groupby(["gerakan", "rep", "fase"]).groups.items():
        idx = np.array(idx)
        st = meta.loc[idx, "mulai"].values
        rent = st.max() + 1.0 - st.min()
        for k, c in enumerate(KANAL):
            ok = OK[idx, k]
            if not ok.any():
                continue
            s = np.sort(st[ok])
            cak, end = 0.0, -np.inf
            for a in s:
                cak += (a + 1.0) - max(a, end)
                end = a + 1.0
            if cak / rent < c_min - 1e-9:
                continue
            p = P[idx[ok], k].mean(axis=0)
            row = dict(participant_id=pid, gerakan=g, rep=r, fase=f, kanal=c)
            for b, (lo, hi) in PITA.items():
                row[f"M0_absolut_{b}"] = 10 * np.log10(_band(p, lo, hi) / _band(ref[k], lo, hi))
                row[f"M2_relatif_{b}"] = 10 * np.log10((_band(p, lo, hi) / tot(p)) / (_band(ref[k], lo, hi) / tot(ref[k])))
                row[f"M3_berdiri_{b}"] = 10 * np.log10(_band(p, lo, hi) / _band(ref_b[k], lo, hi))
            row["otot_db"] = 10 * np.log10(_band(p, 20, 35) / _band(ref[k], 20, 35))
            if ref_fo[k] is not None:
                per, off = _fooof(p)
                for b in PITA:
                    row[f"M1_specparam_{b}"] = per[b] - ref_fo[k][0][b]
                row["aperiodik_offset_db"] = off - ref_fo[k][1]
            rows.append(row)
    d = pd.DataFrame(rows)
    for b in PITA:                                    # M4: regresi dB pita ~ dB otot per partisipan × pita
        y, x = d[f"M0_absolut_{b}"], d["otot_db"]
        m = y.notna() & x.notna()
        slope = np.polyfit(x[m], y[m], 1)[0] if m.sum() > 10 else 0.0
        d[f"M4_otot_{b}"] = y - slope * x
    return d


def evaluasi(d):
    """Per partisipan × metode: (a) kenaikan menyeluruh per fase; (b) LI Tahan mu; (c) reliabilitas belah-dua;
    + ERD sentral (laporan saja)."""
    rows = []
    for pid, g in d.groupby("participant_id"):
        for m in METODE:
            r = dict(participant_id=pid, metode=m)
            for f in ("Gerak", "Tahan", "Naik"):
                gf = g[g.fase == f]
                r[f"menyeluruh_{f}"] = gf.groupby("kanal")[[f"{m}_{b}" for b in PITA]].mean().values.mean()
                for b in ("mu", "beta"):
                    sr = gf[gf.kanal.isin(["C3", "C4"])].groupby(["gerakan", "rep"])[f"{m}_{b}"].mean().dropna()
                    r[f"sentral_{b}_{f}"] = sr.mean()
                    r[f"sentral_{b}_{f}_t"] = (sr.mean() / (sr.std(ddof=1) / np.sqrt(len(sr)))
                                                if len(sr) > 2 else np.nan)
            t = g[(g.fase == "Tahan") & g.gerakan.isin(["Agem Kanan", "Agem Kiri"]) & g.kanal.isin(["C3", "C4"])]
            w = t.pivot_table(index=["gerakan", "rep"], columns="kanal", values=f"{m}_mu").dropna()
            if len(w):
                kr = np.where(w.index.get_level_values(0) == "Agem Kanan", w.C3 - w.C4, w.C4 - w.C3)
                r["LI_tahan_mu"] = kr.mean()
                r["LI_tahan_mu_t"] = kr.mean() / (kr.std(ddof=1) / np.sqrt(len(kr))) if len(kr) > 2 else np.nan
            r["reliabilitas"] = _belah_dua(g, m)
            rows.append(r)
    return pd.DataFrame(rows)


def _belah_dua(g, m):
    vals = []
    for f in FASE_REPETISI:
        gf = g[g.fase == f]
        key = gf[["gerakan", "rep"]].drop_duplicates().reset_index(drop=True)
        key["h"] = np.arange(len(key)) % 2
        x = gf.merge(key, on=["gerakan", "rep"])
        h = x.groupby(["h", "kanal"])[[f"{m}_{b}" for b in PITA]].mean()
        if h.index.get_level_values(0).nunique() < 2:
            continue
        j = pd.concat([h.loc[0].stack(), h.loc[1].stack()], axis=1).dropna()
        if len(j) >= 10:
            rr = np.corrcoef(j.iloc[:, 0], j.iloc[:, 1])[0, 1]
            vals.append(2 * rr / (1 + rr))
    return float(np.median(vals)) if vals else np.nan
