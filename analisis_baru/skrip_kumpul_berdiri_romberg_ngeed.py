import numpy as np, pandas as pd
nr = pd.read_csv("hasil/tahap6_aturan/dataset/nilai_repetisi.csv")
AREA = {"sentral": ["C3","C4"], "oksipital": ["O1","O2"], "frontal": ["F3","F4"]}
rows = []
def ambil(d, kond, pid):
    for a, ch in AREA.items():
        s = d[d.kanal.isin(ch)].groupby(["gerakan","rep"])[["theta_db","mu_db","beta_db"]].mean()
        r = dict(participant_id=pid, kondisi=kond, area=a, n_rep=len(s))
        for b in ("theta","mu","beta"):
            r[b] = s[f"{b}_db"].mean() if len(s) else np.nan
        rows.append(r)
for pid, g in nr.groupby("participant_id"):
    rep = g[g.lolos_R1 & ~g.fase.isin(["Buka Mata","Tutup Mata"])]
    ambil(rep[rep.fase=="Berdiri"], "Berdiri (semua gerakan)", pid)
    ambil(rep[(rep.fase=="Berdiri") & (rep.gerakan=="Ngeed")], "Berdiri (Ngeed)", pid)
    ambil(rep[(rep.fase=="Gerak") & (rep.gerakan=="Ngeed")], "Ngeed Gerak", pid)
    ambil(rep[(rep.fase=="Tahan") & (rep.gerakan=="Ngeed")], "Ngeed Tahan", pid)
    for f in ("Buka Mata","Tutup Mata"):
        ambil(g[(g.fase==f) & (g.n_bersih>=8)], f, pid)
d = pd.DataFrame(rows).round(2)
d.to_csv("hasil/pilot_analisis/berdiri_romberg_ngeed_tahan.csv", index=False)
for a in AREA:
    print("\n##", a); print(d[d.area==a].drop(columns="area").to_string(index=False))
print(nr[nr.fase.isin(["Buka Mata","Tutup Mata"])].groupby(["participant_id","fase"]).n_bersih.median())
