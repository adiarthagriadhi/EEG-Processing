"""Laporan grup (Paper A/B/D). Data simulasi dan riil TIDAK PERNAH dicampur."""
import html

import numpy as np
import pandas as pd

from . import stats as st
from .endpoints import PHASES
from .report import _img, _table, plt

GC = {"penari": "#d95f02", "non-penari": "#1b9e77"}


def _phase_profile(pre, title, real=None):
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.3))
    for ax, (m, lab) in zip(axes, [("erd_beta", "ERD beta kontra (%)"),
                                   ("erd_mu", "ERD mu kontra (%)"),
                                   ("theta_front", "theta F3/F4 (%)"), ("li_mu", "LI mu")]):
        for g, c in GC.items():
            v = pre[pre.group == g][[f"{m}_{ph}" for ph in PHASES]]
            mu, se = v.mean(), v.std() / np.sqrt(v.notna().sum())
            ax.errorbar(range(4), mu, yerr=se, color=c, marker="o", capsize=3,
                        label=f"{g} (n={len(v)})")
        ax.axhline(0, color="grey", lw=0.8)
        ax.set_xticks(range(4), PHASES)
        ax.set_title(lab, fontsize=10)
    axes[0].legend(fontsize=7)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    return _img(fig)


def _real_profile(real):
    fig, axes = plt.subplots(1, 4, figsize=(15, 3))
    for ax, m in zip(axes, ["erd_beta", "erd_mu", "theta_front", "li_mu"]):
        for _, r in real.iterrows():
            ax.plot(range(4), [r.get(f"{m}_{ph}", np.nan) for ph in PHASES], "k-", marker="x",
                    label=r.participant_id)
        ax.axhline(0, color="grey", lw=0.8)
        ax.set_xticks(range(4), PHASES)
        ax.set_title(f"{m} (riil)", fontsize=10)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    return _img(fig)


def _age_plot(pre, y):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    for g, c in GC.items():
        s = pre[pre.group == g].dropna(subset=[y, "age"])
        ax.scatter(s.age, s[y], color=c, label=g, s=18)
        if len(s) > 2:
            b = np.polyfit(s.age, s[y], 1)
            xs = np.linspace(s.age.min(), s.age.max(), 10)
            ax.plot(xs, np.polyval(b, xs), color=c)
    ax.set_xlabel("usia (tahun)")
    ax.set_ylabel(y)
    ax.legend(fontsize=8)
    return _img(fig)


