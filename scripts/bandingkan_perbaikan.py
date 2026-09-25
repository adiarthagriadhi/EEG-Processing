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


STAGES = [("sebelum", OLD, OLD / "derivatives"),
          ("pose_datar", ROOT / "results_perbaikan_pose_datar", ROOT / "results_perbaikan_pose_datar/derivatives"),
          ("reklasifikasi", NEW, ROOT / "data/derivatives")]


def main():
    st = [(n, r, d) for n, r, d in STAGES if r.exists()]
    t = pd.concat([per_participant(r, d).add_suffix(f"_{n}") for n, r, d in st], axis=1)
    t.to_csv(NEW / "perbandingan_perbaikan_v2.csv")
    cols = ["effect", "p_one_sided", "p_fdr"]
    h = pd.read_csv(OLD / "hypothesis_v2_tests.csv").set_index("hipotesis")[["endpoint"]]
    for n, r, _ in st:
        h = h.join(pd.read_csv(r / "hypothesis_v2_tests.csv").set_index("hipotesis")[cols].add_suffix(f"_{n}"))
    h.to_csv(NEW / "perbandingan_perbaikan_H_v2.csv")
    print(t.round(2).to_string())
    print(h.round(3).to_string())


if __name__ == "__main__":
    main()
