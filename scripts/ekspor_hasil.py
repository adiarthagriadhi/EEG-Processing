"""Salin hasil TURUNAN (tanpa data mentah/sinyal) ke hasil_analisis/ agar dapat di-commit dan dibaca sesi
berikutnya. Jalankan dari root repo: python scripts/ekspor_hasil.py
Tidak disalin: EDF, video, *.fif, *.npz (data mentah & turunan sinyal/pose)."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hasil_analisis"
V2 = ("_segments.csv", "_area_map.csv", "_durasi.csv", "_romberg_area.csv")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "v2").mkdir(parents=True)
    (OUT / "metode_lama").mkdir()
    (OUT / "per_partisipan").mkdir()
    for f in sorted((ROOT / "results").glob("*.csv")):
        v2 = f.name.endswith(V2) or "_v2" in f.name
        shutil.copy(f, OUT / ("v2" if v2 else "metode_lama") / f.name)
    shutil.copy(ROOT / "data/participants.csv", OUT)
    der = ROOT / "data/derivatives"
    for d in sorted(p for p in der.iterdir() if p.is_dir()):
        o = OUT / "per_partisipan" / d.name
        o.mkdir()
        for n in ("timeline.csv", "ocr_samples.csv", "reps.csv", "sync.json", "segmen_qc.json"):
            if (d / n).exists():
                shutil.copy(d / n, o / n)
        dec = ROOT / "data/decisions" / f"{d.name}.yaml"
        if dec.exists():
            shutil.copy(dec, o / "keputusan.yaml")
    sens = ROOT / "results_sensitivitas/ringkasan.csv"
    if sens.exists():
        (OUT / "sensitivitas").mkdir()
        shutil.copy(sens, OUT / "sensitivitas/ringkasan_H1-H13.csv")
    # tahapan perbaikan 2026-09-24/25 (hasil disimpan terpisah, keputusan pengguna)
    for snap, dst in (("results_sebelum_perbaikan", "v2_sebelum_perbaikan"),
                      ("results_perbaikan_pose_datar", "v2_perbaikan_pose_datar")):
        src = ROOT / snap
        if src.exists():
            (OUT / dst).mkdir()
            for f in sorted(src.glob("*.csv")):
                if f.name.endswith(V2) or "_v2" in f.name or f.name.startswith(("pola_", "sensitivitas")):
                    shutil.copy(f, OUT / dst / f.name)
    shutil.copy(ROOT / "scripts/README_hasil.md", OUT / "README.md")
    n = sum(1 for _ in OUT.rglob("*") if _.is_file())
    print(f"{n} file → {OUT}")


if __name__ == "__main__":
    main()
