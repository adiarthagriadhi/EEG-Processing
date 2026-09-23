"""Uji cepat Romberg: cakupan + specparam EO vs EC per area (offset tetap 0,85 dtk; jendela 2 dtk,
tolak > 150 µV per area). Reaktivitas = tonjolan alpha periodik EC − EO (dB)."""
import mne, numpy as np, pandas as pd, warnings
from mne.time_frequency import psd_array_multitaper
from fooof import FOOOF
from scipy import stats
warnings.filterwarnings("ignore")
FIX = 0.85; GRID = np.arange(2, 30.01, 0.5)
AREA = {"oksipital": ["O1","O2"], "parietal": ["P3","P4"], "sentral": ["C3","C4"], "temporo-post": ["T5","T6"], "frontal": ["F3","F4"]}
LAB = {"EO": "BERDIRI FOKUS MATA TERBUKA", "EC": "BERDIRI MATA TERTUTUP"}
grp = pd.read_csv("data/participants.csv").set_index("participant_id").group
def fit(P):
    fm = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4, aperiodic_mode="fixed", verbose=False); fm.fit(GRID, P, [2, 30])
    flat = np.log10(P) - fm._ap_fit; m = lambda lo, hi: 10*flat[(GRID >= lo) & (GRID < hi)].mean()
    return dict(offset=10*fm.aperiodic_params_[0], expo=fm.aperiodic_params_[1], alpha=m(8, 13), theta=m(4, 8), beta=m(13, 30))
out = []
for pid in ["P01","P02","P03","P04","P05","P06","P07","P10","P36","P37","P38"]:
    D = f"data/derivatives/{pid}"
    raw = mne.io.read_raw_fif(f"{D}/clean_raw.fif", preload=True, verbose=False); T = raw.times[-1]
    tl = pd.read_csv(f"{D}/timeline.csv")
    for cond, lab in LAB.items():
        r = tl[tl.task == lab]
        if r.empty: continue
        a, b = r.start.iloc[0] + FIX + 1, min(r.end.iloc[-1] + FIX - 1, T)
        cov = max(0, b - a) / (r.end.iloc[-1] - r.start.iloc[0] - 2)
        for ar, chs in AREA.items():
            x = raw.get_data(picks=chs) * 1e6
            W = [x[:, int(s*100):int(s*100)+200] for s in np.arange(a, b - 2 + 1e-9, 1.0)]
            W = [w for w in W if np.ptp(w, axis=1).max() <= 150]
            row = dict(pid=pid, grup=grp[pid], kondisi=cond, area=ar, cakupan=round(cov, 2), n_win=len(W))
            if len(W) >= 2:
                p, f = psd_array_multitaper(np.array(W), 100, fmin=1.5, fmax=31, bandwidth=1.5, verbose=False)
                P = np.interp(GRID, f, p.mean((0, 1))); row.update(fit(P))
            out.append(row)
d = pd.DataFrame(out); d.to_csv("/tmp/claude-0/sp/romberg.csv", index=False)
print(d[d.area == "oksipital"].pivot_table(index="pid", columns="kondisi", values=["cakupan", "n_win", "alpha"]).round(2))
w = d.pivot_table(index=["pid", "grup", "area"], columns="kondisi", values=["alpha", "offset", "theta"]).reset_index()
w.columns = ["_".join(c).strip("_") for c in w.columns]
w["reakt_alpha"] = w.alpha_EC - w.alpha_EO
for ar in AREA:
    q = w[w.area == ar].dropna(subset=["reakt_alpha"])
    a, b = q[q.grup == "penari"], q[q.grup == "non-penari"]
    t1 = stats.ttest_1samp(q.reakt_alpha, 0)
    print(f"{ar:13s} n={len(q):2d} alpha EC−EO: semua {q.reakt_alpha.mean():+.2f} dB (p={t1.pvalue:.3f}) | penari {a.reakt_alpha.mean():+.2f} vs non {b.reakt_alpha.mean():+.2f} "
          f"(p={stats.ttest_ind(a.reakt_alpha, b.reakt_alpha, equal_var=False).pvalue:.2f}) | alpha EC periodik penari {a.alpha_EC.mean():+.2f} vs non {b.alpha_EC.mean():+.2f}")
