"""Orkestrasi per partisipan. Tiap tahap menyimpan hasilnya di data/derivatives/PXX/;
dijalankan ulang hanya jika hasil belum ada atau --force. Keputusan otomatis/manual
dicatat di data/decisions/PXX.yaml. Pipeline berhenti hanya bila QC gagal."""
import json

import mne
import numpy as np
import pandas as pd

from . import erd, ocr, phases, preprocess, romberg, sync
from .config import Participant
from .eeg_io import load_edf

STAGES = ["ocr", "pose", "sync", "phases", "preprocess", "erd", "romberg", "report"]


class QCStop(Exception):
    """QC gagal: perlu keputusan manual di data/decisions/PXX.yaml."""


def _log(pid, msg):
    print(f"[{pid}] {msg}", flush=True)


def stage_ocr(P, cfg, force=False):
    out = P.out("timeline.csv")
    if out.exists() and not force:
        return pd.read_csv(out)
    samples = ocr.run_ocr(P.video, cfg["video"]["hud_box"], cfg["video"]["ocr_coarse_step_sec"])
    samples.to_csv(P.out("ocr_samples.csv"), index=False)
    tl = ocr.segments(samples)
    tl.to_csv(out, index=False)
    n_rep = tl[tl.subphase.notna()].groupby("task").rep.nunique().to_dict()
    _log(P.pid, f"OCR: {len(samples)} sampel, repetisi per gerakan {n_rep}")
    return tl


def stage_pose(P, cfg, force=False):
    out = P.out("pose.npz")
    if out.exists() and not force:
        return dict(np.load(out))
    from .pose import track
    res = track(P.video, cfg["video"]["participant_box"],
                cfg["_root"] / cfg["paths"]["pose_model"], cfg["video"]["pose_frame_step"])
    np.savez(out, **res)
    _log(P.pid, f"pose: {len(res['t'])} frame, tanpa deteksi "
                f"{np.isnan(res['trunk_y']).mean() * 100:.1f}%")
    return res


def stage_sync(P, cfg, tl, pose, raw, force=False):
    dec = P.decisions()
    if "sync" in dec and dec["sync"].get("method") == "manual" and not force:
        return dec["sync"]
    out = P.out("sync.json")
    if out.exists() and not force:
        res = json.loads(out.read_text())
    else:
        res = sync.two_stage(tl, pose["t"], pose["motion"], raw, cfg)
        np.savez(P.out("sync_curves.npz"), **res.pop("curves"))
        res = {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in res.items()}
        res["problems"] = sync.qc(res, cfg)
        out.write_text(json.dumps(res, indent=2))
    dec["sync"] = dict(offset_sec=res["offset_sec"], method="auto",
                       accepted=not res["problems"], problems=res["problems"])
    P.save_decisions(dec)
    _log(P.pid, f"sync: offset {res['offset_sec']:+.2f} dtk (r_kasar {res['r_coarse']:.2f}, "
                f"r_halus {res['r_fine']:.2f}, drift {res['drift_sec']:+.2f})")
    if res["problems"]:
        raise QCStop(f"sync QC gagal: {res['problems']}. Periksa reports/{P.pid}_qc.html; "
                     f"isi sync.offset_sec dan method: manual di {P.decisions_path}")
    return dec["sync"]


def stage_phases(P, cfg, tl, pose, force=False):
    out = P.out("reps.csv")
    if out.exists() and not force:
        return pd.read_csv(out)
    reps = phases.detect_reps(tl, pose["t"], pose["trunk_y"], cfg)
    # koreksi manual (jika ada) menimpa hasil otomatis
    for fix in P.decisions().get("phase_fixes", []):
        m = (reps.task == fix["task"]) & (reps.rep == fix["rep"])
        for k, v in fix.items():
            if k not in ("task", "rep"):
                reps.loc[m, k] = v
    reps.to_csv(out, index=False)
    _log(P.pid, f"fase: {reps.compliance.value_counts().to_dict()}")
    return reps


