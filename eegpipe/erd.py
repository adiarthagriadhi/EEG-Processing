"""Tahap 4.2 + 5: epoching pada onset TURUN aktual, %ERD/ERS per fase, LI."""
import mne
import numpy as np
import pandas as pd

from .sync import to_eeg


def make_epochs(raw, reps, offset, cfg):
    ok = reps.compliance.isin(["ok", "late", "short_hold", "hud_fallback"])
    if "baseline_still" in reps:
        ok &= reps.baseline_still.astype(bool)
    ph = reps[ok].reset_index(drop=True)
    if ph.empty:
        return None
    sf = raw.info["sfreq"]
    t0 = ph.act_arm if "act_arm" in ph else ph.act_turun          # gerak PERTAMA
    samp = np.round(to_eeg(t0, offset) * sf).astype(int)
    events = np.column_stack([samp, np.zeros(len(ph), int), np.arange(1, len(ph) + 1)])
    event_id = {f"{r.task.replace(' ', '_')}/rep{r.rep}": i + 1 for i, r in ph.iterrows()}
    meta = ph[["task", "rep", "compliance"]].copy()
    meta["phase_source"] = ph.get("phase_source", "video")
    for c in ["act_turun", "act_tahan", "act_naik", "act_end"]:
        meta[c.replace("act_", "rel_")] = ph[c] - t0
    meta["latency_hud"] = ph.act_turun - ph.hud_turun
    ec = cfg["erd"]
    return mne.Epochs(raw, events, event_id, tmin=ec["tmin"],
                      tmax=float(meta.rel_end.max()) + ec["post_window"][1] + 1.0, baseline=None, metadata=meta,
                      reject_by_annotation=True, preload=True, verbose="error")


def erd_table(epochs, pid, cfg):
    ec = cfg["erd"]
    roi = [c for c in ec["roi"] if c in epochs.ch_names]
    freqs = np.arange(ec["freqs"][0], ec["freqs"][1] + 1, 1.0)
    tfr = epochs.compute_tfr(method="morlet", freqs=freqs, n_cycles=freqs / 2, picks=roi,
                             average=False, return_itc=False, verbose="error")
    tfr.apply_baseline(baseline=tuple(ec["baseline"]), mode="percent", verbose="error")
    data = tfr.get_data() * 100
    sig = epochs.get_data(picks=roi) * 1e6            # µV, untuk bendera artefak per fase
    rows = []
    for i, m in epochs.metadata.reset_index(drop=True).iterrows():
        windows = {"PRA": tuple(ec["pre_window"]), "TURUN": (m.rel_turun, m.rel_tahan),
                   "TAHAN": (m.rel_tahan, m.rel_naik), "NAIK": (m.rel_naik, m.rel_end),
                   "POST": (m.rel_end + ec["post_window"][0], m.rel_end + ec["post_window"][1])}
        if m.compliance == "short_hold":
            windows.pop("TAHAN")
        for phase, (t0, t1) in windows.items():
            if not np.isfinite([t0, t1]).all() or t1 - t0 < ec["min_phase_sec"]:
                continue
            tm = (tfr.times >= t0) & (tfr.times < t1)
            # P02: TURUN/NAIK memberi "ERS" +26…+93% (median), TAHAN memberi ERD −44…−52%.
            # Apakah ERS fase dinamis = artefak gerak belum terjawab: ptp tidak membedakan
            # (baseline berdiri sama "besar"), jadi hanya dicatat sebagai informasi.
            ptp = np.ptp(sig[i][:, (epochs.times >= t0) & (epochs.times < t1)], axis=1)
            bw = (epochs.times >= ec["baseline"][0]) & (epochs.times < ec["baseline"][1])
            ptp_ratio = ptp / np.maximum(np.ptp(sig[i][:, bw], axis=1), 1e-6)
            for band, (lo, hi) in ec["bands"].items():
                if band == "theta" and t1 - t0 < 1.0:     # wavelet 4 Hz ≈ 0,5 dtk
                    continue
                fm = (freqs >= lo) & (freqs < hi)
                vals = data[i][:, fm][:, :, tm].mean(axis=(1, 2))
                for ch, v, pp, pr in zip(roi, vals, ptp, ptp_ratio):
                    rows.append(dict(participant_id=pid, task=m.task, rep=m.rep, phase=phase,
                                     compliance=m.compliance, latency_hud=m.latency_hud,
                                     phase_source=m.phase_source,
                                     band=band, channel=ch, erd_pct=v, phase_dur=t1 - t0,
                                     phase_ptp_uv=round(float(pp), 1),
                                     ptp_ratio_vs_baseline=round(float(pr), 2),
                                     is_simulated=cfg["is_simulated"]))
    return pd.DataFrame(rows), tfr


def lateralization(erd):
    """LI versi draft Paper A, hanya bila kedua sisi ERD (< 0); lihat 10.1."""
    agem = erd[erd.task.isin(["AGEM KANAN", "AGEM KIRI"]) & erd.channel.isin(["C3", "C4"])]
    if agem.empty:
        return pd.DataFrame()
    w = agem.pivot_table(index=["participant_id", "task", "rep", "phase", "band"],
                         columns="channel", values="erd_pct").reset_index()
    kanan = w.task == "AGEM KANAN"
    w["contra"] = np.where(kanan, w.C3, w.C4)      # asumsi pemetaan sisi (Pertanyaan 8)
    w["ipsi"] = np.where(kanan, w.C4, w.C3)
    both = (w.contra < 0) & (w.ipsi < 0)
    w["li_erd"] = np.where(both, (w.contra - w.ipsi) / (w.contra + w.ipsi), np.nan)
    return w


def task_tfr(epochs, cfg):
    """TFR %ERD/ERS rata-rata per gerakan untuk SEMUA kanal EEG (peta & topografi)."""
    ec = cfg["erd"]
    freqs = np.arange(ec["freqs"][0], ec["freqs"][1] + 1, 1.0)
    out = {}
    for task in epochs.metadata.task.unique():
        ep = epochs[(epochs.metadata.task == task).to_numpy()]
        tfr = ep.compute_tfr(method="morlet", freqs=freqs, n_cycles=freqs / 2, picks="eeg",
                             average=True, return_itc=False, verbose="error")
        tfr.apply_baseline(baseline=tuple(ec["baseline"]), mode="percent", verbose="error")
        md = ep.metadata
        out[task] = dict(data=tfr.data * 100, phases=[0.0, float(md.rel_tahan.median()),
                                                      float(md.rel_naik.median()),
                                                      float(md.rel_end.median())], n=len(ep))
    return out, tfr.times, freqs, tfr.ch_names
