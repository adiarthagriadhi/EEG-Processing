"""Uji cepat: latensi puncak ERD mu RELATIF (mu / broadband 2–30 Hz) per kanal, dikunci onset TURUN
(video + offset tetap 0,85 dtk), acuan gabungan per partisipan. Bootstrap antar-segmen → presisi."""
import sys, mne, numpy as np, pandas as pd, warnings
from scipy.ndimage import uniform_filter1d
warnings.filterwarnings("ignore")
FIX = 0.85
CH = ["F3","F4","C3","C4","P3","P4","T5","T6","O1","O2"]
grp = pd.read_csv("data/participants.csv").set_index("participant_id").group
rng = np.random.default_rng(0)
out = []
for pid in sys.argv[1:]:
    D = f"data/derivatives/{pid}"
    raw = mne.io.read_raw_fif(f"{D}/clean_raw.fif", preload=True, verbose=False).pick(CH)
    sf = raw.info["sfreq"]
    env = lambda lo, hi: raw.copy().filter(lo, hi, verbose=False).apply_hilbert(envelope=True).get_data() ** 2
    rel = 10 * np.log10(uniform_filter1d(env(8, 13), int(0.3*sf), axis=1) / uniform_filter1d(env(2, 30), int(0.3*sf), axis=1))
    reps, tl = pd.read_csv(f"{D}/reps.csv"), pd.read_csv(f"{D}/timeline.csv")
    q = tl[tl.task.isin(["BERDIRI RILEKS", "ISTIRAHAT UTAMA"])]
    idx = np.concatenate([np.arange(int((r.start+0.5+FIX)*sf), int((r.end-0.5+FIX)*sf)) for _, r in q.iterrows()])
    idx = idx[(idx >= 0) & (idx < rel.shape[1])]
    rel = rel - np.median(rel[:, idx], axis=1, keepdims=True)          # dB relatif acuan gabungan
    tt = np.arange(-2, 6, 1/sf); E = []
    for _, m in reps.iterrows():
        if not np.isfinite([m.act_turun, m.act_naik]).all(): continue
        c = int((m.act_turun + FIX) * sf)
        if c - 2*sf < 0 or c + 6*sf > rel.shape[1]: continue
        E.append(rel[:, c - int(2*sf): c + int(6*sf)][:, :len(tt)])
    E = np.array(E); n = len(E)
    win = (tt >= -1) & (tt <= 4)                                          # PRA akhir → TAHAN
    def lat(A): return tt[win][np.argmin(A.mean(0)[:, win], axis=1)]
    L = lat(E); B = np.array([lat(E[rng.integers(0, n, n)]) for _ in range(200)])
    depth = E.mean(0)[:, win].min(1)
    for k, ch in enumerate(CH):
        out.append(dict(pid=pid, grup=grp[pid], ch=ch, n=n, lat=L[k], lat_sd=B[:, k].std(), depth_dB=depth[k]))
d = pd.DataFrame(out); d.to_csv("/tmp/claude-0/sp/latensi.csv", index=False)
print("Presisi latensi per partisipan (SD bootstrap, dtk): median %.2f" % d.lat_sd.median())
print(d.pivot_table(index="ch", columns="grup", values=["lat", "lat_sd", "depth_dB"], aggfunc="median").round(2).reindex(CH))
# konsistensi urutan: korelasi Spearman urutan latensi antar-partisipan
P = d.pivot(index="pid", columns="ch", values="lat")[CH]
from scipy.stats import spearmanr
r = [spearmanr(P.iloc[i], P.iloc[j])[0] for i in range(len(P)) for j in range(i+1, len(P))]
print("Kesepakatan urutan kanal antar-partisipan (median rho Spearman): %.2f" % np.nanmedian(r))
