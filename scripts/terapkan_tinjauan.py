"""Terapkan hasil tinjauan manual peneliti (CSV lembar_tinjauan, diisi 2026-09-25) ke data/decisions/PXX.yaml:
  tinjauan:        [{task, rep, kategori, catatan}]  — kategori: tidak_turun | turun_tidak_terdeteksi | berdiri |
                                                        gerak_lain | tidak_jelas | sesuai (sisi benar)
  reclass_manual:  [{task, rep, jadi, basis}]         — gerak sebenarnya (NGEED / AGEM KANAN / AGEM KIRI)
Aturan baca: kolom sisi_sebenarnya dan kategori digabung (sebagian isian tertukar kolom); catatan yang menyebut
gerak (agem kanan/agem kiri/ngeed) → gerak sebenarnya; catatan 'berdiri' → kategori berdiri.
Jalankan: python scripts/terapkan_tinjauan.py data/decisions/tinjauan_manual_2026-09-25.csv"""
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
KATEGORI = ("tidak_turun", "turun_tidak_terdeteksi", "gerak_lain", "tidak_jelas")


def gerak(txt):
    t = txt.lower()
    for k, v in (("agem kanan", "AGEM KANAN"), ("agem kiri", "AGEM KIRI"), ("ngeed", "NGEED")):
        if k in t:
            return v
    return None


def main(path):
    d = pd.read_csv(path, sep=None, engine="python", dtype=str).fillna("")
    out = {}
    for _, r in d.iterrows():
        sisi, kat, cat = r.sisi_sebenarnya.strip().upper(), r.kategori.strip().lower(), r.catatan.strip()
        if kat and kat not in KATEGORI:          # catatan ditulis di kolom kategori
            cat, kat = (kat + " " + cat).strip(), ""
        task, rep = r.task_hud.strip(), int(r.rep)
        jadi, k = None, kat
        if sisi in ("KANAN", "KIRI"):
            jadi = f"AGEM {sisi}"
        elif sisi == "NGEED":
            jadi = "NGEED"
        elif sisi in ("GERAK_LAIN", "TIDAK_TURUN", "TURUN_TIDAK_TERDETEKSI", "TIDAK_JELAS") and not k:
            k = sisi.lower()
        if k == "gerak_lain" or sisi == "GERAK_LAIN":
            g = gerak(cat)
            if g and not jadi:
                jadi = g
            if "berdiri" in cat.lower():
                k = "berdiri"
        if not k:
            k = "sesuai" if jadi == task else ("gerak_lain" if jadi else "tidak_jelas")
        e = out.setdefault(r.participant_id, {"tinjauan": [], "reclass_manual": []})
        if not any(x["task"] == task and x["rep"] == rep for x in e["tinjauan"]):
            e["tinjauan"].append(dict(task=task, rep=rep, kategori=k, catatan=cat, butir=r.id))
        if jadi and jadi != task and not any(x["task"] == task and x["rep"] == rep for x in e["reclass_manual"]):
            e["reclass_manual"].append(dict(task=task, rep=rep, jadi=jadi,
                                            basis=f"tinjauan visual peneliti 2026-09-25 ({r.id}; {cat or sisi})"))
    for p, e in out.items():
        f = ROOT / "data/decisions" / f"{p}.yaml"
        dec = (yaml.safe_load(open(f)) if f.exists() else None) or {}
        dec.pop("reclass_sisi", None)
        dec["tinjauan"], dec["reclass_manual"] = e["tinjauan"], e["reclass_manual"]
        yaml.safe_dump(dec, open(f, "w"), allow_unicode=True, sort_keys=False)
        print(p, [(x["task"], x["rep"], x["kategori"]) for x in e["tinjauan"]],
              "→", [(x["task"], x["rep"], x["jadi"]) for x in e["reclass_manual"]])


if __name__ == "__main__":
    main(sys.argv[1])
