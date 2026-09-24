"""Uji sensitivitas pembersihan artefak (tanpa menimpa hasil utama):
 A = baku; B = tepi sinyal datar diperlebar 1,6 dtk (ekor filter high-pass 1 Hz);
 C = gabungan spektrum antar-segmen dengan MEDIAN; D = B + C.
Keluaran: results_sensitivitas/<varian>/ + ringkasan efek H1–H13."""
import copy, json, sys
from pathlib import Path
import mne, numpy as np, pandas as pd, yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eegpipe.config import load_config, Participant
from eegpipe.eeg_io import load_edf
from eegpipe import segments
from eegpipe.hypotheses_v2 import endpoints, test

cfg0 = load_config()
parts = pd.read_csv(cfg0["_root"] / "data/participants.csv")
pids = sorted(p.name.split("_area_map")[0] for p in (cfg0["_root"] / "results").glob("*_area_map.csv"))
VAR = {"A_baku": {}, "B_tepi_datar_1.6s": {"flat_pad_sec": 1.6},
       "C_median": {"pool": "median"}, "D_tepi+median": {"flat_pad_sec": 1.6, "pool": "median"}}
rows = []
for name, over in VAR.items():
    cfg = copy.deepcopy(cfg0); cfg["segments"].update(over)
    out = cfg0["_root"] / "results_sensitivitas" / name; out.mkdir(parents=True, exist_ok=True)
    for pid in pids:
        P = Participant(pid, cfg)
        dec = yaml.safe_load(open(P.decisions_path))["sync"]
        off = dec.get("offset_blocks", dec["offset_sec"])
        clean = mne.io.read_raw_fif(P.out("clean_raw.fif"), preload=True, verbose="error")
        raw = load_edf(P.trial_edf, cfg)
        flat = segments.flat_mask(raw, cfg)
        seg, amap, dur, qc = segments.analyze(clean, pd.read_csv(P.out("reps.csv")), pd.read_csv(P.out("timeline.csv")),
                                             dict(np.load(P.out("pose.npz"))), off, pid, cfg, flat=flat)
        amap.to_csv(out / f"{pid}_area_map.csv", index=False); dur.to_csv(out / f"{pid}_durasi.csv", index=False)
        print(name, pid, "segmen C3 valid", round(seg[seg.channel == "C3"].valid.mean(), 2), flush=True)
    df = pd.DataFrame([endpoints(p, out) for p in pids]).merge(parts, on="participant_id")
    t = test(df, cfg["hypotheses_v2"], name)
    rows.append(t[["sampel", "hipotesis", "effect", "p_one_sided"]])
r = pd.concat(rows).pivot_table(index="hipotesis", columns="sampel", values=["effect", "p_one_sided"])
r.to_csv(cfg0["_root"] / "results_sensitivitas" / "ringkasan.csv")
pd.set_option("display.width", 250)
print(r.round(2).to_string())
