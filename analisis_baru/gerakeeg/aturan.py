"""Tahap 6: aturan pakai & dataset bersih (masih persiapan data; belum analisis gelombang/ERD).

Pipeline beku: sinyal 1–35 Hz → ASR k 20 (per belahan) → referensi A2 per jendela → jendela TE 1 dtk (geser 0,25 dtk)
→ bersih = tidak datar & ≤ 150 µV → power theta/mu/beta/otot dB relatif Istirahat (dipotong sama).

Dua aturan yang ditetapkan di sini (hanya dari cakupan, presisi & jumlah data, tanpa melihat nilai ERD atau grup):
  R1  nilai repetisi × fase × kanal (rata-rata power linear jendela bersih) dipakai bila jendela bersih menutupi
      ≥ c_min dari rentang TE fase itu (detik unik bersih / panjang rentang TE). Aturan cakupan (bukan jumlah jendela
      tetap) karena rentang TE Gerak/Naik ±1,5–1,8 dtk (3–4 jendela) sedangkan Tahan/Berdiri 3–6 dtk.
  R2  nilai partisipan × fase × kanal dipakai bila ada ≥ r_min repetisi yang lolos R1.
  Pemilihan (ditetapkan sebelum melihat hasil): c_min terbesar dari {0 (≥ 1 jendela), 25, 50, 75%} yang masih
  menyisakan ≥ 75% sel lolos R2 (median 4 fase) dengan r_min = 3.
Buka Mata & Tutup Mata ikut disiapkan (jendela 1 dtk, geser 0,25 dtk, onset + 1 … akhir segmen dalam EDF; Buka Mata
berakhir paling lambat di TT), dengan aturan bersih yang sama.
"""
import numpy as np
import pandas as pd

from . import data, epoch, jendela, kanal, kualitas, lonjakan
from .istilah import BUKA_MATA, FASE_REPETISI, TUTUP_MATA

MATA = (BUKA_MATA, TUTUP_MATA)

PITA = list(epoch.PITA)
N_KANDIDAT = [1, 2, 3, 4, 6]            # untuk kurva presisi
C_KANDIDAT = [0.0, 0.25, 0.50, 0.75]     # R1: cakupan minimum rentang TE
R_KANDIDAT = [2, 3, 4]
TM_MIN_JENDELA = 8           # Buka/Tutup Mata: ≥ 8 jendela bersih (≈ 2,75 dtk unik) agar nilai kanal dipakai


def potong_mata(W, T):
    """Jendela 1 dtk (geser 0,25) untuk Buka Mata dan Tutup Mata: onset + 1 dtk (Buka Mata: mulai_analisis) … akhir
    segmen (dalam EDF)."""
    out = []
    for w in W[W.fase.isin(MATA)].itertuples():
        a = getattr(w, "mulai_analisis", np.nan)
        a = w.onset + 1.0 if not np.isfinite(a) else a       # Buka Mata: sesudah Berdiri terakhir (jendela.py)
        b = min(w.selesai, T)
        s = np.arange(a, b - epoch.E_PANJANG + 1e-9, epoch.E_GESER)
        out.append(pd.DataFrame(dict(gerakan="-", rep=0, fase=w.fase, mulai=s, selesai=s + epoch.E_PANJANG)))
    return (pd.concat(out, ignore_index=True) if out
            else pd.DataFrame(columns=["gerakan", "rep", "fase", "mulai", "selesai"]))


potong_tutup_mata = potong_mata          # nama lama


def proses(pid, skema_epoch="TE"):
    """Pipeline beku → per jendela × kanal (TE atau TR + Buka/Tutup Mata): bersih, dB per pita."""
    raw = data.muat_edf(pid)
    rp, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
    W = jendela.jendela(rp, tt)
    _, xf, datar, sf = kualitas.sinyal(raw)
    T = xf.shape[1] / sf
    xa, info = lonjakan.asr(xf, datar, sf, W, 20)
    ref, _ = epoch.acuan(xa, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER, kanal.robust)
    ep = pd.concat([epoch.POTONG[skema_epoch](W, T), potong_mata(W, T)], ignore_index=True)
    est = epoch.estimasi(xa, datar, sf, ep, ref, "beku", kanal.robust)
    return est.assign(participant_id=pid), rp.assign(participant_id=pid), info


