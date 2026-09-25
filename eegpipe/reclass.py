"""Reklasifikasi repetisi (2026-09-24, keputusan pengguna). Hasil sebelum reklasifikasi disimpan terpisah.

1. SALAH SISI (agem kanan ↔ kiri) — OTOMATIS HANYA MENANDAI KANDIDAT, PENERAPAN LEWAT KEPUTUSAN MANUAL.
   Penanda: beda tinggi tangan di sisi KIRI GAMBAR − tangan di sisi KANAN GAMBAR (piksel, besar = bawah) selama
   TAHAN; label kiri/kanan anatomis MediaPipe tidak dipakai karena tertukar saat tubuh berputar. Pada kohort,
   AGEM KIRI → tangan kanan-gambar lebih tinggi (31/38 partisipan). Ambang per partisipan (Otsu 1-D atas
   repetisi agem; bias sudut kamera berbeda per partisipan). Repetisi di kelompok sisi lawan dengan jarak ke
   ambang ≥ margin → `kandidat_salah_sisi`. Uji visual (P04, P07, P24, P31, P32, P36): 3 dari 4 kandidat
   satu-repetisi KELIRU (titik pergelangan meleset saat tangan dekat wajah/terhalang) → kandidat hanya
   diterapkan bila dikonfirmasi visual oleh peneliti (lembar tinjauan → scripts/terapkan_tinjauan.py) di
   `data/decisions/PXX.yaml`:  reclass_manual: [{task, rep, jadi: NGEED | AGEM KANAN | AGEM KIRI, basis}]
   Repetisi yang dipindah: `reclass = salah_sisi` (kanan↔kiri) atau `gerak_lain` (mis. NGEED saat instruksi
   AGEM), rep + 10 (kunci unik), label asli di `task_hud`/`rep_hud`; kategori tinjauan di kolom `tinjauan`.
2. TANPA TURUN: repetisi `incomplete` dengan kedalaman < min_depth_px, atau dinilai peneliti tidak_turun/berdiri
   → `reclass = tanpa_turun` (deskriptif;
   tidak ada sub-fase gerak, tidak dipakai sebagai acuan diam)."""
import numpy as np

AGEM = ("AGEM KANAN", "AGEM KIRI")
TASKS = ("NGEED",) + AGEM


def side_feature(reps, pose):
    """Median (y tangan kiri-gambar − y tangan kanan-gambar) selama TAHAN; > 0 = tangan kanan-gambar lebih tinggi."""
    t, W = pose["t"], pose.get("wrists")
    out = np.full(len(reps), np.nan)
    if W is None:
        return out
    lx, ly, rx, ry = np.asarray(W, float).T
    sw = lx > rx
    f = np.where(sw, ry, ly) - np.where(sw, ly, ry)
    for i, (_, m) in enumerate(reps.iterrows()):
        a, b = m.act_tahan, m.act_naik
        if np.isfinite([a, b]).all():
            k = (t >= a) & (t <= b)
            if k.sum() >= 5:
                out[i] = np.nanmedian(f[k])
    return out


def _otsu(v):
    v = np.sort(v)
    best, thr = -1, None
    for i in range(1, len(v)):
        a, b = v[:i], v[i:]
        s = len(a) * len(b) * (a.mean() - b.mean()) ** 2
        if s > best:
            best, thr = s, (a[-1] + b[0]) / 2
    return thr, v[v < thr].mean(), v[v >= thr].mean()


def reclassify(reps, pose, cfg, decisions=None):
    rc = cfg["reclass"]
    df = reps.copy()
    df["task_hud"], df["rep_hud"], df["reclass"] = df.task, df.rep, ""
    df["side_feature"] = side_feature(df, pose)
    df["kandidat_salah_sisi"] = False
    info = dict(side="tidak_dinilai")
    ag = df.task.isin(AGEM) & np.isfinite(df.side_feature)
    if ag.sum() >= rc["min_agem_reps"]:
        thr, c_lo, c_hi = _otsu(df.side_feature[ag].to_numpy())
        sep = c_hi - c_lo
        info.update(side_threshold=round(float(thr), 1), side_sep_px=round(float(sep), 1))
        if sep >= rc["min_sep_px"]:
            margin = max(rc["margin_px"], rc["margin_frac"] * sep)
            pred = np.where(df.side_feature >= thr, "AGEM KIRI", "AGEM KANAN")
            cand = ag & (pred != df.task) & (np.abs(df.side_feature - thr) >= margin)
            df.loc[cand, "kandidat_salah_sisi"] = True
            info["side"] = "ok"
        else:
            info["side"] = "tidak_terpisah"
    dec = decisions or {}
    other = {"AGEM KANAN": "AGEM KIRI", "AGEM KIRI": "AGEM KANAN"}
    manual = list(dec.get("reclass_manual", []) or []) + [
        {**d, "jadi": d.get("jadi", other.get(d["task"]))} for d in dec.get("reclass_sisi", []) or []]
    for d in manual:                                  # hanya dari tinjauan visual (keputusan peneliti)
        k = df.index[(df.task_hud == d["task"]) & (df.rep_hud == int(d["rep"]))]
        if len(k) and d.get("jadi") in TASKS and d["jadi"] != d["task"]:
            i = k[0]
            df.at[i, "task"], df.at[i, "rep"] = d["jadi"], int(d["rep"]) + 10
            df.at[i, "reclass"] = "salah_sisi" if d["jadi"] in AGEM and d["task"] in AGEM else "gerak_lain"
    df["tinjauan"] = ""
    for d in dec.get("tinjauan", []) or []:
        k = df.index[(df.task_hud == d["task"]) & (df.rep_hud == int(d["rep"]))]
        if len(k):
            df.at[k[0], "tinjauan"] = d.get("kategori", "")
    nod = ((df.compliance == "incomplete") & (df.depth_px < cfg["phases"]["min_depth_px"])) | \
        df.tinjauan.isin(["tidak_turun", "berdiri"])
    df.loc[nod & (df.reclass == ""), "reclass"] = "tanpa_turun"
    info.update(n_kandidat=int(df.kandidat_salah_sisi.sum()),
                n_salah_sisi=int((df.reclass == "salah_sisi").sum()),
                n_gerak_lain=int((df.reclass == "gerak_lain").sum()),
                n_tanpa_turun=int((df.reclass == "tanpa_turun").sum()))
    return df, info
