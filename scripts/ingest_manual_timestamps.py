"""Periksa timestamp manual (tanpa EEG): urutan label, jumlah repetisi, timeline turunan.

    python scripts/ingest_manual_timestamps.py P08
    python scripts/ingest_manual_timestamps.py --all

Pipeline memakai file ini otomatis (`python -m eegpipe run P08`); skrip ini hanya untuk cek cepat.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eegpipe import manual_ts
from eegpipe.config import Participant, load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--config")
    args = ap.parse_args()
    cfg = load_config(args.config)
    man = cfg["_root"] / cfg["paths"]["manual_timestamps"]
    pids = [args.pid] if args.pid else sorted(p.name.split("_timestamps")[0] for p in man.glob("*_timestamps.csv"))
    for pid in pids:
        P = Participant(pid, cfg)
        if not manual_ts.exists(P):
            print(f"[{pid}] tidak ada {manual_ts.manual_path(P).name} — dilewati")
            continue
        tl, reps, info = manual_ts.build(manual_ts.load(manual_ts.manual_path(P)), cfg)
        print(f"[{pid}] {info['n_ok']}/{info['n_rep']} repetisi lengkap; rep per gerakan {info['reps_per_task']}; "
              f"tutup mata {info['romberg_ec_onset']} dtk" + (f"; MASALAH: {info['problems']}" if info["problems"] else ""))


if __name__ == "__main__":
    main()
