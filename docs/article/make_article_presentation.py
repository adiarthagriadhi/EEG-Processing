"""Penyajian data artikel (Paper A & D) dari kohort SINTETIS yang diturunkan dari P02
(penari) dan P10 (non-penari). Semua gambar & tabel diberi label SIMULATED.
Jalankan dari root repo: python docs/article/make_article_presentation.py"""
import base64
import html
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eegpipe import stats as st  # noqa: E402
from eegpipe import synthetic  # noqa: E402
from eegpipe.endpoints import PHASES  # noqa: E402

OUT = Path(__file__).resolve().parent
GROUPS = {"penari": ("Dancers", "#2a78d6"), "non-penari": ("Non-dancers", "#eb6834")}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
TEMPLATES = {"penari": "P02", "non-penari": "P10"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False})


def stamp(fig, text):
    fig.text(0.995, 0.005, text, ha="right", va="bottom", fontsize=7, color="#9a9994")


def save(fig, name, label="SIMULATED DATA"):
    stamp(fig, label)
    p = OUT / name
    fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def welch_row(d, col, label):
    a = d.loc[d.group == "penari", col].dropna()
    b = d.loc[d.group == "non-penari", col].dropna()
    if len(a) < 3 or len(b) < 3:            # template partisipan tanpa nilai (mis. theta NAIK P02)
        return None
    t, p = stats.ttest_ind(a, b, equal_var=False)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    J = 1 - 3 / (4 * (len(a) + len(b)) - 9)
    g = J * (a.mean() - b.mean()) / sp
    se = np.sqrt((len(a) + len(b)) / (len(a) * len(b)) + g ** 2 / (2 * (len(a) + len(b))))
    return dict(Measure=label, Dancers=f"{a.mean():.2f} ± {a.std():.2f}",
                **{"Non-dancers": f"{b.mean():.2f} ± {b.std():.2f}"},
                t=round(t, 2), df=round(df, 1), p=p,
                **{"Hedges g [95% CI]": f"{g:.2f} [{g - 1.96 * se:.2f}, {g + 1.96 * se:.2f}]"})


def fdr_col(tab):
    from statsmodels.stats.multitest import multipletests
    tab["p (FDR)"] = multipletests(tab.p, method="fdr_bh")[1]
    tab["p"] = tab.p.map(lambda v: f"{v:.3f}" if v >= 0.001 else "<0.001")
    tab["p (FDR)"] = tab["p (FDR)"].map(lambda v: f"{v:.3f}" if v >= 0.001 else "<0.001")
    return tab


