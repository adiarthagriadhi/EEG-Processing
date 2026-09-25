"""Analisis gelombang EEG mengikuti RENCANA_ANALISIS.md. Dijalankan sebagai PILOT pada set penyetelan (n = 4):
deskriptif per partisipan, tanpa inferensi grup.

Masukan: hasil/tahap6_aturan/dataset/ (nilai_repetisi, nilai_partisipan, repetisi_perilaku) dan participants.csv.
Sentral = rata-rata C3 & C4 (kanal yang lolos). Nilai dB relatif Istirahat; ERD < 0.
"""
import numpy as np
import pandas as pd
from scipy import stats

from .istilah import BUKA_MATA, FASE_REPETISI, TUTUP_MATA

SENTRAL = ["C3", "C4"]
PITA = ["theta", "mu", "beta"]


def _ci(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    n = len(v)
    if n < 2:
        return dict(n=n, rerata=v.mean() if n else np.nan, ci_bawah=np.nan, ci_atas=np.nan, t=np.nan, p=np.nan)
    se = v.std(ddof=1) / np.sqrt(n)
    h = stats.t.ppf(0.975, n - 1) * se
    t, p = stats.ttest_1samp(v, 0.0)
    return dict(n=n, rerata=v.mean(), ci_bawah=v.mean() - h, ci_atas=v.mean() + h, t=t, p=p)


def sentral_per_repetisi(nr):
    """Nilai sentral per repetisi × fase: rata-rata C3/C4 yang lolos R1."""
    d = nr[nr.kanal.isin(SENTRAL) & nr.lolos_R1 & nr.fase.isin(FASE_REPETISI)]
    return d.groupby(["participant_id", "gerakan", "rep", "fase"])[[f"{p}_db" for p in PITA]].mean().reset_index()


def ukuran_utama(nr, perilaku):
    """U1–U5 per partisipan + uji ERD ≠ 0 di dalam partisipan (S1) untuk semua fase × pita sentral."""
    sr = sentral_per_repetisi(nr)
    rows = []
    for (pid, f), g in sr.groupby(["participant_id", "fase"]):
        for p in ("mu", "beta"):
            rows.append(dict(participant_id=pid, fase=f, pita=p, **_ci(g[f"{p}_db"])))
    S1 = pd.DataFrame(rows)
    U = []
    for pid, g in S1.groupby("participant_id"):
        get = lambda f, p: g[(g.fase == f) & (g.pita == p)].rerata.iloc[0] if len(g[(g.fase == f) & (g.pita == p)]) else np.nan
        th = perilaku[perilaku.participant_id == pid].durasi_Tahan.dropna()
        U.append(dict(participant_id=pid, U1_beta_Gerak=get("Gerak", "beta"), U2_mu_Gerak=get("Gerak", "mu"),
                      U3_beta_Tahan=get("Tahan", "beta"), U4_mu_Tahan=get("Tahan", "mu"),
                      U5_CV_Tahan=th.std(ddof=1) / th.mean() if len(th) > 1 else np.nan))
    return pd.DataFrame(U), S1


def lateralisasi(nr):
    """S2: LI = kontralateral − ipsilateral (dB) per repetisi Agem; Agem Kanan kontra = C3, Agem Kiri kontra = C4."""
    d = nr[nr.kanal.isin(SENTRAL) & nr.lolos_R1 & nr.gerakan.isin(["Agem Kanan", "Agem Kiri"])
           & nr.fase.isin(["Gerak", "Tahan"])]
    w = d.pivot_table(index=["participant_id", "gerakan", "rep", "fase"], columns="kanal",
                      values=["mu_db", "beta_db"]).dropna()
    rows = []
    for (pid, f), g in w.groupby(level=["participant_id", "fase"]):
        for p in ("mu", "beta"):
            kontra = np.where(g.index.get_level_values("gerakan") == "Agem Kanan", g[(f"{p}_db", "C3")],
                              g[(f"{p}_db", "C4")])
            ipsi = np.where(g.index.get_level_values("gerakan") == "Agem Kanan", g[(f"{p}_db", "C4")],
                            g[(f"{p}_db", "C3")])
            rows.append(dict(participant_id=pid, fase=f, pita=p, **_ci(kontra - ipsi)))
    return pd.DataFrame(rows)


def perilaku_ringkas(perilaku):
    rows = []
    for pid, g in perilaku.groupby("participant_id"):
        r = dict(participant_id=pid, n_repetisi=len(g))
        for f in ("Gerak", "Tahan", "Naik", "Berdiri"):
            v = g[f"durasi_{f}"].dropna()
            r[f"durasi_{f}_median"] = v.median()
            r[f"durasi_{f}_cv"] = v.std(ddof=1) / v.mean() if len(v) > 1 else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def romberg(est):
    """Per partisipan: alpha (mu 8–13 Hz) dB per kanal/area, Tutup − Buka Mata, dari jendela 1 dtk bersih.
    Ketidakpastian: bootstrap blok 4 jendela (1 dtk tanpa tumpang tindih) per segmen, 2000 ulangan."""
    rng = np.random.default_rng(0)
    area = {"oksipital": ["O1", "O2"], "sentral": ["C3", "C4"], "frontal": ["F3", "F4"], "parietal": ["P3", "P4"]}
    rows = []
    for pid, g in est[est.fase.isin([BUKA_MATA, TUTUP_MATA]) & est.bersih].groupby("participant_id"):
        for nama, chs in area.items():
            for pita in ("mu", "theta"):
                seg = {}
                for f in (BUKA_MATA, TUTUP_MATA):
                    s = g[(g.fase == f) & g.kanal.isin(chs)].groupby("mulai")[f"{pita}_db"].mean().sort_index()
                    seg[f] = s.values
                if min(len(seg[BUKA_MATA]), len(seg[TUTUP_MATA])) < 8:
                    rows.append(dict(participant_id=pid, area=nama, pita=pita, n_buka=len(seg[BUKA_MATA]),
                                     n_tutup=len(seg[TUTUP_MATA])))
                    continue
                lin = lambda v: 10 * np.log10(np.mean(10 ** (v / 10)))
                d = lin(seg[TUTUP_MATA]) - lin(seg[BUKA_MATA])
                boot = []
                for _ in range(2000):
                    bb = []
                    for f in (BUKA_MATA, TUTUP_MATA):
                        v = seg[f]
                        blk = [v[i:i + 4] for i in range(0, len(v) - 3, 4)] or [v]
                        pick = rng.integers(0, len(blk), len(blk))
                        bb.append(lin(np.concatenate([blk[i] for i in pick])))
                    boot.append(bb[1] - bb[0])
                rows.append(dict(participant_id=pid, area=nama, pita=pita, n_buka=len(seg[BUKA_MATA]),
                                 n_tutup=len(seg[TUTUP_MATA]), buka_db=lin(seg[BUKA_MATA]),
                                 tutup_db=lin(seg[TUTUP_MATA]), tutup_minus_buka_db=d,
                                 ci_bawah=np.percentile(boot, 2.5), ci_atas=np.percentile(boot, 97.5)))
    return pd.DataFrame(rows)
