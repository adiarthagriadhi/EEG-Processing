"""Lembar tinjauan manual repetisi yang tidak jelas (2026-09-24).
Butir: (1) kandidat salah sisi agem (eegpipe/reclass.py), (2) repetisi incomplete (termasuk tanpa_turun).
Tiap butir = satu halaman PDF: potongan video saat TAHAN (atau pertengahan jadwal HUD bila fase tak terdeteksi)
+ pembanding AGEM KANAN dan AGEM KIRI yang paling jelas dari partisipan yang sama.
Keluaran (TIDAK di-commit; wajah partisipan terlihat): reports/tinjauan/lembar_tinjauan.pdf dan
reports/tinjauan/lembar_tinjauan.csv (kolom isian: sisi_sebenarnya, kategori, catatan).
Pengisian: sisi_sebenarnya = KANAN | KIRI | tidak_jelas (butir sisi);
kategori = tidak_turun | turun_tidak_terdeteksi | gerak_lain | tidak_jelas (butir incomplete).
Jalankan: python scripts/lembar_tinjauan.py [P01 P02 …]"""
import glob
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eegpipe.config import load_config          # noqa: E402
from eegpipe.reclass import reclassify          # noqa: E402

OUT = ROOT / "reports/tinjauan"
CROP = (300, 60, 780, 660)                       # x0, y0, x1, y1 (area partisipan + tepi)


def mid_time(m, lat):
    if np.isfinite([m.act_tahan, m.act_naik]).all():
        return (m.act_tahan + m.act_naik) / 2
    return m.hud_tahan + 1.0 + lat


def frames_at(video, times):
    """Satu pembacaan berurutan; seek webm VFR tidak andal."""
    want = sorted(set(round(t, 2) for t in times))
    got, cap, i = {}, cv2.VideoCapture(video), 0
    while i < len(want):
        ok, f = cap.read()
        if not ok:
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        while i < len(want) and t >= want[i]:
            x0, y0, x1, y1 = CROP
            got[want[i]] = cv2.cvtColor(f[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
            i += 1
    return got


def participant_items(p, cfg):
    der = ROOT / "data/derivatives" / p
    reps = pd.read_csv(der / "reps.csv")
    pose = dict(np.load(der / "pose.npz"))
    df, info = reclassify(reps, pose, cfg)
    lat = float(df.get("fallback_latency_sec", pd.Series([1.2])).iloc[0])
    items = []
    for _, m in df[df.kandidat_salah_sisi].iterrows():
        items.append(dict(jenis="sisi", m=m))
    for _, m in df[df.compliance == "incomplete"].iterrows():
        items.append(dict(jenis="incomplete", m=m))
    if not items:
        return [], None, None
    # pembanding: repetisi agem ok dengan fitur sisi paling jauh dari ambang, searah labelnya
    refs = {}
    thr = info.get("side_threshold", np.nanmedian(df.side_feature))
    for task, sign in (("AGEM KANAN", -1), ("AGEM KIRI", 1)):
        s = df[(df.task_hud == task) & np.isfinite(df.side_feature) & ~df.kandidat_salah_sisi]
        if len(s):
            refs[task] = s.loc[(sign * (s.side_feature - thr)).idxmax()]
    return items, refs, lat


def page(p, it, refs, fr, lat, n, total):
    W, H = 1500, 760
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
        small = ImageFont.truetype("DejaVuSans.ttf", 17)
    except OSError:
        font = small = ImageFont.load_default()
    m = it["m"]
    title = f"{it['id']}   {p}   HUD: {m.task_hud} rep {int(m.rep_hud)}   ({n}/{total})"
    q = ("Sisi SEBENARNYA? isi sisi_sebenarnya = KANAN / KIRI / tidak_jelas" if it["jenis"] == "sisi" else
         f"Repetisi tidak lengkap (kedalaman {m.depth_px:.0f} px). isi kategori = tidak_turun / "
         "turun_tidak_terdeteksi / gerak_lain / tidak_jelas")
    d.text((20, 12), title, fill="black", font=font)
    d.text((20, 44), q, fill="darkred", font=small)
    panels = [("DITINJAU", mid_time(m, lat))] + [(f"contoh {k}", mid_time(r, lat)) for k, r in refs.items()]
    for j, (lab, t) in enumerate(panels):
        a = fr.get(round(t, 2))
        x = 20 + j * 490
        if a is not None:
            im = Image.fromarray(a).resize((470, 588))
            img.paste(im, (x, 110))
        d.text((x, 80), f"{lab}  (t={t:.1f} dtk)", fill="navy" if j else "darkred", font=small)
    return img


def main(pids):
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    pages, rows, k = [], [], 0
    for p in pids:
        items, refs, lat = participant_items(p, cfg)
        if not items:
            continue
        vid = glob.glob(str(ROOT / f"data/raw/{p}/*.webm"))[0]
        times = [mid_time(it["m"], lat) for it in items] + [mid_time(r, lat) for r in refs.values()]
        fr = frames_at(vid, times)
        for it in items:
            k += 1
            it["id"] = f"T{k:03d}"
            m = it["m"]
            rows.append(dict(id=it["id"], participant_id=p, jenis=it["jenis"], task_hud=m.task_hud,
                             rep=int(m.rep_hud), compliance=m.compliance, depth_px=round(m.depth_px, 1),
                             side_feature=round(m.side_feature, 1) if np.isfinite(m.side_feature) else "",
                             t_video=round(mid_time(m, lat), 1), sisi_sebenarnya="", kategori="", catatan=""))
            it["p"], it["refs"], it["fr"], it["lat"] = p, refs, fr, lat
            pages.append(it)
    total = len(pages)
    imgs = [page(it["p"], it, it["refs"], it["fr"], it["lat"], i + 1, total) for i, it in enumerate(pages)]
    pd.DataFrame(rows).to_csv(OUT / "lembar_tinjauan.csv", index=False)
    if imgs:
        imgs[0].save(OUT / "contoh_halaman_1.png")
        imgs[0].save(OUT / "lembar_tinjauan.pdf", save_all=True, append_images=imgs[1:], resolution=100)
    print(f"{total} butir → {OUT}")


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(Path(p).name for p in glob.glob(str(ROOT / "data/derivatives/P*")))
    main(ids)
