"""Uji cepat konektivitas berarah dalam satu belahan: PSI (Nolte 2008; + = kanal pertama memimpin)
dan wPLI, pita mu/beta, per subsegmen TURUN/TAHAN (video + offset tetap 0,85 dtk), 11 partisipan."""
import mne, numpy as np, pandas as pd, warnings
from scipy import stats
warnings.filterwarnings("ignore")
FIX, NF = 0.85, 128
PAIRS = [("F3","C3"), ("C3","P3"), ("F4","C4"), ("C4","P4")]
BANDS = {"mu": (8, 13), "beta": (13, 30)}
PH = {"TURUN": ("act_turun", "act_tahan"), "TAHAN": ("act_tahan", "act_naik")}
grp = pd.read_csv("data/participants.csv").set_index("participant_id").group
f = np.fft.rfftfreq(NF, 0.01); out = []
for pid in ["P01","P02","P03","P04","P05","P06","P07","P10","P36","P37","P38"]:
    D = f"data/derivatives/{pid}"
    raw = mne.io.read_raw_fif(f"{D}/clean_raw.fif", preload=True, verbose=False)
    X = {c: raw.get_data(picks=[c])[0] for c in ["F3","C3","P3","F4","C4","P4"]}
    reps = pd.read_csv(f"{D}/reps.csv")
    for ph, (c0, c1) in PH.items():
        F = {c: [] for c in X}
        for _, m in reps.iterrows():
            a, b = m[c0], m[c1]
            if not np.isfinite([a, b]).all() or b - a < 0.5: continue
            i0, i1 = int((a + FIX) * 100), int((b + FIX) * 100)
            for s in range(i0, i1 - 50 + 1, 25):                         # jendela 0,5 dtk, geser 0,25
                for c in X:
                    w = X[c][s:s+50]; F[c].append(np.fft.rfft((w - w.mean()) * np.hanning(50), NF))
        F = {c: np.array(v) for c, v in F.items()}
        for i, j in PAIRS:
            S = F[i] * np.conj(F[j]); C = S.mean(0) / np.sqrt((abs(F[i])**2).mean(0) * (abs(F[j])**2).mean(0))
            for bn, (lo, hi) in BANDS.items():
                k = np.where((f >= lo) & (f <= hi))[0]
                psi = np.imag(np.sum(np.conj(C[k[:-1]]) * C[k[1:]]))
                im = np.imag(S[:, k]); wpli = abs(im.mean(0)).sum() / abs(im).mean(0).sum()
                out.append(dict(pid=pid, grup=grp[pid], fase=ph, pasangan=f"{i}→{j}", pita=bn, psi=psi, wpli=wpli, n_win=len(S)))
d = pd.DataFrame(out); d.to_csv("/tmp/claude-0/sp/konek.csv", index=False)
res = []
for (ph, pr, bn), q in d.groupby(["fase", "pasangan", "pita"]):
    a, b = q[q.grup == "penari"], q[q.grup == "non-penari"]
    res.append(dict(fase=ph, alur=pr, pita=bn, psi_penari=a.psi.mean(), psi_non=b.psi.mean(),
                    p_arah_semua=stats.ttest_1samp(q.psi, 0)[1], wpli_penari=a.wpli.mean(), wpli_non=b.wpli.mean(),
                    p_beda_psi=stats.ttest_ind(a.psi, b.psi, equal_var=False)[1], p_beda_wpli=stats.ttest_ind(a.wpli, b.wpli, equal_var=False)[1]))
r = pd.DataFrame(res)
from statsmodels.stats.multitest import multipletests
for c in ["p_arah_semua", "p_beda_psi", "p_beda_wpli"]: r[c + "_fdr"] = multipletests(r[c], method="fdr_bh")[1]
pd.set_option("display.width", 250); print(r.round(3).to_string(index=False)); print("median jendela/fase:", d.n_win.median())
