"""Visualisasi perubahan gelombang di setiap tahap analisis (metode final: TR + M2b, M0 untuk LI).
Satu repetisi Agem Kanan (rep 1) per partisipan, ditambah spektrum semua repetisi.

Gambar per partisipan (hasil/visual_tahap/):
  1_gelombang_tahap0-3.png : 0 mentah → 1 filter 1–35 Hz + sinyal datar → 2 ASR k 20 → 3 referensi A2
  2_jendela_dan_pita.png   : 4 jendela TR & jendela bersih (C3/C4) → 5 gelombang mu & beta + selubungnya vs Istirahat
  3_spektrum_dan_nilai.png : 6 spektrum per fase relatif Istirahat: M0 vs M2b → 7 nilai akhir M2b per fase
Pemakaian: .venv/bin/python analisis_baru/skrip_visual_tahap.py P08 P31
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, hilbert, sosfiltfilt

sys.path.insert(0, str(Path(__file__).parent))
from gerakeeg import data, epoch, jendela, kanal, koreksi_global as kg, kualitas, lonjakan  # noqa: E402
from gerakeeg.grafik import GRID, INK, INK2, SURFACE  # noqa: E402
from gerakeeg.istilah import ISTIRAHAT, KANAL  # noqa: E402

OUT = Path(__file__).parent / "hasil" / "visual_tahap"
FASE = ["Pra-Gerak", "Gerak", "Tahan", "Naik", "Pasca-Naik", "Berdiri"]
WARNA = {"Pra-Gerak": "#e87ba4", "Gerak": "#2a78d6", "Tahan": "#1baf7a", "Naik": "#eb6834",
         "Pasca-Naik": "#4a3aa7", "Berdiri": "#eda100"}          # divalidasi (CVD lolos); label langsung dipasang
TAMPIL = ["Fp1", "F3", "C3", "P3", "O1", "C4", "P4", "O2"]
DATAR_WARNA, REKON_WARNA = "#a9a8a2", "#d03b3b"


def _gaya(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(labelsize=7, colors=INK2)
    ax.grid(axis="x", color=GRID, lw=0.5)


def _fase_span(ax, ep, rng, label=False, y=None):
    for f in FASE:
        g = ep[ep.fase == f]
        if not len(g):
            continue
        a, b = g.mulai.min() - rng[0], g.selesai.max() - rng[0]
        ax.axvspan(a, b, color=WARNA[f], alpha=0.10, lw=0)
        if label:
            ax.text((a + b) / 2, y, f, ha="center", va="bottom", fontsize=7, color=INK)
            ax.plot([a, b], [y - 0.02 * abs(y) - 5] * 2, color=WARNA[f], lw=3, solid_capstyle="butt")


def _tumpuk(ax, x, t, idx, jarak, warna=INK2, lw=0.6):
    for j, k in enumerate(idx):
        ax.plot(t, x[k] - j * jarak, color=warna, lw=lw)
    ax.set_yticks([-j * jarak for j in range(len(idx))], [KANAL[k] for k in idx], fontsize=7)


def a2_kontinu(xa, datar, sf):
    """Referensi A2 per blok 1 dtk (sama dengan jendela analisis)."""
    n = int(sf)
    y = np.full_like(xa, np.nan)
    for a in range(0, xa.shape[1] - n + 1, n):
        y[:, a:a + n], _ = kanal.robust(xa[:, a:a + n], datar[:, a:a + n].mean(axis=1))
    return y


def pita(x, sf, lo, hi):
    sos = butter(4, [lo, hi], btype="band", fs=sf, output="sos")
    v = sosfiltfilt(sos, np.nan_to_num(x))
    return v, np.abs(hilbert(v))


def gambar(pid, gerakan="Agem Kanan", rep=1):
    OUT.mkdir(parents=True, exist_ok=True)
    raw = data.muat_edf(pid)
    rp, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
    W = jendela.jendela(rp, tt)
    xm, xf, datar, sf = kualitas.sinyal(raw)
    T = xf.shape[1] / sf
    xa, info = lonjakan.asr(xf, datar, sf, W, 20)
    y = a2_kontinu(xa, datar, sf)
    TR = epoch.potong_TR(W, T)
    ep = TR[(TR.gerakan == gerakan) & (TR.rep == rep)]
    r = rp[(rp.gerakan == gerakan) & (rp.rep == rep)].iloc[0]
    rng = (r.onset_Gerak - 3.0, min(ep.selesai.max() + 0.5, T))
    i0, i1 = int(rng[0] * sf), int(rng[1] * sf)
    t = np.arange(i0, i1) / sf - rng[0]
    idx = [KANAL.index(c) for c in TAMPIL]
    judul = f"{pid} — {gerakan} repetisi {rep} (detik {rng[0]:.1f}–{rng[1]:.1f} EEG, offset 0)"

    # ---------- Gambar 1: tahap 0–3 ----------
    jarak = 150.0
    fig, axes = plt.subplots(4, 1, figsize=(13, 17), sharex=True, facecolor=SURFACE,
                             gridspec_kw=dict(hspace=0.28))
    mentah = xm[:, i0:i1] - np.median(xm[:, i0:i1], axis=1, keepdims=True)
    rekon = np.abs(xa - xf)[:, i0:i1] > 1.0
    tahap = [("Tahap 0 — Mentah (EDF, referensi telinga A1/A2, hanya dikurangi median)", mentah, None),
             ("Tahap 1 — Bandpass 1–35 Hz; abu-abu = sinyal datar (reset amplifier KT88)", xf[:, i0:i1], "datar"),
             ("Tahap 2 — + ASR k = 20 per belahan; merah = bagian yang direkonstruksi ASR", xa[:, i0:i1], "asr"),
             ("Tahap 3 — + referensi A2 (rata-rata belahan, robust) = sinyal yang dianalisis", y[:, i0:i1], None)]
    for ax, (jd, x, tanda) in zip(axes, tahap):
        _gaya(ax)
        _fase_span(ax, ep, rng, label=True, y=jarak * 0.9)
        _tumpuk(ax, np.clip(x, -jarak * 1.4, jarak * 1.4), t, idx, jarak)
        for j, k in enumerate(idx):
            if tanda == "datar":
                m = datar[k, i0:i1]
                ax.fill_between(t, -j * jarak - 60, -j * jarak + 60, where=m, color=DATAR_WARNA, alpha=0.5, lw=0)
            if tanda == "asr":
                m = rekon[k]
                ax.plot(t[m], (x[k] - j * jarak)[m], ".", ms=1.2, color=REKON_WARNA)
        ptp = np.nanmedian(np.ptp(np.nan_to_num(x[idx]), axis=1))
        ax.set_title(f"{jd}\nmedian peak-to-peak kanal tampil: {ptp:.0f} µV", fontsize=9, color=INK, loc="left")
        ax.set_ylim(-(len(idx) - 1) * jarak - jarak, jarak * 1.35)
    axes[-1].set_xlabel("detik sejak 3 dtk sebelum onset Gerak", fontsize=8, color=INK2)
    fig.suptitle(judul + f"\nskala: jarak antar kanal {jarak:.0f} µV; ASR kalibrasi kiri "
                 f"{info.get('kalibrasi_kiri_dtk')} dtk, kanan {info.get('kalibrasi_kanan_dtk')} dtk",
                 fontsize=10, color=INK, x=0.01, ha="left")
    fig.savefig(OUT / f"{pid}_1_gelombang_tahap0-3.png", dpi=110, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)

    # ---------- Gambar 2: tahap 4–5 ----------
    ist = W[W.fase == ISTIRAHAT]
    ist_idx = np.concatenate([np.arange(int(w.mulai * sf), int(min(w.selesai, T) * sf)) for w in ist.itertuples()])
    fig, axes = plt.subplots(5, 1, figsize=(13, 15), sharex=True, facecolor=SURFACE,
                             gridspec_kw=dict(hspace=0.35, height_ratios=[1.3, 1, 1, 1, 1]))
    ax = axes[0]
    _gaya(ax)
    _fase_span(ax, ep, rng, label=True, y=260)
    for j, c in enumerate(["C3", "C4"]):
        k = KANAL.index(c)
        ax.plot(t, y[k, i0:i1] - j * 150, color=INK2, lw=0.7)
        ax.text(-0.3, -j * 150, c, ha="right", va="center", fontsize=8, color=INK)
        for e in ep.itertuples():
            a, b = int(round(e.mulai * sf)), int(round(e.selesai * sf))
            _, _, ok = epoch._potong(xa, datar, a, b, kanal.robust)
            yy = -j * 150 - 85 - (e.Index % 4) * 6
            ax.plot([e.mulai - rng[0], e.selesai - rng[0]], [yy, yy], lw=2.2,
                    color=WARNA[e.fase] if ok[k] else DATAR_WARNA, solid_capstyle="butt")
    ax.set_yticks([])
    ax.set_title("Tahap 4 — Jendela TR (1 dtk, geser 0,25 dtk) di bawah tiap kanal: berwarna = bersih & dipakai, "
                 "abu-abu = dibuang (datar atau > 150 µV)", fontsize=9, color=INK, loc="left")
    for row, (nama, lo, hi) in enumerate([("mu 8–13 Hz", 8, 13), ("beta 13–30 Hz", 13, 30)]):
        for j, c in enumerate(["C3", "C4"]):
            k = KANAL.index(c)
            v, env = pita(y[k], sf, lo, hi)
            ref = np.nanmean(env[ist_idx])
            ax = axes[1 + row * 2 + j]
            _gaya(ax)
            _fase_span(ax, ep, rng)
            ax.plot(t, v[i0:i1], color=INK2, lw=0.5)
            ax.plot(t, env[i0:i1], color=INK, lw=1.4, label="selubung (amplitudo)")
            ax.axhline(ref, color=REKON_WARNA, lw=1.2, ls="--", label="rata-rata selubung Istirahat")
            ax.set_ylim(-3 * ref, 4 * ref)
            ax.set_ylabel("µV", fontsize=7, color=INK2)
            ax.set_title(f"Tahap 5 — {c}, {nama}: selubung di bawah garis putus = ERD (power turun), di atas = ERS",
                         fontsize=9, color=INK, loc="left")
            if row == 0 and j == 0:
                ax.legend(fontsize=7, frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
    axes[-1].set_xlabel("detik sejak 3 dtk sebelum onset Gerak", fontsize=8, color=INK2)
    fig.suptitle(judul, fontsize=10, color=INK, x=0.01, ha="left")
    fig.savefig(OUT / f"{pid}_2_jendela_dan_pita.png", dpi=110, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)

    # ---------- Gambar 3: tahap 6–7 ----------
    meta, P, OK = kg.spektrum_jendela(pid, skema_epoch="TR")
    sen = [KANAL.index("C3"), KANAL.index("C4")]
    F = kg.F

    def rata(mask):
        vals = [P[mask & OK[:, k], k].mean(axis=0) for k in sen if (mask & OK[:, k]).any()]
        return np.mean(vals, axis=0) if vals else np.full(len(F), np.nan)

    ref = rata((meta.fase == ISTIRAHAT).values)
    tot = lambda p: p[(F >= 4) & (F < 31)].mean()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), facecolor=SURFACE, gridspec_kw=dict(wspace=0.28))
    for ax, (jd, norm) in zip(axes[:2], [("Tahap 6a — M0: power fase / power Istirahat", False),
                                          ("Tahap 6b — M2b: dinormalisasi power 4–30 Hz dulu", True)]):
        _gaya(ax)
        ax.axvspan(8, 13, color=GRID, alpha=0.6, lw=0)
        ax.axvspan(13, 30, color=GRID, alpha=0.25, lw=0)
        ax.axhline(0, color=INK, lw=0.8)
        for f in FASE:
            p = rata((meta.fase == f).values)
            v = 10 * np.log10((p / tot(p)) / (ref / tot(ref))) if norm else 10 * np.log10(p / ref)
            ax.plot(F, v, color=WARNA[f], lw=2, label=f)
            ax.text(F[-1] + 0.3, v[-1], f, fontsize=6.5, color=INK, va="center")
        ax.set_xlim(2, 38)
        ax.set_ylim(-8, 8)
        ax.set_xlabel("frekuensi (Hz)", fontsize=8, color=INK2)
        ax.set_ylabel("dB relatif Istirahat (C3/C4)", fontsize=8, color=INK2)
        ax.text(10.5, 7.3, "mu", ha="center", fontsize=7, color=INK2)
        ax.text(21.5, 7.3, "beta", ha="center", fontsize=7, color=INK2)
        ax.set_title(jd, fontsize=9, color=INK, loc="left")
    S = pd.read_csv(Path(__file__).parent / "hasil" / "pilot_analisis" / "S1_ERD_sentral_per_fase.csv")
    S = S[S.participant_id == pid]
    ax = axes[2]
    _gaya(ax)
    ax.axhline(0, color=INK, lw=0.8)
    x = np.arange(len(FASE))
    for dx, (b, gaya) in zip((-0.18, 0.18), [("mu", dict(fill=True)), ("beta", dict(fill=False, hatch="///"))]):
        for i, f in enumerate(FASE):
            s = S[(S.fase == f) & (S.pita == b)]
            if not len(s):
                continue
            s = s.iloc[0]
            ax.bar(i + dx, s.rerata, width=0.32, color=WARNA[f] if gaya["fill"] else SURFACE,
                   edgecolor=WARNA[f], hatch=gaya.get("hatch"), lw=1.2)
            if np.isfinite(s.ci_bawah):
                ax.plot([i + dx] * 2, [s.ci_bawah, s.ci_atas], color=INK2, lw=0.8)
    ax.set_xticks(x, FASE, fontsize=7, rotation=20)
    ax.set_ylim(-5, 3)
    ax.set_ylabel("dB (M2b), rata-rata repetisi ± IK 95%", fontsize=8, color=INK2)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=INK2, label="mu (isi)"),
                       Patch(facecolor=SURFACE, edgecolor=INK2, hatch="///", label="beta (arsir)")],
              fontsize=7, frameon=False, loc="lower right")
    ax.set_title("Tahap 7 — Nilai akhir sentral per fase (M2b)", fontsize=9, color=INK, loc="left")
    fig.suptitle(f"{pid} — spektrum C3/C4 semua repetisi (jendela TR bersih, referensi A2)", fontsize=10,
                 color=INK, x=0.01, ha="left")
    fig.savefig(OUT / f"{pid}_3_spektrum_dan_nilai.png", dpi=110, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(pid, "selesai", flush=True)


if __name__ == "__main__":
    for pid in sys.argv[1:] or ["P08", "P31"]:
        gambar(pid)
