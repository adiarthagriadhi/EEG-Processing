"""Tahap 1 data cleaning: INVENTARIS kualitas sinyal per kanal × segmen (tanpa mengubah data).

Sumber waktu: timeline/reps dari timestamp manual (data/derivatives/PXX/, dibuat `python -m eegpipe run PXX`).
Sinyal: EDF mentah (untuk datar/clipping) + bandpass 1–35 Hz (tanpa ICA, tanpa interpolasi).
Tiap segmen dipotong menjadi jendela 1 dtk; tiap jendela × kanal diberi label:
    datar      : ≥ 10% sampel datar (reset/putus kanal KT88, flat_mask pipeline)
    ekstrem    : peak-to-peak > 150 µV (batas tolak baku pipeline, romberg_reject_uv)
    tinggi     : 100–150 µV (ambang abu-abu; tercatat, tidak ditolak)
    ok
Indeks tambahan per segmen (dB relatif median jendela acuan BERDIRI RILEKS + ISTIRAHAT UTAMA kanal yang sama):
    delta_db  : power 1–4 Hz   (gerak kepala/kabel, keringat, mata)
    emg_db    : power 20–34 Hz (otot; perangkat LP ≈ 35 Hz)
Jalankan dari root repo: .venv/bin/python analisis_timestamp_manual/skrip/tahap1_kualitas.py P08 P09 P31 P32
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eegpipe import preprocess, segments                     # noqa: E402
from eegpipe.config import Participant, load_config          # noqa: E402
from eegpipe.eeg_io import load_edf                          # noqa: E402

OUT = ROOT / "analisis_timestamp_manual" / "tahap1_kualitas"
CH = segments.CH
PHASES = ["PRA", "TURUN", "TAHAN", "NAIK", "POST"]
REF = ["BERDIRI RILEKS", "ISTIRAHAT UTAMA"]
EXTREME, HIGH, FLAT = 150.0, 100.0, 0.10


def segment_list(tl, reps, cfg):
    """Jendela fase sama persis dengan tahap `segmen` (segments.phase_windows; timestamp manual:
    tiap fase dimulai manual_timestamps.pre_onset_sec sebelum onsetnya)."""
    S = []
    for _, m in reps.iterrows():
        for ph, w in segments.phase_windows(m, cfg).items():
            if w is not None:
                S.append(dict(kind="gerak", task=m.task, rep=m.rep, phase=ph, a=w[0], b=w[1]))
    for _, r in tl[tl.task.isin(REF + ["BERDIRI MATA TERTUTUP"])].iterrows():
        S.append(dict(kind="acuan" if r.task in REF else "romberg", task=r.task, rep=np.nan,
                      phase="ACUAN" if r.task in REF else "EC", a=r.start, b=r.end))
    return S


def band_power(x, sf, lo, hi):
    f, p = welch(x, sf, nperseg=min(x.shape[-1], int(sf)))
    return p[..., (f >= lo) & (f <= hi)].mean(-1)


def analyze(pid, cfg):
    P = Participant(pid, cfg)
    raw = load_edf(P.trial_edf, cfg)
    sf, T = raw.info["sfreq"], raw.times[-1]
    flat = segments.flat_mask(raw, cfg)
    X = preprocess.filter_raw(raw.copy(), cfg).get_data(picks=CH) * 1e6
    R = raw.get_data(picks=CH) * 1e6
    tl = pd.read_csv(P.out("timeline.csv"))
    reps = pd.read_csv(P.out("reps.csv"))
    win_rows, seg_rows = [], []
    for s in segment_list(tl, reps, cfg):
        a, b = max(s["a"], 0), min(s["b"], T)
        if b - a < 0.3:
            continue
        ia, ib = int(a * sf), int(b * sf)
        n1 = int(sf)
        edges = list(range(ia, ib - n1 + 1, n1)) or [ia]        # jendela 1 dtk (segmen pendek: 1 jendela)
        for e0 in edges:
            e1 = min(e0 + n1, ib)
            x, fl = X[:, e0:e1], flat[:, e0:e1].mean(1)
            ptp = np.ptp(x, axis=1)
            clip = (np.abs(R[:, e0:e1]) > 3000).any(1)
            lab = np.where(fl >= FLAT, "datar", np.where(ptp > EXTREME, "ekstrem",
                           np.where(ptp > HIGH, "tinggi", "ok")))
            for k, c in enumerate(CH):
                win_rows.append(dict(participant_id=pid, kind=s["kind"], task=s["task"], rep=s["rep"],
                                     phase=s["phase"], t0=round(e0 / sf, 2), channel=c, ptp_uv=round(ptp[k], 1),
                                     flat_frac=round(fl[k], 2), clipping=bool(clip[k]), label=lab[k]))
        x = X[:, ia:ib]
        seg_rows.append(dict(participant_id=pid, kind=s["kind"], task=s["task"], rep=s["rep"], phase=s["phase"],
                             a=round(a, 3), b=round(b, 3), dur=round(b - a, 3),
                             **{f"delta_{c}": v for c, v in zip(CH, band_power(x, sf, 1, 4))},
                             **{f"emg_{c}": v for c, v in zip(CH, band_power(x, sf, 20, 34))}))
    W, S = pd.DataFrame(win_rows), pd.DataFrame(seg_rows)
    # dB relatif acuan (median segmen acuan per kanal)
    ref = S[S.kind == "acuan"]
    for q in ("delta", "emg"):
        for c in CH:
            S[f"{q}_{c}"] = 10 * np.log10(S[f"{q}_{c}"] / ref[f"{q}_{c}"].median())
    return W, S


def summarize(W, S):
    W = W.assign(buruk=W.label.isin(["datar", "ekstrem"]))
    ph = (W.groupby(["participant_id", "phase"])
          .agg(n_jendela_kanal=("label", "size"), pct_datar=("label", lambda s: 100 * (s == "datar").mean()),
               pct_ekstrem=("label", lambda s: 100 * (s == "ekstrem").mean()),
               pct_tinggi=("label", lambda s: 100 * (s == "tinggi").mean()),
               pct_ok=("label", lambda s: 100 * (s == "ok").mean()),
               ptp_median_uv=("ptp_uv", "median"), clipping=("clipping", "sum")).reset_index())
    idx = []
    for (pid, p), g in S.groupby(["participant_id", "phase"]):
        idx.append(dict(participant_id=pid, phase=p,
                        delta_db_median=np.nanmedian(g[[f"delta_{c}" for c in CH]].values),
                        emg_db_median=np.nanmedian(g[[f"emg_{c}" for c in CH]].values)))
    ph = ph.merge(pd.DataFrame(idx), on=["participant_id", "phase"])
    order = {p: i for i, p in enumerate(PHASES + ["ACUAN", "EC"])}
    ph = ph.sort_values(["participant_id", "phase"], key=lambda s: s.map(order) if s.name == "phase" else s)
    ch = (W[W.kind == "gerak"].groupby(["participant_id", "channel"])
          .agg(pct_buruk=("buruk", lambda s: 100 * s.mean()),
               pct_datar=("label", lambda s: 100 * (s == "datar").mean()),
               pct_ekstrem=("label", lambda s: 100 * (s == "ekstrem").mean())).reset_index())
    return ph.round(1), ch.round(1)


def figure(W, pid):
    g = W[W.participant_id == pid]
    cols = PHASES + ["ACUAN", "EC"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, lab, title in [(axes[0], "datar", "% jendela 1 dtk DATAR (reset/putus kanal)"),
                           (axes[1], "ekstrem", "% jendela 1 dtk > 150 µV (tanpa datar)")]:
        M = (g.assign(v=g.label == lab).pivot_table(index="channel", columns="phase", values="v", aggfunc="mean")
             .reindex(index=CH, columns=[c for c in cols if c in set(g.phase)]) * 100)
        im = ax.imshow(M.values, vmin=0, vmax=100, cmap="Reds", aspect="auto")
        ax.set_xticks(range(M.shape[1]), M.columns, rotation=45, fontsize=8)
        ax.set_yticks(range(len(CH)), CH, fontsize=8)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M.values[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6,
                            color="white" if v > 60 else "black")
        ax.set_title(title, fontsize=9)
    fig.colorbar(im, ax=axes, shrink=0.8, label="%")
    fig.suptitle(f"{pid} — kualitas sinyal per kanal × fase (EEG 1–35 Hz, sebelum ICA)", fontsize=10)
    fig.savefig(OUT / f"{pid}_peta_kualitas.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def main(pids):
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    Ws, Ss = [], []
    for pid in pids:
        W, S = analyze(pid, cfg)
        figure(W, pid)
        Ws.append(W)
        Ss.append(S)
        print(f"[{pid}] {W.t0.nunique()} jendela 1 dtk × {len(CH)} kanal")
    W, S = pd.concat(Ws), pd.concat(Ss)
    W.to_csv(OUT / "jendela_1dtk_label.csv", index=False)
    S.round(2).to_csv(OUT / "segmen_indeks_delta_emg.csv", index=False)
    ph, ch = summarize(W, S)
    ph.to_csv(OUT / "ringkasan_per_fase.csv", index=False)
    ch.to_csv(OUT / "ringkasan_per_kanal.csv", index=False)
    pd.set_option("display.width", 200)
    print(ph.to_string(index=False))
    print(ch.pivot(index="channel", columns="participant_id", values="pct_buruk").reindex(CH).to_string())


if __name__ == "__main__":
    main(sys.argv[1:] or ["P08", "P09", "P31", "P32"])
