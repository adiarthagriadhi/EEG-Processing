"""Berdiri, Romberg (Buka/Tutup Mata), Ngeed Gerak & Tahan dalam M2b (power pita / total 4–30 Hz, relatif Istirahat)
dan M0 sebagai pembanding. Gerak: repetisi lolos R1 (cakupan ≥ 75%); Romberg: ≥ 8 jendela bersih per kanal."""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from gerakeeg import koreksi_global as kg
from gerakeeg.istilah import BUKA_MATA, KANAL, TUTUP_MATA

AREA = {"sentral": ["C3", "C4"], "oksipital": ["O1", "O2"], "frontal": ["F3", "F4"], "parietal": ["P3", "P4"]}
PID = ["P08", "P09", "P31", "P32"]
MATA = [BUKA_MATA, TUTUP_MATA]


def romberg(meta, P, OK):
    ist = (meta.fase == "Istirahat").values
    ref = np.array([P[ist & OK[:, k], k].mean(axis=0) for k in range(len(KANAL))])
    rows = []
    for f in MATA:
        sel = (meta.fase == f).values
        for k, c in enumerate(KANAL):
            ok = sel & OK[:, k]
            if ok.sum() < 8:
                continue
            p = P[ok, k].mean(axis=0)
            r = dict(participant_id=meta.participant_id.iloc[0], gerakan="-", rep=0, fase=f, kanal=c)
            for b, (lo, hi) in kg.PITA.items():
                r[f"M0_absolut_{b}"] = 10 * np.log10(kg._band(p, lo, hi) / kg._band(ref[k], lo, hi))
                r[f"M2b_relatif4_{b}"] = 10 * np.log10((kg._band(p, lo, hi) / kg._band(p, 4, 31))
                                                      / (kg._band(ref[k], lo, hi) / kg._band(ref[k], 4, 31)))
            rows.append(r)
    return pd.DataFrame(rows)


semua = []
for pid in PID:
    meta, P, OK = kg.spektrum_jendela(pid, mata=True)
    gm = ~meta.fase.isin(MATA).values
    d = kg.nilai(meta[gm].reset_index(drop=True), P[gm], OK[gm])
    semua += [d, romberg(meta, P, OK)]
    print(pid, "selesai", flush=True)
d = pd.concat(semua, ignore_index=True)

KOND = {"Berdiri (semua gerakan)": lambda x: x.fase == "Berdiri",
        "Berdiri (Ngeed)": lambda x: (x.fase == "Berdiri") & (x.gerakan == "Ngeed"),
        "Ngeed Gerak": lambda x: (x.fase == "Gerak") & (x.gerakan == "Ngeed"),
        "Ngeed Tahan": lambda x: (x.fase == "Tahan") & (x.gerakan == "Ngeed"),
        BUKA_MATA: lambda x: x.fase == BUKA_MATA, TUTUP_MATA: lambda x: x.fase == TUTUP_MATA}
rows = []
for pid, g in d.groupby("participant_id"):
    for kond, fn in KOND.items():
        for a, ch in AREA.items():
            x = g[fn(g) & g.kanal.isin(ch)]
            for m in ("M2b_relatif4", "M0_absolut"):
                s = x.groupby(["gerakan", "rep"])[[f"{m}_{b}" for b in kg.PITA]].mean()
                r = dict(participant_id=pid, kondisi=kond, area=a, metode=m, n_rep=len(s))
                for b in kg.PITA:
                    r[b] = s[f"{m}_{b}"].mean() if len(s) else np.nan
                rows.append(r)
out = pd.DataFrame(rows).round(2)
out.to_csv("hasil/pilot_analisis/berdiri_romberg_ngeed_tahan_M2b.csv", index=False)
print(out[out.metode == "M2b_relatif4"].drop(columns="metode").to_string(index=False))
