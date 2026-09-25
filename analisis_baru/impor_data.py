"""Pindahkan file unggahan ke lokasi baku, dikenali dari kode PXX di nama file.

    .venv/bin/python analisis_baru/impor_data.py <file atau folder> [...]

- *Trial*.EDF / .edf          → data/raw/PXX/PXX_Trial.EDF
- *timestamps*.csv            → data/manual_timestamps/PXX_timestamps.csv
- *Baseline*.EDF              → data/raw/PXX/PXX_Baseline.EDF (opsional; belum dipakai metode baru)
File yang sudah ada TIDAK ditimpa kecuali --timpa. File lain dilaporkan dan dilewati.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tujuan(p):
    m = re.search(r"(?<![A-Za-z0-9])P(\d{2})(?!\d)", p.name, flags=re.I)
    if not m:
        return None, "tanpa kode PXX"
    pid = f"P{m.group(1)}"
    n = p.name.lower()
    if n.endswith(".csv") and "timestamp" in n:
        return ROOT / "data" / "manual_timestamps" / f"{pid}_timestamps.csv", pid
    if n.endswith(".edf") and "trial" in n:
        return ROOT / "data" / "raw" / pid / f"{pid}_Trial.EDF", pid
    if n.endswith(".edf") and "baseline" in n:
        return ROOT / "data" / "raw" / pid / f"{pid}_Baseline.EDF", pid
    return None, "jenis file tidak dikenal"


def main(args):
    timpa = "--timpa" in args
    files = []
    for a in (x for x in args if x != "--timpa"):
        p = Path(a)
        files += sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else [p]
    for f in files:
        dst, info = tujuan(f)
        if dst is None:
            print(f"lewati  {f.name}: {info}")
            continue
        if dst.exists() and not timpa:
            print(f"ada     {dst.relative_to(ROOT)} (tidak ditimpa)")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        print(f"salin   {f.name} → {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
