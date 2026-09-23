import sys, mne, numpy as np, pandas as pd, yaml, warnings
sys.path.insert(0, '.')
from eegpipe import sync
from mne.time_frequency import psd_array_multitaper
warnings.filterwarnings("ignore")
FIX, TRIM, CH = 0.85, 0.25, ["C3", "C4"]
grp = pd.read_csv("data/participants.csv").set_index("participant_id").group
def mu_db(x, sf):
    p, f = psd_array_multitaper(x, sf, fmin=2, fmax=31, bandwidth=2.5, verbose=False)
    return 10*np.log10(p[..., (f >= 8) & (f < 13)].mean(-1)).mean(-1)
rows = []
for pid in ["P01","P02","P03","P04","P05","P06","P07","P10","P36","P37","P38"]:
    D = f"data/derivatives/{pid}"
    raw = mne.io.read_raw_fif(f"{D}/clean_raw.fif", preload=True, verbose=False).pick(CH)
    x, sf, T = raw.get_data(), raw.info["sfreq"], raw.times[-1]
    reps, tl = pd.read_csv(f"{D}/reps.csv"), pd.read_csv(f"{D}/timeline.csv")
    pose = dict(np.load(f"{D}/pose.npz")); pt = pose["t"]
    body = sync.pose_speed(pose)[1] / np.nanmedian(sync.pose_speed(pose)[1]) + \
           sync.wrist_speed(pose) / np.nanmedian(sync.wrist_speed(pose))
    seg = lambda a, b: x[:, int(a*sf):int(b*sf)]
    # acuan gabungan: jendela 2 dtk paling diam (50% terendah) di BERDIRI RILEKS + ISTIRAHAT UTAMA
    W = []
    for _, r in tl[tl.task.isin(["BERDIRI RILEKS", "ISTIRAHAT UTAMA"])].iterrows():
        for a in np.arange(r.start + 0.5, r.end - 2.5, 1.0):
            if a + FIX < 0 or a + 2 + FIX > T: continue
            W.append((np.nanmedian(body[(pt >= a) & (pt < a + 2)]), mu_db(seg(a + FIX, a + 2 + FIX), sf)))
    W = np.array(W); base = np.median(W[W[:, 0] <= np.median(W[:, 0]), 1])
    new = []
    for _, m in reps.iterrows():
        a, b = m.act_tahan, m.act_naik
        if not np.isfinite([a, b]).all(): continue
        tr = min(TRIM, 0.15*(b - a)); a, b = a + tr + FIX, b - tr + FIX
        if b - a < 0.4 or a < 0 or b > T: continue
        new.append(mu_db(seg(a, b), sf) - base)
    # lama (dari epoch yang lolos filter, acuan per repetisi)
    ep = mne.read_epochs(f"{D}/move-epo.fif", verbose=False); X, t = ep.get_data(picks=CH), ep.times
    old = [mu_db(X[i][:, (t >= m.rel_tahan) & (t < m.rel_naik)], sf) - mu_db(X[i][:, (t >= -6) & (t < -4)], sf)
           for i, m in ep.metadata.reset_index(drop=True).iterrows()
           if m.compliance != "short_hold" and m.rel_naik - m.rel_tahan >= 0.5]
    new, old = np.array(new), np.array(old)
    rows.append(dict(pid=pid, grup=grp[pid], n_lama=len(old), n_baru=len(new),
                     ERD_lama_dB=round(old.mean(), 2), ERD_baru_dB=round(new.mean(), 2),
                     SE_lama=round(old.std(ddof=1)/np.sqrt(len(old)), 2) if len(old) > 1 else np.nan,
                     SE_baru=round(new.std(ddof=1)/np.sqrt(len(new)), 2)))
d = pd.DataFrame(rows); print(d.to_string(index=False)); d.to_csv("/tmp/claude-0/sp/newerd.csv", index=False)
g = d.groupby("grup")[["n_lama","n_baru","ERD_lama_dB","ERD_baru_dB"]].agg(["mean","std"]).round(2); print(g)
from scipy import stats
for c in ["ERD_lama_dB", "ERD_baru_dB"]:
    a, b = d[d.grup=="penari"][c], d[d.grup=="non-penari"][c]
    t_, p = stats.ttest_ind(a, b, equal_var=False); sp = np.sqrt((a.var()+b.var())/2)
    print(c, "Welch t=%.2f p=%.3f  d=%.2f" % (t_, p, (a.mean()-b.mean())/sp))
