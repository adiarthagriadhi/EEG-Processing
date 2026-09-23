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
    hud = P.decisions().get("hud_box", cfg["video"]["hud_box"])      # override per partisipan
    samples = ocr.run_ocr(P.video, hud, cfg["video"]["ocr_coarse_step_sec"])
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
    box = P.decisions().get("participant_box", cfg["video"]["participant_box"])  # override per partisipan
    res = track(P.video, box,
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
        res = sync.two_stage(tl, pose, raw, cfg)
        np.savez(P.out("sync_curves.npz"), **res.pop("curves"))
        res = json.loads(json.dumps(res, default=float))
        res["problems"] = sync.qc(res, cfg)
        out.write_text(json.dumps(res, indent=2))
    dec["sync"] = dict(offset_sec=res["offset_sec"], method="auto",
                       accepted=not res["problems"], problems=res["problems"])
    P.save_decisions(dec)
    _log(P.pid, f"sync: offset {res['offset_sec']:+.2f} dtk (kasar {res['coarse_sec']:+.1f}, "
                f"r_halus {res['r_fine']:.2f}, sebaran {res['spread_sec']:.2f}, "
                f"drift {res['drift_sec']:+.2f})")
    if res["problems"]:
        raise QCStop(f"sync QC gagal: {res['problems']}. Periksa reports/{P.pid}_qc.html; "
                     f"isi sync.offset_sec dan method: manual di {P.decisions_path}")
    return dec["sync"]


def stage_phases(P, cfg, tl, pose, force=False):
    out = P.out("reps.csv")
    if out.exists() and not force:
        return pd.read_csv(out)
    # lintasan vertikal (config video.trajectory): trunk_y (bahu+pinggul) default
    yk = cfg["video"].get("trajectory", "trunk_y")
    ytraj = pose[yk] if yk in pose else pose["trunk_y"]
    reps = phases.detect_reps(tl, pose["t"], ytraj, cfg)
    # koreksi manual (jika ada) menimpa hasil otomatis
    for fix in P.decisions().get("phase_fixes", []):
        m = (reps.task == fix["task"]) & (reps.rep == fix["rep"])
        for k, v in fix.items():
            if k not in ("task", "rep"):
                reps.loc[m, k] = v
    reps.to_csv(out, index=False)
    _log(P.pid, f"fase: {reps.compliance.value_counts().to_dict()}")
    return reps


def stage_preprocess(P, cfg, raw, tl, offset, force=False):
    out = P.out("clean_raw.fif")
    if out.exists() and not force:
        return mne.io.read_raw_fif(out, preload=True, verbose="error")
    dec = P.decisions()
    filt = preprocess.filter_raw(raw.copy(), cfg)
    r = tl[tl.task == "ISTIRAHAT UTAMA"]
    rest = None
    if len(r):
        a, b = r.start.iloc[0] + offset + 5, r.end.iloc[0] + offset - 5
        rest = (max(a, 0), min(b, raw.times[-1])) if b - a > 20 else None
    if "bad_channels" not in dec or dec.get("bad_channels_method", "").startswith("auto"):
        bads, z = preprocess.detect_bad_channels(filt, rest, cfg["eeg"]["bad_z"])
        dec["bad_channels"], dec["bad_channels_method"] = bads, "auto: z log-SD istirahat"
        dec["bad_channels_z"] = z
        if len(bads) > cfg["eeg"]["max_bad"]:
            P.save_decisions(dec)
            raise QCStop(f"{len(bads)} kanal buruk {bads} > batas {cfg['eeg']['max_bad']}")
    bads = dec["bad_channels"]
    ica = preprocess.fit_ica(filt, bads, rest)
    ica.save(P.out("ica.fif"), overwrite=True, verbose="error")
    eog, blink = preprocess.blink_components(ica, filt, bads)
    dec["ica_blink_qc"] = blink
    # nomor komponen hanya berlaku untuk ICA yang sama: keputusan otomatis selalu diperbarui
    # saat ICA di-fit ulang; keputusan manual dipertahankan (hapus bila kanal buruk berubah)
    if dec.get("ica_method", "auto").startswith("auto"):
        dec["ica_exclude"], dec["ica_method"] = eog, "auto: serakah, ERP kedipan Fp1+Fp2"
    exclude = dec["ica_exclude"]
    P.save_decisions(dec)
    clean = preprocess.clean(raw, cfg, bads, ica, exclude)
    clean.save(out, overwrite=True, verbose="error")
    _log(P.pid, f"preprocess: kanal buruk {bads}, ICA dibuang {exclude}, kedipan "
                f"{blink.get('before')}→{blink.get('after')} µV ({blink.get('n_blinks')} kedipan)")
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
    tab["interpolated"] = tab.channel.isin(P.decisions().get("bad_channels", []))
    tab.to_csv(out, index=False)
    tt, times, freqs, chs = erd.task_tfr(ep, cfg)
    np.savez(P.out("task_tfr.npz"), times=times, freqs=freqs, ch_names=np.array(chs),
             tasks=np.array(list(tt)), **{f"data_{i}": v["data"] for i, v in enumerate(tt.values())},
             **{f"phases_{i}": v["phases"] for i, v in enumerate(tt.values())},
             n=np.array([v["n"] for v in tt.values()]))
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
    feat["interpolated_channels"] = ";".join(P.decisions().get("bad_channels", []))
    pd.DataFrame([feat]).to_csv(out, index=False)
    _log(P.pid, f"Romberg: cakupan EO {feat['coverage_EO']:.0%}, EC {feat['coverage_EC']:.0%}")
    return feat


def run(pid, cfg, stages=None, force=()):
    from . import report
    P = Participant(pid, cfg)
    stages = stages or STAGES
    # memaksa satu tahap = memaksa semua tahap sesudahnya (hasilnya bergantung)
    first = min([STAGES.index(s) for s in force if s in STAGES] +
                [0 if "all" in force else len(STAGES)])
    f = lambda s: STAGES.index(s) >= first
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
            clean = stage_preprocess(P, cfg, raw, tl, offset, f("preprocess"))
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
