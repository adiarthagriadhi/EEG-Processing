"""Cek langsung di EEG (offset 0, referensi telinga asli, tanpa ASR): apakah TT = saat mata mulai ditutup?
Tanda yang dicari: (1) kedipan (Fp1/Fp2) berhenti sesudah TT; (2) selubung alpha oksipital (O1/O2, 8–13 Hz) naik
sesudah TT. Keluaran: hasil/pilot_analisis/cek_tutup_mata.{csv,png}."""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, hilbert

sys.path.insert(0, ".")
from gerakeeg import data  # noqa: E402
from gerakeeg.grafik import GRID, INK, INK2, SURFACE  # noqa: E402

BIRU, ORANYE = "#2a6fdb", "#e07b18"
PID = ["P08", "P31", "P32"]           # P09: TT di luar EDF
PRA, PASCA = (-15, -1), (1, 25)
rows = []
fig, axes = plt.subplots(len(PID) * 2, 1, figsize=(11, 2.3 * len(PID) * 2), sharex=True,
                         gridspec_kw=dict(hspace=0.35), facecolor=SURFACE)
for j, pid in enumerate(PID):
    raw = data.muat_edf(pid)
    ts = data.muat_timestamp(pid)
    tt = ts[ts.label == "TT"].waktu_detik.iloc[0]
    sf = raw.info["sfreq"]
    fp = raw.copy().pick(["Fp1", "Fp2"]).filter(0.3, 8, verbose="error").get_data().mean(axis=0) * 1e6
    oc = raw.copy().pick(["O1", "O2"]).filter(8, 13, verbose="error").get_data() * 1e6
    env = np.abs(hilbert(oc, axis=1)).mean(axis=0)
    env = np.convolve(env, np.ones(int(2 * sf)) / (2 * sf), mode="same")
    a, b = int((tt - 20) * sf), min(int((tt + 30) * sf), len(fp))
    t = np.arange(a, b) / sf - tt
    seg = fp[a:b]
    thr = max(60.0, 5 * np.median(np.abs(seg - np.median(seg))) / 0.6745)
    pk, _ = find_peaks(np.abs(seg), height=thr, distance=int(0.3 * sf))
    tk = t[pk]
    rate = lambda lo, hi: ((tk >= lo) & (tk < hi)).sum() / (hi - lo) * 60
    m = lambda lo, hi: env[a:b][(t >= lo) & (t < hi)].mean()
    akhir = min(PASCA[1], t[-1])
    rows.append(dict(participant_id=pid, TT=tt, kedip_per_mnt_sebelum=round(rate(*PRA), 1),
                     kedip_per_mnt_sesudah=round(rate(PASCA[0], akhir), 1),
                     kedipan_terakhir_rel_TT=round(tk[tk < 5].max(), 2) if (tk < 5).any() else np.nan,
                     kedipan_sesudah_TT_plus_2=int((tk > 2).sum()),
                     alpha_sesudah_vs_sebelum_db=round(20 * np.log10(m(PASCA[0], akhir) / m(*PRA)), 2),
                     detik_EEG_sesudah_TT=round(akhir, 1)))
    ax = axes[2 * j]
    ax.plot(t, seg, color=INK2, lw=1)
    ax.plot(tk, seg[pk], "o", ms=5, color=ORANYE, mec=SURFACE, mew=1.5, label="kedipan/gerak mata")
    ax.set_ylabel("Fp1/Fp2\nµV", fontsize=8, color=INK2)
    ax.set_title(f"{pid}: TT = {tt:.2f} dtk (garis) — atas: mata (Fp1/Fp2), bawah: alpha oksipital", fontsize=9,
                 color=INK, loc="left")
    ax2 = axes[2 * j + 1]
    ax2.plot(t, env[a:b], color=BIRU, lw=2)
    ax2.set_ylabel("alpha O1/O2\nµV", fontsize=8, color=INK2)
    for x in (ax, ax2):
        x.axvline(0, color=INK, lw=1)
        x.set_facecolor(SURFACE)
        x.grid(color=GRID, lw=0.6)
        for s in ("top", "right"):
            x.spines[s].set_visible(False)
        x.tick_params(labelsize=7, colors=INK2)
    if j == 0:
        ax.legend(fontsize=7, frameon=False, loc="upper left")
axes[-1].set_xlabel("detik relatif TT (offset 0)", fontsize=8, color=INK2)
fig.savefig("hasil/pilot_analisis/cek_tutup_mata.png", dpi=130, bbox_inches="tight", facecolor=SURFACE)
D = pd.DataFrame(rows)
D.to_csv("hasil/pilot_analisis/cek_tutup_mata.csv", index=False)
print(D.to_string(index=False))