def _paper_d_plot(pre):
    feats = ["alpha_occ_EC", "alpha_reactivity_EC_EO", "theta_front_EC", "stork_time_sec"]
    fig, axes = plt.subplots(1, len(feats) + 1, figsize=(17, 3.3))
    for ax, f in zip(axes, feats):
        data = [pre[pre.group == g][f].dropna() for g in GC]
        bp = ax.boxplot(data, patch_artist=True)
        for patch, c in zip(bp["boxes"], GC.values()):
            patch.set_facecolor(c)
            patch.set_alpha(0.5)
        ax.set_xticks([1, 2], list(GC))
        ax.set_title(f, fontsize=9)
    ax = axes[-1]
    for g, c in GC.items():
        s = pre[pre.group == g]
        ax.scatter(s.alpha_reactivity_EC_EO, s.stork_time_sec, color=c, s=18, label=g)
    ax.set_xlabel("reaktivitas alpha EC/EO")
    ax.set_ylabel("Stork Test (dtk)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    return _img(fig)


def _paper_b_plot(ind):
    fig, ax = plt.subplots(1, 3, figsize=(15, 3.4))
    for _, r in ind.iterrows():
        ax[0].plot([0, 1], [r.pre, r.post], color="#1b9e77" if r.berubah_nyata else "grey",
                   marker="o")
    ax[0].plot([0, 1], [ind.benchmark_penari_usia.mean()] * 2, "k:", label="benchmark penari")
    ax[0].set_xticks([0, 1], ["pre", "post"])
    ax[0].set_title("ERD beta TAHAN per individu (hijau = |RCI| ≥ 1,96)", fontsize=9)
    ax[0].legend(fontsize=7)
    o = ind.sort_values("rci")
    ax[1].barh(o.participant_id, o.rci, color=np.where(o.berubah_nyata, "#1b9e77", "grey"))
    ax[1].axvline(-1.96, color="k", ls="--")
    ax[1].axvline(1.96, color="k", ls="--")
    ax[1].set_title("Reliable Change Index", fontsize=9)
    o = ind.sort_values("gap_closure_pct")
    ax[2].barh(o.participant_id, o.gap_closure_pct, color="#7570b3")
    ax[2].axvline(100, color="k", ls="--")
    ax[2].set_title("Gap Closure (%) vs benchmark penari sesuai usia", fontsize=9)
    fig.tight_layout()
    return _img(fig)


def write(data, out_path, real=None):
    if data.is_simulated.nunique() != 1:
        raise ValueError("data simulasi dan riil tercampur")
    sim = bool(data.is_simulated.iloc[0])
    pre = data[data.timepoint.fillna("pre") == "pre"]
    P = ["<h1>Laporan Grup — Paper A, D, B</h1>"]
    if sim:
        P.append("<p class='bad' style='font-size:20px'><b>[SIMULATED RESULTS]</b> — data karangan "
                 "untuk menunjukkan bentuk akhir analisis. Besaran efek BUKAN hipotesis atau "
                 "temuan. Jangan dikutip.</p>")
    P.append(f"<p>n = {pre.participant_id.nunique()} partisipan (penari "
             f"{(pre.group == 'penari').sum()}, non-penari {(pre.group == 'non-penari').sum()}); "
             "non-penari memakai data <b>pre</b> untuk Paper A & D. Fase: PRA = 2 dtk sebelum "
             "onset gerak aktual, TURUN, TAHAN, NAIK (baseline −5…−3 dtk).</p>")
    # Paper A
    a, sens = st.paper_a(pre)
    P.append("<h2>Paper A — Movement generation (ERD/ERS, LI)</h2>")
    P.append(_phase_profile(pre, "Profil fase (rata-rata ± SE)"))
    if real is not None and len(real):
        P.append("<h3>Data riil tersedia (TIDAK ikut dalam statistik simulasi)</h3>" +
                 _real_profile(real) + _table(real[["participant_id"] + [
                     f"{m}_{ph}" for m in ("erd_beta", "erd_mu", "theta_front", "li_mu")
                     for ph in PHASES if f"{m}_{ph}" in real]]))
    P.append("<h3>Welch's t-test per indeks × fase (BH atas 16 uji)</h3>" + _table(
        a[["indeks", "n_penari", "n_nonpenari", "mean_penari", "mean_nonpenari", "hedges_g",
           "t", "p", "p_fdr"]]))
    P.append("<h3>Interaksi grup × usia (ERD beta TAHAN) — uji sensitivitas</h3>" +
             _table(sens, "{:.3f}") + _age_plot(pre, "erd_beta_TAHAN"))
    # Paper D
    g, c, cg = st.paper_d(pre)
    P.append("<h2>Paper D — Kontrol postural (Romberg × Stork Test)</h2>")
    P.append(_paper_d_plot(pre))
    P.append("<h3>Welch penari vs non-penari (BH)</h3>" + _table(
        g[["indeks", "mean_penari", "mean_nonpenari", "hedges_g", "t", "p", "p_fdr"]]))
    P.append("<h3>Korelasi parsial Spearman fitur Tier 1 × Stork Test, sampel gabungan</h3>"
             "<p>Dikontrol usia (utama) dan usia + grup (sensitivitas: korelasi yang hilang "
             "setelah grup dikontrol kemungkinan hanya mencerminkan beda grup).</p>" +
             _table(c.merge(cg[["fitur", "r", "p_fdr"]], on="fitur",
                            suffixes=("_usia", "_usia+grup"))))
    # Paper B
    if (data.timepoint == "post").any():
        b, ind, rel = st.paper_b(data)
        P.append("<h2>Paper B — Pre–post 6 minggu (non-penari)</h2>")
        P.append(f"<p>Reliabilitas split-half (Spearman-Brown) r<sub>xx</sub> = {rel['rxx']:.2f} "
                 f"(dari data, bukan placeholder); S<sub>diff</sub> = {rel['s_diff']:.2f}. "
                 "Catatan: reliabilitas dalam sesi → RCI cenderung liberal.</p>")
        P.append(_table(b, "{:.3f}") + _paper_b_plot(ind) + _table(ind))
    css = ("body{font-family:system-ui,sans-serif;max-width:1250px;margin:24px auto;padding:0 16px}"
           "img{max-width:100%}.bad{color:#b00020}table.t{border-collapse:collapse;font-size:12px}"
           ".t td,.t th{padding:2px 6px;border-bottom:1px solid #ddd}")
    out_path.write_text("<!doctype html><meta charset='utf-8'><title>Laporan grup</title>"
                        f"<style>{css}</style>" + "\n".join(P))
    return out_path