def main():
    res = ROOT / "results"
    parts = pd.read_csv(ROOT / "data" / "participants.csv")
    d = synthetic.cohort(res, TEMPLATES, parts)
    for ph in PHASES:
        for m in ("erd_mu", "erd_beta", "theta_front"):
            d[f"{m}_{ph}_db"] = synthetic.to_db(d[f"{m}_{ph}"])
    d.to_csv(OUT / "SIMULATED_cohort.csv", index=False)
    figs, tabs = {}, {}

    # ---------- Table 1: characteristics & data quality ----------
    rows = []
    for g, (lab, _) in GROUPS.items():
        s = d[d.group == g]
        rows.append({"Group": lab, "n": len(s),
                     "Age, years (mean ± SD; range)": f"{s.age.mean():.1f} ± {s.age.std():.1f} ({s.age.min()}–{s.age.max()})",
                     "Agem hold, s (median [IQR])": f"{s.hold_agem_sec.median():.2f} [{s.hold_agem_sec.quantile(.25):.2f}–{s.hold_agem_sec.quantile(.75):.2f}]",
                     "EEG–video offset, s (mean ± SD)": f"{s.sync_offset_sec.mean():.2f} ± {s.sync_offset_sec.std():.2f}",
                     "Interpolated channels (median)": f"{s.n_bad_channels.median():.0f}",
                     "Romberg EC coverage, % (median)": f"{100 * s.romberg_ec_coverage.median():.0f}"})
    tabs["Table 1. Participant characteristics and data quality"] = pd.DataFrame(rows)

    # ---------- Figure 2: phase profile of ERD (dB) ----------
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    rng = np.random.default_rng(1)
    for ax, band, title in zip(axes, ("mu", "beta"), ("Mu 8–13 Hz", "Beta 13–30 Hz")):
        for j, (g, (lab, col)) in enumerate(GROUPS.items()):
            s = d[d.group == g]
            xs = np.arange(4) + (j - 0.5) * 0.22
            vals = [s[f"erd_{band}_{ph}_db"].dropna() for ph in PHASES]
            for x, v in zip(xs, vals):
                ax.scatter(x + rng.uniform(-0.05, 0.05, len(v)), v, s=6, color=col, alpha=0.35,
                           linewidths=0)
            m = [v.mean() for v in vals]
            ci = [1.96 * v.std() / np.sqrt(len(v)) for v in vals]
            ax.errorbar(xs, m, yerr=ci, color=col, lw=2, marker="o", ms=5, capsize=0,
                        mec="white", mew=1.2, label=lab)
            if band == "mu":                  # label langsung di satu panel (panel lain: legenda)
                ax.text(xs[-1] + 0.12, m[-1], lab, color=INK, fontsize=8, va="center")
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xticks(range(4), ["Pre", "Descent", "Hold", "Rise"])
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_xlim(-0.5, 3.9)
    axes[0].set_ylabel("Power change, dB\n(negative = ERD)")
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    figs["Figure 2. Contralateral ERD/ERS across movement phases (agem). Points: participants; "
         "markers: group mean ± 95% CI. Power change relative to relaxed standing (−5 to −3 s)."] = \
        save(fig, "fig2_erd_phase_profile.png")

    # ---------- Figure 3: representative real TFR maps ----------
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), sharex=True, sharey=True)
    for i, (g, pid) in enumerate(TEMPLATES.items()):
        z = np.load(ROOT / "data" / "derivatives" / pid / "task_tfr.npz")
        tasks, chs = list(z["tasks"]), list(z["ch_names"])
        for j, (task, ch) in enumerate([("AGEM KANAN", "C3"), ("AGEM KIRI", "C4")]):
            k = tasks.index(task)
            ax = axes[i][j]
            data = 10 * np.log10(1 + z[f"data_{k}"][chs.index(ch)] / 100)
            im = ax.pcolormesh(z["times"], z["freqs"], data, cmap="RdBu_r", vmin=-6, vmax=6,
                               shading="auto", rasterized=True)
            ph = z[f"phases_{k}"]
            for x in ph[1:3]:
                ax.axvline(x, color=INK, lw=0.7, ls="--")
            ax.axvline(0, color=INK, lw=0.9)
            ax.set_title(f"{GROUPS[g][0][:-1]} ({pid}) · {task.title()} · {ch}", fontsize=8.5,
                         color=INK, loc="left")
            ax.set_xlim(-3, 7)
    for ax in axes[1]:
        ax.set_xlabel("Time from actual descent onset, s")
    for ax in axes[:, 0]:
        ax.set_ylabel("Frequency, Hz")
    cb = fig.colorbar(im, ax=axes, shrink=0.7, label="dB")
    cb.outline.set_visible(False)
    figs["Figure 3. Time–frequency maps from one representative participant per group "
         "(REAL data, contralateral channel, mean of 4 repetitions). Dashed lines: hold "
         "onset and rise onset (median)."] = save(fig, "fig3_representative_tfr.png",
                              "REAL DATA — single participants P02, P10")

    # ---------- Table 2: Paper A ----------
    rows = []
    for ph, phl in zip(PHASES, ["Pre", "Descent", "Hold", "Rise"]):
        for m, ml in (("erd_mu", "Mu ERD"), ("erd_beta", "Beta ERD"),
                      ("theta_front", "Frontal theta")):
            r = welch_row(d, f"{m}_{ph}_db", f"{ml} · {phl} (dB)")
            if r:
                rows.append(r)
    tabs["Table 2. Group comparison of movement-related power change (Welch's t-test; "
         f"FDR over {len(rows)} tests)"] = fdr_col(pd.DataFrame(rows))

    # ---------- Figure 4: Romberg & Stork ----------
    fig, axes = plt.subplots(1, 3, figsize=(8.0, 3.0), gridspec_kw={"width_ratios": [1, 1, 1.4]})
    for ax, col, lab in zip(axes[:2], ["alpha_occ_EC", "alpha_reactivity_EC_EO"],
                            ["Occipital alpha, EC\n(relative power)", "Alpha reactivity\n(EC / EO)"]):
        for j, (g, (gl, c)) in enumerate(GROUPS.items()):
            v = d.loc[d.group == g, col].dropna()
            ax.scatter(j + rng.uniform(-0.12, 0.12, len(v)), v, s=8, color=c, alpha=0.45,
                       linewidths=0)
            ax.plot([j - 0.22, j + 0.22], [v.median()] * 2, color=c, lw=2.2)
        ax.set_xticks([0, 1], ["Dancers", "Non-\ndancers"])
        ax.set_ylabel(lab)
        ax.set_xlim(-0.5, 1.5)
        ax.grid(axis="y", color=GRID, lw=0.6)
    if "alpha_reactivity_EC_EO" in d:
        axes[1].axhline(1, color=MUTED, lw=0.8, ls=":")
    ax = axes[2]
    for g, (gl, c) in GROUPS.items():
        s = d[d.group == g]
        ax.scatter(s.alpha_reactivity_EC_EO, s.stork_time_sec, s=12, color=c, label=gl,
                   edgecolors="white", linewidths=0.6)
    ax.set_xlabel("Alpha reactivity (EC / EO)")
    ax.set_ylabel("Stork Test, s (hypothetical)")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(color=GRID, lw=0.6)
    fig.tight_layout()
    figs["Figure 4. Romberg EEG features by group (lines: medians) and their relation to "
         "Standing Stork Test duration. Stork values are HYPOTHETICAL (no data received yet)."] = \
        save(fig, "fig4_romberg_stork.png")

    # ---------- Table 3: Paper D ----------
    feats = [("alpha_occ_EC", "Occipital alpha, EC"), ("alpha_reactivity_EC_EO", "Alpha reactivity EC/EO"),
             ("mu_sm_EC", "Sensorimotor mu, EC"), ("mu_sm_EO", "Sensorimotor mu, EO"),
             ("theta_front_EC", "Frontal theta, EC")]
    rows = []
    for c, lab in feats:
        if d[c].notna().sum() < 6:
            continue
        r = welch_row(d, c, lab)
        if r is None:
            continue
        pa = st.partial_spearman(d, c, "stork_time_sec", ["age"])
        pg = st.partial_spearman(d, c, "stork_time_sec", ["age", "group"])
        r["ρ with Stork | age"] = f"{pa['r']:.2f}"
        r["ρ with Stork | age + group"] = f"{pg['r']:.2f}"
        rows.append(r)
    tabs["Table 3. Romberg EEG features: group comparison (Welch) and partial Spearman "
         "correlation with Stork Test in the pooled sample (Stork values hypothetical)"] = \
        fdr_col(pd.DataFrame(rows))

    for title, t in tabs.items():
        t.to_csv(OUT / (title.split(".")[0].replace(" ", "_").lower() + ".csv"), index=False)
    write_html(figs, tabs)


