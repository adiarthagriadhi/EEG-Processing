"""Laporan QC HTML per partisipan (satu file, gambar tertanam base64)."""
import base64
import html
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLORS = {"TURUN": "#d95f02", "TAHAN": "#1b9e77", "NAIK": "#7570b3"}


def _img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
    plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'


def _table(df, float_fmt="{:.2f}"):
    return df.to_html(index=False, float_format=lambda x: float_fmt.format(x), border=0,
                      classes="t", na_rep="—")


def fig_timeline(tl, offset, eeg_dur):
    fig, ax = plt.subplots(figsize=(12, 2.2))
    for _, r in tl.iterrows():
        c = COLORS.get(r.subphase, "#bbbbbb" if "ISTIRAHAT" in r.task or "RILEKS" in r.task
                       else "#e6ab02" if "MATA" in r.task else "#999999")
        ax.barh(0, r.end - r.start, left=r.start, color=c, edgecolor="none")
    if offset is not None:
        ax.axvline(-offset, color="k", ls="--", lw=1)
        ax.axvline(eeg_dur - offset, color="red", lw=2)
        ax.text(eeg_dur - offset, 0.45, " akhir EEG", color="red", va="center")
    ax.set_yticks([])
    ax.set_xlabel("waktu video (dtk)")
    ax.set_title("Timeline HUD (oranye TURUN, hijau TAHAN, ungu NAIK, kuning Romberg)")
    return _img(fig)


def fig_sync(P, res):
    c = np.load(P.out("sync_curves.npz"))
    fig, ax = plt.subplots(1, 2, figsize=(12, 3))
    ax[0].plot(c["lags_coarse"], c["cc_coarse"])
    ax[0].axvline(res["coarse_sec"], color="r", ls="--")
    ax[0].set_title("Kasar: boxcar HUD vs EEG 20–34 Hz")
    ax[0].set_xlabel("lag (dtk)")
    ax[1].plot(c["lags_fine"], c["cc_fine"])
    ax[1].axvline(res["fine_sec"], color="r", ls="--")
    ax[1].set_title("Halus: gerak video vs EEG (sekitar hasil kasar)")
    ax[1].set_xlabel("lag tambahan (dtk)")
    return _img(fig)


def fig_reps(reps, pose):
    moves = ["NGEED", "AGEM KANAN", "AGEM KIRI"]
    n = int(reps.rep.max()) if len(reps) else 4
    fig, axes = plt.subplots(len(moves), n, figsize=(3.2 * n, 2.2 * len(moves)), squeeze=False)
    t, y = pose["t"], pose["trunk_y"]
    for i, mv in enumerate(moves):
        for j in range(n):
            ax = axes[i][j]
            r = reps[(reps.task == mv) & (reps.rep == j + 1)]
            if r.empty:
                ax.axis("off")
                continue
            r = r.iloc[0]
            m = (t >= r.hud_turun - 1) & (t <= r.hud_end + 3)
            ax.plot(t[m] - r.hud_turun, y[m], "k", lw=0.8)
            for ph, key in [("TURUN", "hud_turun"), ("TAHAN", "hud_tahan"), ("NAIK", "hud_naik")]:
                ax.axvline(r[key] - r.hud_turun, color=COLORS[ph], ls=":", lw=1)
            for ph, key in [("TURUN", "act_turun"), ("TAHAN", "act_tahan"), ("NAIK", "act_naik")]:
                if np.isfinite(r[key]):
                    ax.axvline(r[key] - r.hud_turun, color=COLORS[ph], lw=1.5)
            if np.isfinite(r.act_end):
                ax.axvline(r.act_end - r.hud_turun, color="grey", lw=1.5)
            ax.invert_yaxis()
            ax.set_title(f"{mv} rep{j + 1}: {r.compliance}", fontsize=9,
                         color="k" if r.compliance in ("ok", "late") else "red")
            ax.tick_params(labelsize=7)
    fig.suptitle("Batang tubuh (y, piksel; turun = ke bawah). Titik-titik = HUD, garis = aktual",
                 fontsize=10)
    fig.tight_layout()
    return _img(fig)


