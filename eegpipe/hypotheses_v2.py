"""Hipotesis v2 (H6–H13), model campuran tingkat segmen, dan regresi dosis-respons durasi menari.
Semua endpoint dari keluaran tahap `segmen` (pendekatan v2). Definisi di config.yaml → hypotheses_v2.
Uji dijalankan pada (a) seluruh sampel dan (b) set KONFIRMATORI = partisipan di luar exploration_set
(yang membentuk hipotesis). Hasil (a) pada sampel pembentuk hipotesis = EKSPLORATIF."""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

VIDEO = lambda d: d[d.phase_source.fillna("video") != "hud_fallback"]


def endpoints(pid, res):
    am = pd.read_csv(res / f"{pid}_area_map.csv")
    du = pd.read_csv(res / f"{pid}_durasi.csv")
    a = am[(am.pool == "SEMUA") & (am.level == "area")].set_index(["unit", "phase"])
    g = lambda u, ph, col: a[col].get((u, ph), np.nan)
    v = VIDEO(du)
    th = v.dur_tahan.dropna()
    e = dict(participant_id=pid,
             dur_turun_sec=v.dur_turun.median(), dur_tahan_sec=th.median(),
             cv_tahan=th.std(ddof=1) / th.mean() if len(th) > 1 else np.nan,
             dur_naik_sec=v.dur_naik.median(), n_rep_video=len(v),
             mu_periodic_central_TURUN=g("sentral", "TURUN", "mu_periodic_db"),
             mu_periodic_posterior_TAHAN=np.nanmean([g("parietal", "TAHAN", "mu_periodic_db"),
                                                     g("temporo-posterior", "TAHAN", "mu_periodic_db")]),
             noise_floor_db=am.noise_floor_db.iloc[0])
    for ph in ("PRA", "TURUN", "TAHAN", "NAIK", "POST"):
        e[f"offset_central_{ph}"] = g("sentral", ph, "offset_change")
        e[f"n_seg_{ph}"] = a["n_seg"].get(("sentral", ph), 0)
    # H1–H5 (hipotesis awal) dari keluaran v2
    k = am[am.level == "kanal"].set_index(["pool", "unit", "phase"])
    kv = lambda pool, ch, ph, col: k[col].get((pool, ch, ph), np.nan)
    e["mu_periodic_contra_abs_TAHAN"] = np.nanmean([abs(kv("AGEM KANAN", "C3", "TAHAN", "mu_periodic_db")),
                                                    abs(kv("AGEM KIRI", "C4", "TAHAN", "mu_periodic_db"))])
    bl = am[(am.pool == "SEMUA") & (am.level == "belahan") & (am.phase == "TAHAN")]
    e["global_offset_TAHAN"] = bl.offset_change.mean()
    ag = v[v.task.isin(["AGEM KANAN", "AGEM KIRI"])]
    e["hold_agem_sec"] = ag.dur_tahan.median()
    rel = lambda chs, ph: np.nanmean([kv("SEMUA", c, ph, "mu_relative_db") for c in chs])
    e["mu_relative_FCP_left_TURUN"] = rel(["F3", "C3", "P3"], "TURUN")
    e["mu_relative_right_minus_left_TAHAN"] = rel(["C4", "F4"], "TAHAN") - rel(["C3", "F3"], "TAHAN")
    e["demand_minus_naik_offset_central"] = (np.nanmean([e["offset_central_TURUN"], e["offset_central_TAHAN"]])
                                             - e["offset_central_NAIK"])
    return e


def _alt(expect):
    """Alternatif untuk (penari − non-penari)."""
    e = expect.strip()
    if e.startswith("penari <") or e.startswith("non-penari >"):
        return "less"
    return "greater"                                   # "penari >" atau "non-penari <"


def _partial_spearman(d, x, y, covars):
    z = d[[x, y] + covars].dropna().rank()
    if len(z) < 5:
        return np.nan, np.nan, len(z)
    X = np.column_stack([np.ones(len(z))] + [z[c] for c in covars])
    rx = z[x] - X @ np.linalg.lstsq(X, z[x], rcond=None)[0]
    ry = z[y] - X @ np.linalg.lstsq(X, z[y], rcond=None)[0]
    r, _ = stats.pearsonr(rx, ry)
    dfree = len(z) - 2 - len(covars)
    t = r * np.sqrt(dfree / max(1e-12, 1 - r ** 2))
    return r, stats.t.sf(t, dfree), len(z)          # satu arah: rho > 0