def write_html(figs, tabs):
    css = """
    :root{--surface:#fcfcfb;--ink:#0b0b0b;--muted:#52514e;--rule:#e4e3df;--warn:#b00020}
    @media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--surface:#1a1a19;
      --ink:#ffffff;--muted:#c3c2b7;--rule:#3a3a38;--warn:#ff8a80}}
    :root[data-theme="dark"]{--surface:#1a1a19;--ink:#ffffff;--muted:#c3c2b7;--rule:#3a3a38;--warn:#ff8a80}
    body{background:var(--surface);color:var(--ink);font:15px/1.5 Georgia,serif;
      max-width:980px;margin:0 auto;padding:24px 16px}
    h1{font-size:24px;margin:0 0 4px} .warn{color:var(--warn);font-weight:bold}
    figure{margin:28px 0}figure img{width:100%;background:#fff;border:1px solid var(--rule)}
    figcaption,caption{font-size:13.5px;color:var(--muted);text-align:left;margin-top:6px}
    table{border-collapse:collapse;font:12.5px/1.4 system-ui,sans-serif;margin:28px 0;width:100%}
    caption{caption-side:top;margin-bottom:6px;font-weight:600;color:var(--ink)}
    th,td{padding:4px 8px;border-bottom:1px solid var(--rule);text-align:left}
    thead th{border-bottom:1.5px solid var(--ink)} .scroll{overflow-x:auto}"""
    P = [f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
         f"<title>Article data presentation</title><style>{css}</style>",
         "<h1>Article data presentation — Papers A and D</h1>",
         "<p class='warn'>SIMULATED DATA. Synthetic cohort (24 dancers, 14 non-dancers) derived "
         "from two real participants (P02 dancer, P10 non-dancer); Stork Test values are "
         "hypothetical. Layout and analysis only — do not cite any number.</p>",
         f"<figure><img src='data:image/png;base64,{b64(OUT / '..' / 'figures' / 'pipeline.png')}'>"
         "<figcaption>Figure 1. Processing pipeline.</figcaption></figure>"]
    items = list(tabs.items())
    P.append(tab_html(*items[0]))
    for i, (cap, path) in enumerate(figs.items()):
        P.append(f"<figure><img src='data:image/png;base64,{b64(path)}'><figcaption>{html.escape(cap)}"
                 "</figcaption></figure>")
        if i == 1:
            P.append(tab_html(*items[1]))
    P.append(tab_html(*items[2]))
    (OUT / "article_presentation.html").write_text("\n".join(P))
    print(OUT / "article_presentation.html")


def tab_html(title, t):
    return ("<div class='scroll'>" + t.to_html(index=False, border=0, escape=True)
            .replace("<table", f"<table><caption>{html.escape(title)}</caption", 1)
            .replace("<caption>", "", 0) + "</div>").replace("<table><caption>", "<table><caption>", 1)


def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()


if __name__ == "__main__":
    main()