def fig_erd(tab):
    s = tab[tab.channel.isin(["C3", "C4"]) & tab.band.isin(["mu", "beta"])]
    g = s.groupby(["task", "phase", "band", "channel"]).erd_pct.mean().unstack(["band", "channel"])
    fig, ax = plt.subplots(figsize=(10, 3))
    g.plot.bar(ax=ax)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("%ERD/ERS (rata-rata repetisi)")
    ax.legend(fontsize=7, ncol=4)
    return _img(fig)


def write(ctx, cfg):
    P = ctx["P"]
    parts = [f"<h1>QC {html.escape(P.pid)}</h1>"]
    if cfg.get("is_simulated"):
        parts.insert(0, "<p class='bad'>[SIMULATED RESULTS]</p>")
    if ctx["problems"]:
        parts.append("<h2 class='bad'>Perlu tindakan</h2><ul>" +
                     "".join(f"<li>{html.escape(p)}</li>" for p in ctx["problems"]) + "</ul>")
    else:
        parts.append("<p class='ok'>Semua gerbang QC lolos.</p>")
    raw, tl = ctx["raw"], ctx["tl"]
    offset = ctx.get("offset")
    parts.append(f"<h2>1. Timeline & cakupan</h2><p>Durasi EEG {raw.times[-1]:.1f} dtk; "
                 f"video {ctx['pose']['t'][-1]:.1f} dtk; offset "
                 f"{'—' if offset is None else f'{offset:+.2f} dtk'} "
                 f"(t_eeg = t_video + offset).</p>")
    parts.append(fig_timeline(tl, offset, raw.times[-1]))
    if P.out("sync.json").exists():
        import json
        res = json.loads(P.out("sync.json").read_text())
        parts.append("<h2>2. Sinkronisasi</h2>")
        parts.append(f"<p>kasar {res['coarse_sec']:+.1f} dtk (r {res['r_coarse']:.2f}; puncak "
                     f"lain {res['r_coarse_second']:.2f}), halus {res['fine_sec']:+.1f} dtk "
                     f"(r {res['r_fine']:.2f}), drift {res['drift_sec']:+.2f} dtk</p>")
        parts.append(fig_sync(P, res))
    if "reps" in ctx:
        reps = ctx["reps"]
        parts.append("<h2>3. Fase gerak aktual</h2>")
        parts.append(fig_reps(reps, ctx["pose"]))
        cols = ["task", "rep", "compliance", "hud_turun", "act_turun", "act_tahan", "act_naik",
                "act_end", "depth_px", "pose_valid_frac", "ocr_protocol_dev"]
        parts.append(_table(reps[[c for c in cols if c in reps]]))
    dec = P.decisions()
    if "clean" in ctx:
        parts.append(f"<h2>4. Preprocessing</h2><p>Kanal buruk: {dec.get('bad_channels', [])}; "
                     f"komponen ICA dibuang: {dec.get('ica_exclude')} "
                     f"({html.escape(str(dec.get('ica_method')))})</p>")
    if ctx.get("erd") is not None and len(ctx["erd"]):
        parts.append("<h2>5. ERD/ERS (C3/C4)</h2>")
        parts.append(fig_erd(ctx["erd"]))
    if "romberg" in ctx:
        rb = ctx["romberg"]
        parts.append("<h2>6. Romberg</h2><p>Cakupan EEG: EO "
                     f"{rb['coverage_EO']:.0%} ({rb['clean_sec_EO']:.0f} dtk bersih), EC "
                     f"{rb['coverage_EC']:.0%} ({rb['clean_sec_EC']:.0f} dtk bersih). "
                     f"Fitur dengan cakupan kurang ditulis NaN.</p>")
    css = ("body{font-family:system-ui,sans-serif;max-width:1200px;margin:24px auto;padding:0 16px}"
           "img{max-width:100%}.bad{color:#b00020}.ok{color:#1b7e3c}"
           "table.t{border-collapse:collapse;font-size:12px}.t td,.t th{padding:2px 6px;"
           "border-bottom:1px solid #ddd}")
    out = P.report_dir / f"{P.pid}_qc.html"
    out.write_text(f"<!doctype html><meta charset='utf-8'><title>QC {P.pid}</title>"
                   f"<style>{css}</style>" + "\n".join(parts))
    return out