def test(df, hyp, label):
    rows = []
    for h, d in hyp.items():
        eps = d["endpoint"] if isinstance(d["endpoint"], list) else [d["endpoint"]]
        if str(d["expect"]).startswith("rho"):
            cov = [c for c in ["age"] if c in df and df[c].notna().sum() >= 5]
            r, p, n = _partial_spearman(df, eps[0], eps[1], cov)
            rows.append(dict(sampel=label, hipotesis=h, endpoint=" ~ ".join(eps), expect=d["expect"],
                             n_total=n, statistik="Spearman parsial" + (" (kontrol usia)" if cov else " (TANPA kontrol usia)"),
                             effect=r, p_one_sided=p))
            continue
        for k, ep in enumerate(eps):
            a = df.loc[df.group == "penari", ep].dropna()
            b = df.loc[df.group == "non-penari", ep].dropna()
            r = dict(sampel=label, hipotesis=h + ("abcdef"[k] if len(eps) > 1 else ""), endpoint=ep,
                     expect=d["expect"], n_penari=len(a), n_nonpenari=len(b),
                     mean_penari=a.mean(), mean_nonpenari=b.mean(), statistik="Welch satu arah")
            if len(a) >= 3 and len(b) >= 3:
                t, p = stats.ttest_ind(a, b, equal_var=False, alternative=_alt(d["expect"]))
                sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
                J = 1 - 3 / (4 * (len(a) + len(b)) - 9)
                r.update(t=t, p_one_sided=p, effect=J * (a.mean() - b.mean()) / sp)   # Hedges g
            else:
                r.update(catatan="n < 3 per grup")
            rows.append(r)
    out = pd.DataFrame(rows)
    ok = out.p_one_sided.notna()
    if ok.any():
        out.loc[ok, "p_fdr"] = multipletests(out.loc[ok, "p_one_sided"], method="fdr_bh")[1]
    return out


def explore_map(res, parts, pids):
    """Peta eksploratif lengkap: penari vs non-penari (Welch dua arah, Hedges g) untuk setiap
    fase × area × ukuran specparam (gabungan 12 segmen) + durasi subfase; FDR atas seluruh peta."""
    am = pd.concat([pd.read_csv(res / f"{p}_area_map.csv") for p in pids])
    am = am[(am.pool == "SEMUA") & (am.level == "area")].merge(parts[["participant_id", "group"]])
    rows = []
    for (ph, ar), q in am.groupby(["phase", "unit"]):
        for col in ["offset_change", "exponent_change", "theta_periodic_db", "mu_periodic_db", "beta_periodic_db"]:
            a = q.loc[q.group == "penari", col].dropna()
            b = q.loc[q.group == "non-penari", col].dropna()
            if len(a) < 3 or len(b) < 3:
                continue
            t, p = stats.ttest_ind(a, b, equal_var=False)
            sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
            rows.append(dict(jenis="EEG", fase=ph, area=ar, ukuran=col, n_penari=len(a), n_nonpenari=len(b),
                             mean_penari=a.mean(), mean_nonpenari=b.mean(),
                             hedges_g=(1 - 3 / (4 * (len(a) + len(b)) - 9)) * (a.mean() - b.mean()) / sp, p=p,
                             artefak_rawan=ar in ("frontopolar", "frontotemporal", "temporal")))
    du = pd.concat([pd.read_csv(res / f"{p}_durasi.csv") for p in pids])
    du = VIDEO(du).merge(parts[["participant_id", "group"]])
    for col in ["dur_turun", "dur_tahan", "dur_naik", "latency_hud"]:
        agg = du.groupby(["participant_id", "group"])[col].agg(["median", lambda x: x.std(ddof=1) / x.mean()])
        agg.columns = ["median", "cv"]
        agg = agg.reset_index()
        for stat in ["median", "cv"]:
            a = agg.loc[agg.group == "penari", stat].dropna()
            b = agg.loc[agg.group == "non-penari", stat].dropna()
            t, p = stats.ttest_ind(a, b, equal_var=False)
            sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
            rows.append(dict(jenis="perilaku", fase=col, area="-", ukuran=stat, n_penari=len(a), n_nonpenari=len(b),
                             mean_penari=a.mean(), mean_nonpenari=b.mean(),
                             hedges_g=(1 - 3 / (4 * (len(a) + len(b)) - 9)) * (a.mean() - b.mean()) / sp, p=p,
                             artefak_rawan=False))
    out = pd.DataFrame(rows)
    out["p_fdr"] = multipletests(out.p, method="fdr_bh")[1]
    return out.sort_values("p")