def _lin(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return 10 * np.log10(np.mean(10 ** (v / 10))) if len(v) else np.nan


def nilai_repetisi(est):
    """Satu baris per partisipan × gerakan × rep × fase × kanal: n jendela (semua/bersih), detik unik bersih, dB."""
    g = est.groupby(["participant_id", "gerakan", "rep", "fase", "kanal"])
    out = g.agg(n_jendela=("bersih", "size"), n_bersih=("bersih", "sum"))
    b = est[est.bersih].groupby(["participant_id", "gerakan", "rep", "fase", "kanal"])
    for p in PITA + ["otot"]:
        out[f"{p}_db"] = b[f"{p}_db"].apply(_lin)
    out["detik_bersih"] = b.mulai.apply(lambda s: _unik(np.sort(s.values)))
    out["rentang_detik"] = g.mulai.max() + 1.0 - g.mulai.min()
    out = out.reset_index()
    out["detik_bersih"] = out.detik_bersih.fillna(0.0)
    out["cakupan"] = (out.detik_bersih / out.rentang_detik).clip(upper=1.0)
    return out


def _unik(s, L=1.0):
    tot, end = 0.0, -np.inf
    for a in s:
        tot += (a + L) - max(a, end)
        end = a + L
    return tot


def sd_antar_repetisi(nr, min_n=2):
    """Median SD antar-repetisi (dB) per fase, dari nilai repetisi dengan ≥ min_n jendela bersih."""
    d = nr[nr.fase.isin(FASE_REPETISI) & (nr.n_bersih >= min_n)]
    s = d.groupby(["participant_id", "fase", "kanal"])[[f"{p}_db" for p in PITA]].std(ddof=1)
    s.columns = PITA
    return s.groupby("fase").median().assign(semua=lambda x: x[PITA].mean(axis=1)).reset_index()


def presisi_vs_n(est, n_list=N_KANDIDAT, min_sel=8, ulang=40, seed=0):
    """Galat (RMS, dB) nilai repetisi dari n jendela bersih acak terhadap nilai dari semua jendela bersih, pada sel
    dengan ≥ min_sel jendela bersih. Jendela berurutan (tumpang tindih 0,75 dtk) diambil sebagai blok berurutan
    acak, sesuai kenyataan: repetisi dengan sedikit jendela bersih biasanya punya satu potongan bersih pendek."""
    rng = np.random.default_rng(seed)
    d = est[est.bersih & est.fase.isin(FASE_REPETISI)]
    rows = []
    for key, g in d.groupby(["participant_id", "gerakan", "rep", "fase", "kanal"]):
        if len(g) < min_sel:
            continue
        g = g.sort_values("mulai")
        full = {p: _lin(g[f"{p}_db"]) for p in PITA}
        for n in n_list:
            for _ in range(ulang):
                a = rng.integers(0, len(g) - n + 1)
                sub = g.iloc[a:a + n]
                rows.append(dict(fase=key[3], n=n, **{p: _lin(sub[f"{p}_db"]) - full[p] for p in PITA}))
    r = pd.DataFrame(rows)
    return (r.groupby(["fase", "n"])[PITA].apply(lambda x: np.sqrt((x ** 2).mean())).reset_index()
            .assign(semua=lambda x: np.sqrt((x[PITA] ** 2).mean(axis=1))))


def _lolos_R1(nr, c):
    return (nr.n_bersih >= 1) & (nr.cakupan >= c - 1e-9)


def hasil_vs_aturan(nr, c_list=C_KANDIDAT, r_list=R_KANDIDAT):
    """Untuk tiap (c_min, r_min): % repetisi lolos R1 dan % sel partisipan × fase × kanal lolos R2, per fase."""
    rep = nr[nr.fase.isin(FASE_REPETISI)]
    semua = rep.groupby(["participant_id", "fase", "kanal"]).size()
    rows = []
    for c in c_list:
        ok = rep[_lolos_R1(rep, c)]
        cnt = ok.groupby(["participant_id", "fase", "kanal"]).size().reindex(semua.index, fill_value=0)
        for r in r_list:
            for f in FASE_REPETISI:
                m = cnt.index.get_level_values("fase") == f
                rows.append(dict(c_min=c, r_min=r, fase=f,
                                 pct_repetisi_lolos_R1=round(100 * _lolos_R1(rep[rep.fase == f], c).mean(), 1),
                                 pct_sel_lolos_R2=round(100 * (cnt[m] >= r).mean(), 1),
                                 median_rep_per_sel=float(cnt[m].median())))
    return pd.DataFrame(rows)


def pilih_c(hasil, r_min=3, ambang=75.0):
    m = hasil[hasil.r_min == r_min].groupby("c_min").pct_sel_lolos_R2.median()
    ok = m[m >= ambang]
    return float(ok.index.max()) if len(ok) else float(m.index.min())


def dataset(nr, c_min, r_min):
    """→ (nilai repetisi berlabel lolos_R1, nilai partisipan × fase × kanal berlabel lolos_R2).
    Nilai partisipan = rata-rata dB antar-repetisi yang lolos R1 (per gerakan & gabungan 'Semua'); SE antar-repetisi."""
    nr = nr.copy()
    nr["lolos_R1"] = np.where(nr.fase.isin(MATA), nr.n_bersih >= TM_MIN_JENDELA, _lolos_R1(nr, c_min))
    ok = nr[nr.lolos_R1]
    parts = []
    for label, d in [("Semua", ok)] + [(g, ok[ok.gerakan == g]) for g in sorted(ok.gerakan.unique()) if g != "-"]:
        if label != "Semua":
            d = d.assign(gerakan=label)
        grp = d.groupby(["participant_id", "fase", "kanal"])
        s = grp.size().rename("n_rep").to_frame()
        for p in PITA + ["otot"]:
            s[f"{p}_db"] = grp[f"{p}_db"].mean()
            s[f"{p}_se"] = grp[f"{p}_db"].std(ddof=1) / np.sqrt(s.n_rep)
        parts.append(s.reset_index().assign(gerakan=label))
    P = pd.concat(parts, ignore_index=True)
    P["lolos_R2"] = np.where(P.fase.isin(MATA), P.n_rep >= 1, P.n_rep >= r_min)
    return nr, P
