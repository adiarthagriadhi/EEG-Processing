"""Banding jendela observasi TE (beku) vs TR (berdasar rujukan, 2026-09-26) pada set penyetelan.
Ukuran: mu/beta sentral (C3/C4), M2b (relatif 4–30 Hz) dan M0 (absolut), relatif Istirahat.
TR menambah Pra-Gerak [onset − 2, onset] dan Pasca-Naik [B + 0,5, B + 2,5]; Berdiri dipersempit [B + 2,5, akhir − 2]."""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from gerakeeg import koreksi_global as kg

PID = ["P08", "P09", "P31", "P32"]
OUT = "hasil/banding_jendela_TE_TR"


def sentral(d, pid, skema):
    rows = []
    c = d[d.kanal.isin(["C3", "C4"])]
    for f, g in c.groupby("fase"):
        for m in ("M2b_relatif4", "M0_absolut"):
            for b in ("mu", "beta"):
                v = g.groupby(["gerakan", "rep"])[f"{m}_{b}"].mean().dropna()
                t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 else np.nan
                rows.append(dict(participant_id=pid, skema=skema, fase=f, metode=m, pita=b, n_rep=len(v),
                                 rerata_db=v.mean(), t=t))
    return rows


rows, jml = [], []
for pid in PID:
    for skema in ("TE", "TR"):
        meta, P, OK = kg.spektrum_jendela(pid, skema_epoch=skema)
        d = kg.nilai(meta, P, OK)
        rows += sentral(d, pid, skema)
        n = meta[meta.fase != "Istirahat"].groupby("fase").size().rename("n_jendela")
        jml.append(n.to_frame().assign(participant_id=pid, skema=skema,
                                        rep_lolos_R1=d[d.kanal.isin(["C3", "C4"])].groupby("fase")
                                        .apply(lambda x: x[["gerakan", "rep"]].drop_duplicates().shape[0])))
        print(pid, skema, flush=True)
R = pd.DataFrame(rows).round(3)
J = pd.concat(jml).reset_index()
import os
os.makedirs(OUT, exist_ok=True)
R.to_csv(f"{OUT}/sentral_per_partisipan.csv", index=False)
J.to_csv(f"{OUT}/jumlah_jendela.csv", index=False)
urut = ["Pra-Gerak", "Gerak", "Tahan", "Naik", "Pasca-Naik", "Berdiri"]
for m in ("M2b_relatif4", "M0_absolut"):
    x = R[R.metode == m].pivot_table(index=["fase", "pita"], columns=["skema", "participant_id"], values="rerata_db")
    print("\n##", m); print(x.reindex(urut, level=0).round(2).to_string())
    tt = R[R.metode == m].pivot_table(index=["fase", "pita"], columns=["skema", "participant_id"], values="t")
    print("t:"); print(tt.reindex(urut, level=0).round(1).to_string())
print(J.pivot_table(index="fase", columns=["skema", "participant_id"], values=["n_jendela", "rep_lolos_R1"]).to_string())
