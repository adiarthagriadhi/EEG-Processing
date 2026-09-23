import mne, numpy as np, pandas as pd, yaml, warnings
from mne.time_frequency import psd_array_multitaper
warnings.filterwarnings("ignore")
FIX, TRIM = 0.85, 0.25
def mu_db(x, sf):
    p, f = psd_array_multitaper(x, sf, fmin=2, fmax=31, bandwidth=2.5, verbose=False)
    return 10*np.log10(p[..., (f >= 8) & (f < 13)].mean(-1)).mean(-1)   # rata C3/C4
rows = []
for pid in ["P02","P05","P07","P10","P36","P37","P38"]:
    ep = mne.read_epochs(f"data/derivatives/{pid}/move-epo.fif", verbose=False)
    off = yaml.safe_load(open(f"data/decisions/{pid}.yaml"))["sync"]["offset_sec"]
    X, t, sf = ep.get_data(picks=["C3","C4"]), ep.times, ep.info["sfreq"]
    md = ep.metadata.reset_index(drop=True)
    old, new = [], []
    for i, m in md.iterrows():
        def val(a, b):
            if b - a < 0.4 or a < t[0] or b > t[-1]: return np.nan
            s = mu_db(X[i][:, (t >= a) & (t < b)], sf); d = mu_db(X[i][:, (t >= -6) & (t < -4)], sf)
            return s - d
        old.append((m.task, val(m.rel_tahan, m.rel_naik) if m.compliance != "short_hold" else np.nan))
        d = FIX - off   # geser jendela ke offset tetap
        tr = min(TRIM, 0.15*(m.rel_naik - m.rel_tahan)); new.append((m.task, val(m.rel_tahan + d + tr, m.rel_naik + d - tr)))
    o = pd.DataFrame(old, columns=["task","v"]).dropna(); n = pd.DataFrame(new, columns=["task","v"]).dropna()
    se_old = o.groupby("task").v.agg(lambda v: v.std(ddof=1)/np.sqrt(len(v)) if len(v) > 1 else np.nan).median()
    se_new = n.v.std(ddof=1)/np.sqrt(len(n))
    rows.append(dict(pid=pid, offset=off, n_old_per_gerak=round(o.groupby("task").size().median(),1),
                     n_new=len(n), SE_old_dB=round(se_old,2), SE_new_dB=round(se_new,2),
                     perbaikan_pct=(round(100*(1-se_new/se_old)) if np.isfinite(se_old) else None), mean_old=round(o.v.mean(),2), mean_new=round(n.v.mean(),2)))
print(pd.DataFrame(rows).to_string(index=False))
