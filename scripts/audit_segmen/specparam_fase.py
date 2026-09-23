"""Uji cepat: garis latar & mu periodik (specparam) per fase TURUN/TAHAN/NAIK, semua segmen,
offset tetap 0,85 dtk, acuan gabungan per partisipan (jendela paling diam dari video)."""
import sys, mne, numpy as np, pandas as pd, warnings
sys.path.insert(0, '.')
from eegpipe import sync
from mne.time_frequency import psd_array_multitaper
from fooof import FOOOF
from scipy import stats
warnings.filterwarnings("ignore")
FIX, TRIM, CH = 0.85, 0.25, ["C3", "C4"]
GRID = np.arange(2, 30.01, 0.5)
grp = pd.read_csv("data/participants.csv").set_index("participant_id").group
PH = {"TURUN": ("act_turun", "act_tahan"), "TAHAN": ("act_tahan", "act_naik"), "NAIK": ("act_naik", "act_end")}
def spec(x, sf):
    p, f = psd_array_multitaper(x, sf, fmin=1.5, fmax=31, bandwidth=2.5, verbose=False)
    return np.array([np.interp(GRID, f, pp) for pp in p]).mean(0)
def fit(P):
    fm = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4, aperiodic_mode="fixed", verbose=False); fm.fit(GRID, P, [2, 30])
    flat = np.log10(P) - fm._ap_fit
    return fm.aperiodic_params_[0], flat[(GRID >= 8) & (GRID < 13)].mean(), flat[(GRID >= 13) & (GRID < 30)].mean()
out = []
for pid in sys.argv[1:]:
    D = f"data/derivatives/{pid}"
    raw = mne.io.read_raw_fif(f"{D}/clean_raw.fif", preload=True, verbose=False).pick(CH)
    x, sf, T = raw.get_data(), raw.info["sfreq"], raw.times[-1]
    reps, tl = pd.read_csv(f"{D}/reps.csv"), pd.read_csv(f"{D}/timeline.csv")
    pose = dict(np.load(f"{D}/pose.npz")); pt = pose["t"]
    s1, s2 = sync.pose_speed(pose)[1], sync.wrist_speed(pose); body = s1/np.nanmedian(s1) + s2/np.nanmedian(s2)
    W = []
    for _, r in tl[tl.task.isin(["BERDIRI RILEKS", "ISTIRAHAT UTAMA"])].iterrows():
        for a in np.arange(r.start + 0.5, r.end - 2.5, 1.0):
            if 0 <= a + FIX and a + 2 + FIX <= T:
                W.append((np.nanmedian(body[(pt >= a) & (pt < a + 2)]), spec(x[:, int((a+FIX)*sf):int((a+2+FIX)*sf)], sf)))
    thr = np.median([w[0] for w in W]); b0 = fit(np.mean([w[1] for w in W if w[0] <= thr], 0))
    for ph, (c0, c1) in PH.items():
        S = []
        for _, m in reps.iterrows():
            a, b = m[c0], m[c1]
            if not np.isfinite([a, b]).all(): continue
            tr = min(TRIM, 0.15*(b - a)); a, b = a + tr + FIX, b - tr + FIX
            if b - a >= 0.4 and a >= 0 and b <= T: S.append(spec(x[:, int(a*sf):int(b*sf)], sf))
        if not S: continue
        f1 = fit(np.mean(S, 0))
        out.append(dict(pid=pid, grup=grp[pid], fase=ph, n=len(S), garis_latar_dB=10*(f1[0]-b0[0]),
                        mu_periodik_dB=10*(f1[1]-b0[1]), beta_periodik_dB=10*(f1[2]-b0[2])))
d = pd.DataFrame(out); d.to_csv("/tmp/claude-0/sp/fase.csv", index=False)
print(d.groupby(["fase", "grup"])[["n", "garis_latar_dB", "mu_periodik_dB", "beta_periodik_dB"]].mean().round(2))
for ph in PH:
    for c in ["garis_latar_dB", "mu_periodik_dB", "beta_periodik_dB"]:
        q = d[d.fase == ph]; a, b = q[q.grup == "penari"][c], q[q.grup == "non-penari"][c]
        t_, p = stats.ttest_ind(a, b, equal_var=False)
        print(f"{ph:6s} {c:17s} d={(a.mean()-b.mean())/np.sqrt((a.var()+b.var())/2):+.2f} p={p:.3f}")