def stage_preprocess(P, cfg, raw, force=False):
    out = P.out("clean_raw.fif")
    if out.exists() and not force:
        return mne.io.read_raw_fif(out, preload=True, verbose="error")
    dec = P.decisions()
    bads = dec.get("bad_channels", [])
    filt = preprocess.filter_raw(raw.copy(), cfg)
    ica, eog = preprocess.fit_ica(filt, bads)
    ica.save(P.out("ica.fif"), overwrite=True, verbose="error")
    exclude = dec.get("ica_exclude", eog)
    dec.setdefault("ica_exclude", exclude)
    dec.setdefault("ica_method", "auto: find_bads_eog Fp1/Fp2")
    P.save_decisions(dec)
    clean = preprocess.clean(raw, cfg, bads, ica, exclude)
    clean.save(out, overwrite=True, verbose="error")
    _log(P.pid, f"preprocess: kanal buruk {bads}, ICA dibuang {exclude}")
    return clean


def stage_erd(P, cfg, clean, reps, offset, force=False):
    out = P.results_dir / f"{P.pid}_erd_ers.csv"
    if out.exists() and not force:
        return pd.read_csv(out)
    ep = erd.make_epochs(clean, reps, offset, cfg)
    if ep is None or len(ep) == 0:
        _log(P.pid, "ERD: tidak ada epoch valid")
        return pd.DataFrame()
    ep.save(P.out("move-epo.fif"), overwrite=True, verbose="error")
    tab, _ = erd.erd_table(ep, P.pid, cfg)
    tab.to_csv(out, index=False)
    erd.lateralization(tab).to_csv(P.results_dir / f"{P.pid}_li.csv", index=False)
    _log(P.pid, f"ERD: {len(ep)} epoch, {len(tab)} baris")
    return tab


def stage_romberg(P, cfg, clean, tl, offset, force=False):
    out = P.results_dir / f"{P.pid}_romberg_features.csv"
    if out.exists() and not force:
        return pd.read_csv(out).iloc[0].to_dict()
    eeg_dur = clean.times[-1]
    segs = {}
    for cond, label in cfg["romberg"]["labels"].items():
        r = tl[tl.task == label]
        if r.empty:
            continue
        on, dur = float(r.start.iloc[0]), float(r.end.iloc[-1] - r.start.iloc[0])
        segs[cond] = (on + offset, dur, sync.coverage(on, dur, offset, eeg_dur))
    feat = romberg.features(clean, segs, P.pid, cfg)
    pd.DataFrame([feat]).to_csv(out, index=False)
    _log(P.pid, f"Romberg: cakupan EO {feat['coverage_EO']:.0%}, EC {feat['coverage_EC']:.0%}")
    return feat


def run(pid, cfg, stages=None, force=()):
    from . import report
    P = Participant(pid, cfg)
    stages = stages or STAGES
    f = lambda s: s in force or "all" in force
    raw = load_edf(P.trial_edf, cfg)
    tl = stage_ocr(P, cfg, f("ocr"))
    pose = stage_pose(P, cfg, f("pose"))
    ctx = dict(P=P, tl=tl, pose=pose, raw=raw, problems=[])
    try:
        s = stage_sync(P, cfg, tl, pose, raw, f("sync"))
        offset = s["offset_sec"]
        ctx["offset"] = offset
        reps = stage_phases(P, cfg, tl, pose, f("phases"))
        ctx["reps"] = reps
        if "preprocess" in stages:
            clean = stage_preprocess(P, cfg, raw, f("preprocess"))
            ctx["clean"] = clean
            if "erd" in stages:
                ctx["erd"] = stage_erd(P, cfg, clean, reps, offset, f("erd"))
            if "romberg" in stages:
                ctx["romberg"] = stage_romberg(P, cfg, clean, tl, offset, f("romberg"))
    except QCStop as e:
        ctx["problems"].append(str(e))
        _log(pid, f"BERHENTI: {e}")
    path = report.write(ctx, cfg)
    _log(pid, f"laporan QC: {path}")
    return ctx
