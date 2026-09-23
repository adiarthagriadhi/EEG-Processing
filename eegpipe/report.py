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
    ax[0].set_title("Kasar: kecepatan tubuh (pose) vs EEG 1–4 Hz")
    ax[0].set_xlabel("lag (dtk)")
    pr = res.get("per_rep", [])
    if pr:
        ax[1].scatter([p["t"] for p in pr], [p["offset"] for p in pr],
                      c=[p["r"] for p in pr], cmap="viridis")
        ax[1].axhline(res["offset_sec"], color="r", ls="--", label="offset sesi")
        ax[1].legend()
    ax[1].set_title(f"Offset lokal per repetisi (drift {res['drift_sec']:+.2f} dtk, "
                    f"p={res.get('drift_p', 1):.2f})")
    ax[1].set_xlabel("waktu video (dtk)")
    ax[1].set_ylabel("offset (dtk)")
    return _img(fig)


def fig_reps(reps, pose):
    moves = ["NGEED", "AGEM KANAN", "AGEM KIRI"]
    n = int(reps.rep.max()) if len(reps) else 4
    fig, axes = plt.subplots(len(moves), n, figsize=(3.2 * n, 2.2 * len(moves)), squeeze=False)
    t = pose["t"]
    y = pose["trunk_y"]
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
                         color="k" if r.compliance in ("ok", "late") else
                         "darkorange" if r.compliance == "hud_fallback" else "red")
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


def _topo_info(chs, cfg):
    import mne
    info = mne.create_info(list(chs), 100.0, "eeg")
    info.set_montage(cfg["eeg"]["montage"], verbose="error")
    return info


