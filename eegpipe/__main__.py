"""Pemakaian:
    python -m eegpipe run P02                 # semua tahap (lanjut dari cache)
    python -m eegpipe run P02 --force sync    # ulang tahap tertentu
    python -m eegpipe run-all                 # semua folder di data/raw/
"""
import argparse

from .config import load_config
from .pipeline import STAGES, run


def main():
    ap = argparse.ArgumentParser(prog="eegpipe")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("pid")
    r.add_argument("--force", nargs="*", default=[], choices=STAGES + ["all"])
    r.add_argument("--config")
    a = sub.add_parser("run-all")
    a.add_argument("--config")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.cmd == "run":
        run(args.pid, cfg, force=set(args.force))
    else:
        raw_dir = cfg["_root"] / cfg["paths"]["raw"]
        for d in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
            try:
                run(d.name, cfg)
            except Exception as e:          # satu partisipan gagal ≠ semua berhenti
                print(f"[{d.name}] GAGAL: {e}")


if __name__ == "__main__":
    main()
