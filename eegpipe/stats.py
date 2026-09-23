"""Statistik grup (Tahap 6): Paper A, D, B. Satu fungsi per naskah; mengembalikan tabel."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests


def welch(d, col, g1="penari", g2="non-penari"):
    a = d.loc[d.group == g1, col].dropna()
    b = d.loc[d.group == g2, col].dropna()
    if len(a) < 2 or len(b) < 2:
        return dict(indeks=col, n_penari=len(a), n_nonpenari=len(b))
    t, p = stats.ttest_ind(a, b, equal_var=False)
    sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    J = 1 - 3 / (4 * (len(a) + len(b)) - 9)
    return dict(indeks=col, n_penari=len(a), n_nonpenari=len(b), mean_penari=a.mean(),
                sd_penari=a.std(), mean_nonpenari=b.mean(), sd_nonpenari=b.std(), t=t, p=p,
                hedges_g=J * (a.mean() - b.mean()) / sp)


def partial_spearman(d, x, y, covars):
    """Korelasi parsial Spearman: rank, residualisasi terhadap kovariat, Pearson."""
    z = d[[x, y] + covars].dropna()
    z = pd.get_dummies(z, drop_first=True, dtype=float).rank()
    X = np.column_stack([np.ones(len(z))] + [z[c] for c in z.columns if c not in (x, y)])
    rx = z[x] - X @ np.linalg.lstsq(X, z[x], rcond=None)[0]
    ry = z[y] - X @ np.linalg.lstsq(X, z[y], rcond=None)[0]
    r, _ = stats.pearsonr(rx, ry)
    k = X.shape[1] - 1
    df = len(z) - 2 - k
    t = r * np.sqrt(df / (1 - r ** 2))
    return dict(fitur=x, n=len(z), r=r, p=2 * stats.t.sf(abs(t), df))


def fdr(df, col="p"):
    df = df.copy()
    ok = df[col].notna()
    df.loc[ok, "p_fdr"] = multipletests(df.loc[ok, col], method="fdr_bh")[1]
    return df


def age_sensitivity(d, y):
    rows = []
    q = d.age.quantile([0.05, 0.95])
    full = smf.ols(f"{y} ~ C(group) * age", d).fit(cov_type="HC3")
    cook = full.get_influence().cooks_distance[0]
    for name, sub in [("semua", d), ("tanpa pengaruh besar (Cook)", d[cook < 4 / len(d)]),
                      ("usia persentil 5–95", d[d.age.between(*q)])]:
        m = smf.ols(f"{y} ~ C(group) * age", sub).fit(cov_type="HC3")
        k = [c for c in m.params.index if ":age" in c][0]
        rows.append(dict(model=name, n=int(m.nobs), interaksi_grup_x_usia=m.params[k],
                         p=m.pvalues[k]))
    return pd.DataFrame(rows)


PHASES = ["PRA", "TURUN", "TAHAN", "NAIK"]


def paper_a(pre):
    """Semua fase × indeks; BH atas seluruh keluarga uji Paper A."""
    idx = [f"{m}_{ph}" for ph in PHASES for m in ("erd_beta", "erd_mu", "theta_front", "li_mu")]
    tab = fdr(pd.DataFrame([welch(pre, c) for c in idx if c in pre]))
    sens = age_sensitivity(pre.dropna(subset=["erd_beta_TAHAN", "age"]), "erd_beta_TAHAN")
    return tab, sens


def paper_d(pre):
    tier1 = ["alpha_occ_EC", "alpha_reactivity_EC_EO", "mu_sm_EC", "mu_sm_EO", "theta_front_EC"]
    grp = fdr(pd.DataFrame([welch(pre, c) for c in tier1 + ["stork_time_sec"]]))
    cor = fdr(pd.DataFrame([partial_spearman(pre, c, "stork_time_sec", ["age"]) for c in tier1]))
    cor_g = fdr(pd.DataFrame([partial_spearman(pre, c, "stork_time_sec", ["age", "group"])
                              for c in tier1]))
    return grp, cor, cor_g


def paper_b(d, benchmark_model=None, min_gap_sd=0.25):
    y = "erd_beta_TAHAN"
    non = d[d.group == "non-penari"].pivot_table(index="participant_id", columns="timepoint",
                                                 values=[y, "iaf_occ_EC", "age"])
    pre, post = non[(y, "pre")], non[(y, "post")]
    # reliabilitas split-half (Spearman-Brown) dari seluruh sampel pre
    base = d[d.timepoint == "pre"]
    r = base[f"{y}_odd"].corr(base[f"{y}_even"])
    rxx = 2 * r / (1 + r)
    s_diff = pre.std() * np.sqrt(2 * (1 - rxx))
    rci = (post - pre) / s_diff
    dancers = base[base.group == "penari"]
    m = smf.ols(f"{y} ~ age", dancers).fit()
    bench = m.predict(pd.DataFrame({"age": non[("age", "pre")]}))   # benchmark sesuai usia
    gap = bench.values - pre.values
    gc = np.where(np.abs(gap) < min_gap_sd * dancers[y].std(), np.nan,
                  (post.values - pre.values) / gap * 100)
    ind = pd.DataFrame(dict(participant_id=non.index, age=non[("age", "pre")].values,
                            pre=pre.values, post=post.values, rci=rci.values,
                            berubah_nyata=np.abs(rci.values) >= 1.96,
                            benchmark_penari_usia=bench.values, gap_closure_pct=gc))
    t_t, p_t = stats.ttest_rel(post, pre)
    ndv = non[("iaf_occ_EC", "post")] - non[("iaf_occ_EC", "pre")]
    t_n, p_n = stats.ttest_rel(non[("iaf_occ_EC", "post")], non[("iaf_occ_EC", "pre")])
    summary = pd.DataFrame([
        dict(uji="Target: ERD beta AGEM kontra, TAHAN, pre→post (paired t)", n=len(pre),
             beda_rata=float((post - pre).mean()), t=t_t, p=p_t),
        dict(uji="NDV: IAF oksipital pre→post (paired t)", n=int(ndv.notna().sum()),
             beda_rata=float(ndv.mean()), t=t_n, p=p_n)])
    return summary, ind, dict(rxx=rxx, s_diff=s_diff)