def participant_results(P, cfg):
    """Bagian 'Hasil partisipan': peta TFR C3/C4 per gerakan, topografi beta TAHAN,
    ringkasan ERD, dan LI. Endpoint utama = fase TAHAN (keputusan default, Pertanyaan 14)."""
    import mne
    import pandas as pd
    f = P.out("task_tfr.npz")
    if not f.exists():
        return ""
    z = np.load(f, allow_pickle=False)
    times, freqs, chs, tasks = z["times"], z["freqs"], list(z["ch_names"]), list(z["tasks"])
    bads = P.decisions().get("bad_channels", [])
    parts = ["<h2>7. Hasil partisipan</h2>",
             "<p>Endpoint utama ERD = <b>fase TAHAN</b> (diam menahan posisi). Fase TURUN/NAIK "
             "ditampilkan tetapi kemungkinan besar didominasi artefak gerak (lihat Pertanyaan 14). "
             f"Kanal interpolasi: {', '.join(bads) or '—'}.</p>"]
    # (a) peta TFR C3 & C4 per gerakan
    fig, axes = plt.subplots(2, len(tasks), figsize=(4.2 * len(tasks), 6), squeeze=False)
    for j, task in enumerate(tasks):
        d, ph = z[f"data_{j}"], z[f"phases_{j}"]
        for i, ch in enumerate(["C3", "C4"]):
            ax = axes[i][j]
            im = ax.pcolormesh(times, freqs, d[chs.index(ch)], cmap="RdBu_r", vmin=-100,
                               vmax=100, shading="auto")
            for x, lab in zip(ph, ["TURUN", "TAHAN", "NAIK", "akhir"]):
                ax.axvline(x, color="k", lw=0.8, ls="--")
            ax.axvspan(ph[1], ph[2], color="none", ec="g", lw=2)
            ax.set_title(f"{task} — {ch}{' (interp.)' if ch in bads else ''} (n={z['n'][j]})",
                         fontsize=9)
            ax.set_xlabel("dtk dari onset TURUN aktual")
            ax.set_ylabel("Hz")
    fig.colorbar(im, ax=axes, label="%ERD/ERS", shrink=0.6)
    parts.append("<h3>a. Peta waktu–frekuensi (%ERD/ERS; biru = ERD). Kotak hijau = TAHAN</h3>"
                 + _img(fig))
    # (b) topografi beta pada fase TAHAN per gerakan (nearest, tanpa interpolasi garis tengah)
    info = _topo_info(chs, cfg)
    fig, axes = plt.subplots(1, len(tasks), figsize=(3.6 * len(tasks), 3.4), squeeze=False)
    for j, task in enumerate(tasks):
        d, ph = z[f"data_{j}"], z[f"phases_{j}"]
        tm = (times >= ph[1]) & (times < ph[2])
        fm = (freqs >= 13) & (freqs < 30)
        val = d[:, fm][:, :, tm].mean(axis=(1, 2))
        mne.viz.plot_topomap(val, info, axes=axes[0][j], image_interp="nearest", contours=0,
                             cmap="RdBu_r", vlim=(-80, 80), show=False, names=chs)
        axes[0][j].set_title(f"{task}\nbeta 13–30 Hz, TAHAN", fontsize=9)
    parts.append("<h3>b. Topografi ERD beta (fase TAHAN, nearest-neighbour)</h3>" + _img(fig))
    # (c) ringkasan ERD C3/C4 per gerakan x fase x band
    tab = pd.read_csv(P.results_dir / f"{P.pid}_erd_ers.csv")
    s = (tab[tab.channel.isin(["C3", "C4"]) & tab.band.isin(["mu", "beta"])]
         .groupby(["task", "phase", "band", "channel"]).erd_pct.agg(["median", "count"])
         .round(1).unstack("channel"))
    s.columns = [f"{a}_{b}" for a, b in s.columns]
    parts.append("<h3>c. Ringkasan %ERD/ERS C3/C4 (median antar repetisi)</h3>" +
                 s.reset_index().to_html(index=False, border=0, classes="t"))
    # (d) Indeks Lateralisasi (AGEM, fase TAHAN)
    li_f = P.results_dir / f"{P.pid}_li.csv"
    if li_f.exists():
        li = pd.read_csv(li_f)
        li = li[li.phase == "TAHAN"]
        if len(li):
            g = li.groupby(["task", "band"]).agg(contra=("contra", "median"),
                                                ipsi=("ipsi", "median"),
                                                li_erd=("li_erd", "median"),
                                                n_valid=("li_erd", "count")).round(2)
            parts.append("<h3>d. Indeks Lateralisasi (AGEM, TAHAN; kontra = C3 untuk AGEM KANAN)"
                         "</h3>" + g.reset_index().to_html(index=False, border=0, classes="t"))
    return "\n".join(parts)


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
                     f"lain {res['r_coarse_second']:.2f}; diagnostik boxcar HUD "
                     f"{res.get('hud_boxcar_lag', float('nan')):+.1f} dtk, r {res.get('hud_boxcar_r', float('nan')):.2f}). "
                     f"Offset akhir {res['offset_sec']:+.2f} ± {res.get('offset_se_sec', float('nan')):.2f} dtk (SE) "
                     f"= median offset lokal {res.get('n_rep', '?')} repetisi (SD {res.get('per_rep_sd', float('nan')):.2f} dtk). "
                     f"Median {len(res['combos'])} kombinasi sinyal {res.get('combo_offset_sec', res['offset_sec']):+.2f} dtk "
                     f"(IQR {res['spread_sec']:.2f} dtk, r {res['r_fine']:.2f}).</p>")
        if res.get("warnings"):
            parts.append("<p><b>Peringatan sinkronisasi:</b> " + html.escape("; ".join(res["warnings"])) + "</p>")
        parts.append(fig_sync(P, res))
    if "reps" in ctx:
        reps = ctx["reps"]
        parts.append("<h2>3. Fase gerak aktual</h2>")
        parts.append(fig_reps(reps, ctx["pose"]))
        cols = ["task", "rep", "compliance", "hud_turun", "act_turun", "act_tahan", "act_naik",
                "act_end", "depth_px", "track_noise_px", "phase_source", "baseline_range_frac",
                "baseline_still", "pose_valid_frac",
                "ocr_protocol_dev"]
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
                     f"{rb['coverage_EO']:.0%} ({rb.get('sec_available_EO', 0):.1f} dtk tersedia), EC "
                     f"{rb['coverage_EC']:.0%} ({rb.get('sec_available_EC', 0):.1f} dtk tersedia). "
                     "Data yang tersedia dipakai walau segmen terpotong; artefak ditolak per "
                     f"fitur (hanya kanal fitur tsb, batas {cfg['romberg']['reject_uv']:.0f} µV "
                     "peak-to-peak). <b>n_win = jumlah jendela yang dipakai</b>.</p>")
        import pandas as pd
        rows = [dict(fitur=k, nilai=rb.get(k), n_win=rb.get(f"{k}_n_win"))
                for k in ["alpha_occ_EC", "alpha_reactivity_EC_EO", "mu_sm_EC", "mu_sm_EO",
                          "theta_front_EC", "theta_alpha_ratio_EC", "beta_sm_EO", "beta_sm_EC",
                          "alpha_par_EC", "iaf_occ_EC", "iaf_par_EC"]]
        parts.append(_table(pd.DataFrame(rows), "{:.3f}"))
        for cond in ("EO", "EC"):
            if isinstance(rb.get(f"ptp_median_{cond}"), str):
                parts.append(f"<p><small>Median peak-to-peak {cond} (µV): "
                             f"{html.escape(rb[f'ptp_median_{cond}'])}</small></p>")
    if ctx.get("erd") is not None and len(ctx["erd"]):
        parts.append(participant_results(P, cfg))
    css = ("body{font-family:system-ui,sans-serif;max-width:1200px;margin:24px auto;padding:0 16px}"
           "img{max-width:100%}.bad{color:#b00020}.ok{color:#1b7e3c}"
           "table.t{border-collapse:collapse;font-size:12px}.t td,.t th{padding:2px 6px;"
           "border-bottom:1px solid #ddd}")
    out = P.report_dir / f"{P.pid}_qc.html"
    out.write_text(f"<!doctype html><meta charset='utf-8'><title>QC {P.pid}</title>"
                   f"<style>{css}</style>" + "\n".join(parts))
    return out
