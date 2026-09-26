"""Banding 4 metode terhadap harapan teori, pada set penyetelan (P08, P09, P31, P32).
A repo lama  : ERD % power total, acuan per repetisi, fase dari video/pose (hasil_analisis/metode_lama)
B repo v2    : specparam periodik, acuan gabungan paling diam, fase dari video/pose, offset 0,85 (hasil_analisis/v2)
C kita lama  : timestamp manual, ASR + A2, epoch TE, dB absolut (M0) relatif Istirahat
D kita baru  : seperti C, epoch TR; M2b untuk ukuran tingkat, M0 untuk Pra-Gerak & LI; syarat rebound khas-beta
Sentral = C3/C4. Nilai per partisipan = rata-rata antar-repetisi (A: median, karena % sangat miring)."""
import numpy as np
import pandas as pd

PID = ["P08", "P09", "P31", "P32"]
R = "../hasil_analisis"
FASE = {"PRA": "Pra-Gerak", "TURUN": "Gerak", "TAHAN": "Tahan", "NAIK": "Naik", "POST": "Pasca-Naik"}


def A(pid):
    e = pd.read_csv(f"{R}/metode_lama/{pid}_erd_ers.csv")
    e = e[e.channel.isin(["C3", "C4"])]
    s = e.groupby(["task", "rep", "phase", "band"]).erd_pct.mean().groupby(["phase", "band"]).median()
    v = {(FASE.get(p, p), b): x for (p, b), x in s.items()}
    t = e[(e.phase == "TAHAN") & (e.band == "mu") & e.task.str.startswith("AGEM")]
    w = t.pivot_table(index=["task", "rep"], columns="channel", values="erd_pct").dropna()
    li = np.where(w.index.get_level_values(0) == "AGEM KANAN", w.C3 - w.C4, w.C4 - w.C3)
    rb = pd.read_csv(f"{R}/metode_lama/{pid}_romberg_features.csv").alpha_reactivity_EC_EO.iloc[0]
    return v, np.median(li) if len(li) else np.nan, (rb - 1 if np.isfinite(rb) else np.nan), None


def B(pid):
    a = pd.read_csv(f"{R}/v2/{pid}_area_map.csv")
    a = a[(a.level == "area") & (a.pool == "SEMUA") & (a.area == "sentral")].set_index("phase")
    v = {(FASE[p], b): a.loc[p, f"{b}_periodic_db"] for p in a.index for b in ("mu", "beta")}
    s = pd.read_csv(f"{R}/v2/{pid}_segments.csv")
    t = s[(s.phase == "TAHAN") & s.task.str.startswith("AGEM") & s.channel.isin(["C3", "C4"]) & s.valid]
    w = t.pivot_table(index=["task", "rep"], columns="channel", values="mu_db").dropna()
    li = np.where(w.index.get_level_values(0) == "AGEM KANAN", w.C3 - w.C4, w.C4 - w.C3)
    r = pd.read_csv(f"{R}/v2/{pid}_romberg_area.csv")
    r = r[r.area == "oksipital"].set_index("kondisi").mu_periodic_db
    ber = r.get("EC", np.nan) - r.get("EO", np.nan)
    return v, li.mean() if len(li) else np.nan, ber, True       # periodik = khas pita


S = pd.read_csv("hasil/banding_jendela_TE_TR/sentral_per_partisipan.csv")
LI = pd.read_csv("hasil/pilot_analisis/S2_lateralisasi_agem.csv")
RB = pd.read_csv("hasil/pilot_analisis/berdiri_romberg_ngeed_tahan_M2b.csv")


def kita(pid, skema, level):
    d = S[(S.participant_id == pid) & (S.skema == skema)]
    get = lambda f, b, m: d[(d.fase == f) & (d.pita == b) & (d.metode == m)].rerata_db.mean()
    v = {(f, b): get(f, b, level) for f in d.fase.unique() for b in ("mu", "beta")}
    if skema == "TR":
        for b in ("mu", "beta"):
            v[("Pra-Gerak", b)] = get("Pra-Gerak", b, "M0_absolut")
        v[("Pasca-Naik", "beta")] = get("Pasca-Naik", "beta", "M0_absolut")
        khas = get("Pasca-Naik", "beta", "M2b_relatif4") >= 0
    else:
        khas = None
    li = LI[(LI.participant_id == pid) & (LI.fase == "Tahan") & (LI.pita == "mu")].rerata
    r = RB[(RB.participant_id == pid) & (RB.area == "oksipital") & (RB.metode == "M0_absolut")].set_index("kondisi").mu
    return v, li.iloc[0] if len(li) else np.nan, r.get("Tutup Mata", np.nan) - r.get("Buka Mata", np.nan), khas


METODE = {"A repo lama": A, "B repo v2": B, "C kita lama (TE+M0)": lambda p: kita(p, "TE", "M0_absolut"),
          "D kita baru (TR+M2b/M0)": lambda p: kita(p, "TR", "M2b_relatif4")}
CEK = ["Pra-Gerak: mu turun", "Gerak: beta turun", "Gerak: mu turun", "Tahan: beta pulih (> Gerak)",
       "Tahan: LI mu < 0", "Pasca-Naik: rebound beta khas", "Romberg: alpha oksipital naik (EC > EO)"]
rows = []
for m, fn in METODE.items():
    for pid in PID:
        v, li, ber, khas = fn(pid)
        g = lambda f, b: v.get((f, b), np.nan)
        pb = g("Pasca-Naik", "beta")
        hasil = [g("Pra-Gerak", "mu") < 0 if np.isfinite(g("Pra-Gerak", "mu")) else None,
                 g("Gerak", "beta") < 0, g("Gerak", "mu") < 0,
                 g("Tahan", "beta") > g("Gerak", "beta"),
                 li < 0 if np.isfinite(li) else None,
                 (bool(pb > 0 and khas) if khas is not None else None) if np.isfinite(pb) else None,
                 ber > 0 if np.isfinite(ber) else None]
        for c, h in zip(CEK, hasil):
            rows.append(dict(metode=m, participant_id=pid, harapan=c, searah=h))
D = pd.DataFrame(rows)
D["searah"] = D.searah.map(lambda x: np.nan if x is None else float(bool(x)))
D.to_csv("hasil/banding_metode_teori.csv", index=False)
T = D.groupby(["harapan", "metode"]).searah.apply(
    lambda s: f"{int(s.dropna().sum())}/{s.notna().sum()}" if s.notna().any() else "–").unstack().reindex(CEK)
tot = D.groupby("metode").searah.apply(lambda s: f"{int(s.dropna().sum())}/{s.notna().sum()}")
T.loc["TOTAL"] = tot
print(T.to_string())