def mixed_segments(res, parts, pids):
    """Model campuran tingkat segmen (semua segmen, C3/C4 dirata-rata per segmen):
    nilai ~ grup + gerakan, intersep acak partisipan; per fase × ukuran (dB rel. acuan gabungan)."""
    import statsmodels.formula.api as smf
    seg = pd.concat([pd.read_csv(res / f"{p}_segments.csv") for p in pids])
    seg = seg[seg.channel.isin(["C3", "C4"])]
    s = seg.groupby(["participant_id", "task", "rep", "phase"])[["broad_db", "mu_db", "beta_db"]].mean().reset_index()
    s = s.merge(parts[["participant_id", "group"]], on="participant_id")
    s["nonpenari"] = (s.group == "non-penari").astype(int)
    rows = []
    for ph in sorted(s.phase.unique()):
        for y in ("broad_db", "mu_db", "beta_db"):
            d = s[s.phase == ph].dropna(subset=[y])
            try:
                m = smf.mixedlm(f"{y} ~ nonpenari + C(task)", d, groups=d.participant_id).fit(reml=True)
                rows.append(dict(phase=ph, ukuran=y, n_seg=len(d), n_partisipan=d.participant_id.nunique(),
                                 beda_nonpenari_minus_penari_db=m.params["nonpenari"],
                                 se=m.bse["nonpenari"], p=m.pvalues["nonpenari"]))
            except Exception as e:                     # konvergensi gagal pada n kecil
                rows.append(dict(phase=ph, ukuran=y, n_seg=len(d), catatan=str(e)[:80]))
    out = pd.DataFrame(rows)
    ok = out.get("p", pd.Series(dtype=float)).notna()
    if ok.any():
        out.loc[ok, "p_fdr"] = multipletests(out.loc[ok, "p"], method="fdr_bh")[1]
    return out


def dose_response(df, cfg):
    """outcome ~ prediktor paparan tari + usia (OLS, SE HC3) + VIF, per sampel.
    Sampel 'semua': non-penari = 0 tahun/0 kali (hanya prediktor yang bermakna bila 0);
    sampel 'penari': dosis-respons di dalam penari saja (termasuk usia mulai menari)."""
    import statsmodels.formula.api as smf
    dc = cfg["dose_response"]
    cov = dc["covariates"]
    rows = []
    for pr in dc["predictors"]:
        for smp in pr.get("samples", ["semua", "penari"]):
            base = df if smp == "semua" else df[df.group == "penari"]
            need = [pr["name"]] + cov
            if any(c not in base for c in need):
                continue
            for y in dc["outcomes"]:
                d = base[[y] + need].dropna()
                if len(d) < dc["min_n"] or d[pr["name"]].nunique() < 3:
                    continue
                m = smf.ols(f"{y} ~ " + " + ".join(need), d).fit(cov_type="HC3")
                r_xy = d[need].corr().iloc[0, 1] if cov else 0.0
                sd_x, sd_y = d[pr["name"]].std(), d[y].std()
                rows.append(dict(prediktor=pr["name"], sampel=smp, outcome=y, n=len(d),
                                 slope=m.params[pr["name"]], se=m.bse[pr["name"]],
                                 beta_std=m.params[pr["name"]] * sd_x / sd_y if sd_y > 0 else np.nan,
                                 p=m.pvalues[pr["name"]],
                                 slope_usia=m.params.get("age", np.nan), p_usia=m.pvalues.get("age", np.nan),
                                 r_prediktor_usia=r_xy,
                                 vif=1 / (1 - r_xy ** 2) if abs(r_xy) < 1 else np.inf, r2=m.rsquared))
    out = pd.DataFrame(rows)
    if len(out):
        out["p_fdr"] = out.groupby(["prediktor", "sampel"]).p.transform(
            lambda p: multipletests(p, method="fdr_bh")[1])
        out["is_simulated"] = cfg["is_simulated"]
    return out


def run(cfg):
    root = cfg["_root"]
    res = root / cfg["paths"]["results"]
    pids = sorted(p.name.split("_area_map")[0] for p in res.glob("*_area_map.csv"))
    df = pd.DataFrame([endpoints(p, res) for p in pids])
    parts = pd.read_csv(root / cfg["paths"]["participants"])
    df = df.merge(parts, on="participant_id", how="left")
    df["set"] = np.where(df.participant_id.isin(cfg["exploration_set"]), "eksplorasi", "konfirmatori")
    df.to_csv(res / "hypothesis_v2_endpoints.csv", index=False)
    if cfg.get("analysis_mode", "eksploratif") == "eksploratif":
        t = test(df, cfg["hypotheses_v2"], f"semua (n={len(df)}; eksploratif)")
    else:
        t = pd.concat([test(df, cfg["hypotheses_v2"], "semua (termasuk sampel pembentuk hipotesis)"),
                       test(df[df.set == "konfirmatori"], cfg["hypotheses_v2"], "konfirmatori (partisipan baru)")])
    t.to_csv(res / "hypothesis_v2_tests.csv", index=False)
    explore_map(res, parts, pids).to_csv(res / "exploratory_map_v2.csv", index=False)
    mx = mixed_segments(res, parts, pids)
    mx.to_csv(res / "mixed_segments_v2.csv", index=False)
    dr = dose_response(df, cfg)
    dr.to_csv(res / "dose_response_v2.csv", index=False)
    return df, t, mx, dr
