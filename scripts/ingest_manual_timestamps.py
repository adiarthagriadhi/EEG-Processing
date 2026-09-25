"""Tulis timeline/reps dari CSV timestamp manual.

    python scripts/ingest_manual_timestamps.py P08
    python scripts/ingest_manual_timestamps.py --all
    python -m eegpipe run P08 --force preprocess
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eegpipe.config import Participant, load_config
from eegpipe.manual_ts import exists, ingest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--config")
    args = ap.parse_args()
    cfg = load_config(args.config)
    man = cfg["_root"] / cfg.get("paths", {}).get("manual_timestamps", "data/manual_timestamps")
    if args.pid:
        pids = [args.pid]
    else:
        pids = sorted(p.name.split("_fase_")[0] for p in man.glob("*_fase_gerakan.csv"))
    for pid in pids:
        P = Participant(pid, cfg)
        if not exists(P):
            print(f"[{pid}] tidak ada CSV manual — dilewati")
            continue
        tl, reps, _ = ingest(P, cfg)
        print(f"[{pid}] manual: {len(reps)} repetisi, {len(tl)} baris timeline → {P.deriv_dir}")


if __name__ == "__main__":
    main()
