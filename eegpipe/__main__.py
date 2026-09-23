"""Pemakaian:
    python -m eegpipe run P02                 # semua tahap (lanjut dari cache)
    python -m eegpipe run P02 --force sync    # ulang tahap tertentu
    python -m eegpipe run-all                 # semua folder di data/raw/
"""
import argparse

from .config import load_config
from .pipeline import STAGES, run


def group(cfg, simulated):
    import pandas as pd

    from . import group_report, simulate
    from .endpoints import collect
    res = cfg["_root"] / cfg["paths"]["results"]
    rep = cfg["_root"] / cfg["paths"]["reports"]
    rep.mkdir(parents=True, exist_ok=True)
    pfile = cfg["_root"] / cfg["paths"]["participants"]
    parts = pd.read_csv(pfile) if pfile.exists() else None
    real = collect(res, parts)
    if simulated:
        data = simulate.cohort()
        data.to_csv(res / "SIMULATED_group_endpoints.csv", index=False)
        out = group_report.write(data, rep / "SIMULATED_group_report.html",
                                 real=real if len(real) else None)
    else:
        real.to_csv(res / "group_endpoints.csv", index=False)
        out = group_report.write(real, rep / "group_report.html")
    print(f"laporan grup: {out}")


def main():
    ap = argparse.ArgumentParser(prog="eegpipe")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("pid")
    r.add_argument("--force", nargs="*", default=[], choices=STAGES + ["all"])
    r.add_argument("--config")
    a = sub.add_parser("run-all")
    a.add_argument("--config")
    h = sub.add_parser("hypotheses", help="endpoint & uji H1–H5 dari results/")
    h.add_argument("--config")
    g = sub.add_parser("group", help="statistik grup + laporan (Paper A/B/D)")
    g.add_argument("--simulated", action="store_true",
                   help="demo dengan kohort simulasi 38 partisipan ([SIMULATED RESULTS])")
    g.add_argument("--config")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.cmd == "run":
        run(args.pid, cfg, force=set(args.force))
    elif args.cmd == "hypotheses":
        import pandas as pd
        from .hypotheses import endpoints, test
        res = cfg["_root"] / cfg["paths"]["results"]
        der = cfg["_root"] / cfg["paths"]["derivatives"]
        pids = sorted(p.name.split("_spectral")[0] for p in res.glob("*_spectral.csv"))
        df = pd.DataFrame([endpoints(p, res, der) for p in pids])
        parts = cfg["_root"] / cfg["paths"]["participants"]
        if parts.exists():
            df = df.merge(pd.read_csv(parts), on="participant_id", how="left")
        df.to_csv(res / "hypothesis_endpoints.csv", index=False)
        t = test(df, cfg["hypotheses"])
        t.to_csv(res / "hypothesis_tests.csv", index=False)
        pd.set_option("display.width", 220)
        print(df.round(2).to_string(index=False))
        print(t.drop(columns=["label"]).round(3).to_string(index=False))
    elif args.cmd == "group":
        group(cfg, args.simulated)
    else:
        raw_dir = cfg["_root"] / cfg["paths"]["raw"]
        for d in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
            try:
                run(d.name, cfg)
            except Exception as e:          # satu partisipan gagal ≠ semua berhenti
                print(f"[{d.name}] GAGAL: {e}")


if __name__ == "__main__":
    main()
