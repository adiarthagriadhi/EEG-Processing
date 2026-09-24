"""Bandingkan hasil sebelum (results_sebelum_perbaikan/) vs sesudah perbaikan pelacak pose + penyelamatan
sinyal datar (results/). Keluaran: results/perbandingan_perbaikan_v2.csv (per partisipan) dan
results/perbandingan_perbaikan_H_v2.csv (uji H1–H13). Jalankan dari root repo."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = ROOT / "results_sebelum_perbaikan", ROOT / "results"


def per_participant(res, der):
    rows = []
    for f in sorted(res.glob("P*_segments.csv")):
        p = f.name.split("_")[0]
        s = pd.read_csv(f)
        mv = s[s.phase.isin(["TURUN", "TAHAN", "NAIK"])]
        reps = pd.read_csv(der / p / "reps.csv")
        rows.append(dict(participant_id=p, fase_ok=int((reps.compliance == "ok").sum()),
                         incomplete=int((reps.compliance == "incomplete").sum()),
                         hud_fallback=int((reps.get("phase_source") == "hud_fallback").sum()),
                         n_segmen=int(s.groupby(["task", "rep", "phase"]).ngroups),
                         kanal_segmen_gerak_valid=round(float(mv.valid.mean()), 3),
                         salvaged=round(float(mv.get("salvaged", pd.Series(False)).mean()), 3)))
    return pd.DataFrame(rows).set_index("participant_id")


def main():
    a = per_participant(OLD, OLD / "derivatives")
    b = per_participant(NEW, ROOT / "data/derivatives")
    t = a.join(b, lsuffix="_sebelum", rsuffix="_sesudah")
    t.to_csv(NEW / "perbandingan_perbaikan_v2.csv")
    ha = pd.read_csv(OLD / "hypothesis_v2_tests.csv").set_index("hipotesis")
    hb = pd.read_csv(NEW / "hypothesis_v2_tests.csv").set_index("hipotesis")
    cols = ["effect", "p_one_sided", "p_fdr"]
    h = ha[["endpoint"] + cols].join(hb[cols], lsuffix="_sebelum", rsuffix="_sesudah")
    h.to_csv(NEW / "perbandingan_perbaikan_H_v2.csv")
    print(t.round(2).to_string())
    print(h.round(3).to_string())


if __name__ == "__main__":
    main()
