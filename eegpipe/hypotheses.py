"""Endpoint & uji hipotesis H1–H5 (definisi di config.yaml → hypotheses)."""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

CONTRA = {"AGEM KANAN": "C3", "AGEM KIRI": "C4"}


def endpoints(pid, results_dir, deriv_dir):
    s = pd.read_csv(results_dir / f"{pid}_spectral.csv")
    a = s[s.task.isin(CONTRA)]
    c = a[a.apply(lambda r: r.channel == CONTRA[r.task], axis=1)]
    mu = lambda ph, chs: a[(a.phase == ph) & a.channel.isin(chs)].groupby("task").mu_relative_db.mean().mean()
    reps = pd.read_csv(deriv_dir / pid / "reps.csv")
    ag = reps[reps.task.isin(CONTRA)]
    return dict(participant_id=pid,
                mu_periodic_contra_abs_TAHAN=c[c.phase == "TAHAN"].mu_periodic_db.abs().mean(),
                global_offset_TAHAN=a[a.phase == "TAHAN"].groupby(["task", "hemisphere"]).global_offset_db.first().mean(),
                hold_agem_sec=(ag.act_naik - ag.act_tahan).median(),
                mu_relative_FCP_left_TURUN=mu("TURUN", ["F3", "C3", "P3"]),
                mu_relative_right_minus_left_TAHAN=mu("TAHAN", ["C4", "F4"]) - mu("TAHAN", ["C3", "F3"]),
                noise_floor_db=s.noise_floor_db.iloc[0])


def test(df, hyp):
    rows = []
    for h, d in hyp.items():
        a = df.loc[df.group == "penari", d["endpoint"]].dropna()
        b = df.loc[df.group == "non-penari", d["endpoint"]].dropna()
        r = dict(hipotesis=h, label=d["label"], endpoint=d["endpoint"], expect=d["expect"],
                 n_penari=len(a), n_nonpenari=len(b), mean_penari=a.mean(), mean_nonpenari=b.mean())
        if len(a) >= 3 and len(b) >= 3:
            alt = "less" if d["expect"].startswith("penari <") else "greater"
            if d["expect"].startswith("non-penari <"):
                alt = "greater"                       # penari > non-penari
            t, p = stats.ttest_ind(a, b, equal_var=False, alternative=alt)
            r.update(t=t, p_one_sided=p)
        else:
            r.update(t=np.nan, p_one_sided=np.nan, catatan="n < 3 per grup: belum dapat diuji")
        rows.append(r)
    out = pd.DataFrame(rows)
    ok = out.p_one_sided.notna()
    if ok.any():
        out.loc[ok, "p_fdr"] = multipletests(out.loc[ok, "p_one_sided"], method="fdr_bh")[1]
    return out
