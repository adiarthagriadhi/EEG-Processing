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

STAGES = ["ocr", "pose", "sync", "phases", "preprocess", "erd", "spectral", "romberg", "baseline", "segmen", "report"]


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
    """pose.npz menyimpan kandidat mentah (cand_xy/cand_vis) + lintasan terpilih. Bila kandidat ada dan
    aturan pemilihan berubah, cukup `--force phases` setelah memanggil pose.select (tanpa MediaPipe)."""
    from . import pose as pz
    out = P.out("pose.npz")
    vc = cfg["video"]
    mode = vc.get("pose_select", "continuity")
    if out.exists() and not force:
        res = dict(np.load(out))
        if "cand_xy" in res and str(res.get("select_mode", "")) != mode + "_v2":
            res.update(pz.select(res, mode))          # pilih ulang dengan aturan terbaru
            res["select_mode"] = np.array(mode + "_v2")
            np.savez(out, **res)
            _log(P.pid, f"pose: pilih ulang ({mode}_v2), tanpa deteksi {np.isnan(res['trunk_y']).mean() * 100:.1f}%")
        return res
    box = P.decisions().get("participant_box", vc["participant_box"])  # override per partisipan
    res = pz.track(P.video, box, cfg["_root"] / cfg["paths"]["pose_model"], vc["pose_frame_step"],
                   select_mode=mode, num_poses=vc.get("pose_num_poses", 2))
    res["select_mode"] = np.array(mode + "_v2")
    np.savez(out, **res)
    _log(P.pid, f"pose: {len(res['t'])} frame, tanpa deteksi "
                f"{np.isnan(res['trunk_y']).mean() * 100:.1f}%")
    return res


def stage_sync(P, cfg, tl, pose, raw, force=False):
    """Estimasi berbasis data selalu dihitung (sync.json, cache). Mode `fixed` (v2): offset = offset
    tetap; estimasi hanya alarm. Keputusan manual (method: manual) tidak pernah ditimpa."""
    dec = P.decisions()
    out = P.out("sync.json")
    if out.exists() and not force:
        res = json.loads(out.read_text())
    else:
        res = sync.two_stage(tl, pose, raw, cfg)
        np.savez(P.out("sync_curves.npz"), **res.pop("curves"))
        res = json.loads(json.dumps(res, default=float))
    res["problems"], res["warnings"] = sync.qc(res, cfg)
    out.write_text(json.dumps(res, indent=2))
    _log(P.pid, f"sync (estimasi data): {res['offset_sec']:+.2f} ± "
                f"{res.get('offset_se_sec', float('nan')):.2f} dtk (n_rep {res.get('n_rep')}, "
                f"r kasar {res['r_coarse']:.2f}, IQR kombinasi {res['spread_sec']:.2f})")
    old = dec.get("sync", {})
    if old.get("method") == "manual":
        _log(P.pid, f"sync: keputusan MANUAL {old.get('offset_blocks', old.get('offset_sec'))} dtk "
                    f"({old.get('basis', '')})")
        return old
    if cfg["sync"].get("mode", "auto") == "fixed":
        fixed = float(cfg["sync"]["fixed_offset_sec"])
        al, warn = sync.alarm(res, cfg, fixed)
        dec["sync"] = dict(offset_sec=fixed, method="fixed", estimate_sec=res["offset_sec"],
                           estimate_se_sec=res.get("offset_se_sec"), alarm_pending=al,
                           warnings=[w for w in [warn] if w], accepted=al is None)
        P.save_decisions(dec)
        # alarm xcorr belum final: dikonfirmasi/dibantah cek onset-ke-onset setelah fase gerak
        _log(P.pid, f"sync: offset TETAP {fixed:+.2f} dtk" + (f" — {warn}" if warn else "")
             + (f" — ALARM TERTUNDA: {al}" if al else ""))
        return dec["sync"]
    dec["sync"] = dict(offset_sec=res["offset_sec"], offset_se_sec=res.get("offset_se_sec"),
                       method="auto", accepted=not res["problems"], problems=res["problems"],
                       warnings=res.get("warnings", []))
    P.save_decisions(dec)
    if res["problems"]:
        raise QCStop(f"sync QC gagal: {res['problems']}. Periksa reports/{P.pid}_qc.html; "
                     f"isi sync.offset_sec dan method: manual di {P.decisions_path}")
    return dec["sync"]


def stage_onset_check(P, cfg, raw, reps, offset, force=False):
    """Cek onset-ke-onset (onset artefak EEG vs onset lengan video). Mode auto: koreksi offset.
    Mode fixed: hanya ALARM (tidak mengubah offset). Keputusan manual: dicatat saja."""
    dec = P.decisions()
    s = dec.get("sync", {})
    oc = cfg["sync"]["onset_check"]
    chk = sync.onset_check(raw, reps, offset, cfg)
    s["onset_check"] = chk
    lag = chk["onset_lag_sec"]
    strong = chk["onset_n"] >= oc["min_n"] and chk["onset_lag_iqr"] <= oc["max_iqr_sec"]
    msg = (f"cek onset {lag:+.2f} dtk (IQR {chk['onset_lag_iqr']}, n {chk['onset_n']})")
    if s.get("method") == "manual":
        _log(P.pid, f"sync: {msg} pada offset manual")
    elif s.get("method") == "fixed":
        dec["sync"] = s
        P.save_decisions(dec)
        pend = s.pop("alarm_pending", None)
        lag_c = lag - oc.get("expected_lag_sec", 0.0) if np.isfinite(lag) else np.nan   # lag terkalibrasi
        s["onset_lag_calibrated_sec"] = None if not np.isfinite(lag_c) else round(float(lag_c), 2)
        if pend:
            dev = (s.get("estimate_sec") or 0.0) - s["offset_sec"]
            # alarm DRIFT tidak dapat dibantah median onset keseluruhan (blok 1 & 2 bisa meleset
            # berlawanan arah namun mediannya ≈ 0; P11) → selalu perlu keputusan offset per blok
            fits = (chk["onset_n"] >= oc["dismiss_min_n"] and np.isfinite(lag_c) and "bergeser" not in pend
                    and (abs(lag_c) <= oc["dismiss_max_lag_sec"] or np.sign(lag_c) != np.sign(dev)))
            if fits:
                s["alarm_dismissed"] = f"{pend} — DIBANTAH: {msg} (terkalibrasi {lag_c:+.2f}) pada offset tetap"
                s["accepted"] = True
                _log(P.pid, f"sync: alarm xcorr dibantah ({msg}; terkalibrasi {lag_c:+.2f} dtk)")
            else:
                s["alarm"], s["accepted"] = f"{pend}; {msg} (terkalibrasi {lag_c:+.2f}) tidak membantah", False
                dec["sync"] = s
                P.save_decisions(dec)
                raise QCStop(f"ALARM sinkronisasi: {s['alarm']}. Tinjau reports/{P.pid}_qc.html; bila "
                             f"penyimpangan nyata, isi sync.offset_sec + method: manual + basis di "
                             f"{P.decisions_path}")
        if strong and np.isfinite(lag_c) and abs(lag_c) > oc["alarm_lag_sec"]:
            s["alarm"], s["accepted"] = f"onset EEG menyimpang {lag_c:+.2f} dtk (terkalibrasi) dari onset video", False
            dec["sync"] = s
            P.save_decisions(dec)
            raise QCStop(f"ALARM sinkronisasi: {s['alarm']} (IQR {chk['onset_lag_iqr']}, n "
                         f"{chk['onset_n']}). Isi keputusan manual di {P.decisions_path}")
        _log(P.pid, f"sync: {msg} → offset tetap dipertahankan")
    elif strong and abs(lag) > oc["max_abs_lag_sec"]:
        s["offset_xcorr_sec"] = offset
        s["offset_sec"] = offset = round(offset + lag, 2)
        s["method"] = "auto+onset"
        _log(P.pid, f"sync: {msg} → offset dikoreksi ke {offset:+.2f} dtk")
    else:
        _log(P.pid, f"sync: {msg} → offset dipertahankan")
    dec["sync"] = s
    P.save_decisions(dec)
    return s.get("offset_blocks", s["offset_sec"])      # offset per blok (keputusan manual) bila ada


def stage_phases(P, cfg, tl, pose, force=False):
    out = P.out("reps.csv")
    if out.exists() and not force:
        return pd.read_csv(out)
    # lintasan vertikal (config video.trajectory): trunk_y (bahu+pinggul) default
    yk = cfg["video"].get("trajectory", "trunk_y")
    ytraj = pose[yk] if yk in pose else pose["trunk_y"]
    reps = phases.detect_reps(tl, pose["t"], ytraj, cfg, pose.get("wrists"))
    # koreksi manual (jika ada) menimpa hasil otomatis
    for fix in P.decisions().get("phase_fixes", []):
        m = (reps.task == fix["task"]) & (reps.rep == fix["rep"])
        for k, v in fix.items():
            if k not in ("task", "rep"):
                reps.loc[m, k] = v
    if cfg.get("reclass", {}).get("enabled", False):
        from .reclass import reclassify
        reps, info = reclassify(reps, pose, cfg, P.decisions())
        _log(P.pid, f"reklasifikasi: {info}")
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
        a = float(sync.to_eeg(r.start.iloc[0], offset)) + 5
        b = float(sync.to_eeg(r.end.iloc[0], offset)) - 5
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


def stage_spectral(P, cfg, force=False):
    """Referensi rata-rata spektral (eksploratif) + batas ketelitian per partisipan."""
    out = P.results_dir / f"{P.pid}_spectral.csv"
    if out.exists() and not force:
        return pd.read_csv(out)
    from . import spectral
    ep = mne.read_epochs(P.out("move-epo.fif"), verbose="error")
    df, floor = spectral.analyze(ep, P.pid, cfg)
    df["noise_floor_db"] = floor
    df.to_csv(out, index=False)
    g = df[df.channel.isin(["C3", "C4"])].groupby("phase").global_offset_db.median()
    _log(P.pid, f"spectral: batas ketelitian {floor:.1f} dB; indeks global (median) "
                f"{g.round(1).to_dict()}")
    return df


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
        segs[cond] = (float(sync.to_eeg(on, offset)), dur, sync.coverage(on, dur, offset, eeg_dur))
    feat = romberg.features(clean, segs, P.pid, cfg)
    feat["interpolated_channels"] = ";".join(P.decisions().get("bad_channels", []))
    pd.DataFrame([feat]).to_csv(out, index=False)
    _log(P.pid, f"Romberg: cakupan EO {feat['coverage_EO']:.0%}, EC {feat['coverage_EC']:.0%}")
    return feat


def stage_baseline(P, cfg, force=False):
    """Baseline.EDF (istirahat terpisah, sebelum Trial): fitur + uji sensitivitas ERD.
    Kanal buruk dan ICA dari Trial diterapkan (sesi & pemasangan elektroda sama)."""
    out = P.results_dir / f"{P.pid}_baseline_features.csv"
    if out.exists() and not force:
        return pd.read_csv(out).iloc[0].to_dict()
    from . import baseline
    from mne.preprocessing import read_ica
    dec = P.decisions()
    raw = load_edf(P.baseline_edf, cfg)
    filt = preprocess.filter_raw(raw.copy(), cfg)
    ica = read_ica(P.out("ica.fif"), verbose="error") if P.out("ica.fif").exists() else None
    clean = preprocess.clean(raw, cfg, dec.get("bad_channels", []), ica,
                             dec.get("ica_exclude", []))
    feat, _ = baseline.features(clean, filt, P.pid, cfg)
    pd.DataFrame([feat]).to_csv(out, index=False)
    msg = (f"baseline: {feat['baseline_sec']} dtk, kedipan {feat['blink_per_min']}/mnt, "
           f"alpha O1/O2 relatif {feat['rest_alpha_occ']:.2f}, IAF {feat['iaf_occ_rest']}")
    if P.out("move-epo.fif").exists():
        ep = mne.read_epochs(P.out("move-epo.fif"), verbose="error")
        sens = baseline.erd_sensitivity(ep, clean, P.pid, cfg)
        sens.to_csv(P.results_dir / f"{P.pid}_erd_sensitivity.csv", index=False)
        if len(sens):
            g = sens[sens.channel.isin(["C3", "C4"]) & (sens.band == "mu")].groupby("phase")[
                ["erd_ref_trial_pct", "erd_ref_restEDF_pct"]].median().round(0)
            msg += f"; ERD mu C3/C4 median (acuan Trial vs Baseline.EDF) {g.to_dict('index')}"
    _log(P.pid, msg)
    return feat


def stage_segmen(P, cfg, clean, reps, tl, pose, offset, raw, force=False):
    """Pendekatan v2: segmen dari video, acuan gabungan, specparam kanal/area/belahan, durasi,
    Romberg per area (lihat eegpipe/segments.py)."""
    from . import segments
    out = P.results_dir / f"{P.pid}_area_map.csv"
    qc_path = P.out("segmen_qc.json")
    if out.exists() and qc_path.exists() and not force:
        return json.loads(qc_path.read_text())
    flat = segments.flat_mask(raw, cfg)                  # dari EDF mentah (sebelum filter/ICA)
    np.savez_compressed(P.out("flat_mask.npz"), mask=np.packbits(flat, axis=1), shape=flat.shape)
    seg, amap, dur, qc = segments.analyze(clean, reps, tl, pose, offset, P.pid, cfg, flat=flat)
    rb = segments.romberg_area(clean, tl, offset, P.pid, cfg, flat=flat)
    seg.to_csv(P.results_dir / f"{P.pid}_segments.csv", index=False)
    amap.to_csv(out, index=False)
    dur.to_csv(P.results_dir / f"{P.pid}_durasi.csv", index=False)
    rb.to_csv(P.results_dir / f"{P.pid}_romberg_area.csv", index=False)
    qc["offset_sec"] = offset
    qc["n_seg_per_phase"] = (seg[seg.channel == "C3"].groupby("phase").size().to_dict()
                             if len(seg) else {})
    qc_path.write_text(json.dumps(qc, indent=2, default=float))
    c = amap[(amap.pool == "SEMUA") & (amap.level == "area") & (amap.unit == "sentral")]
    _log(P.pid, f"segmen v2: kanal×waktu datar (reset amplifier) median "
                f"{np.median(list(qc['flat_pct_total'].values())):.1f}%, C3/C4 valid per fase "
                f"{qc['valid_frac_C3C4']}")
    _log(P.pid, f"segmen v2: {qc['n_segments']} segmen {qc['n_seg_per_phase']}; acuan "
                f"{qc.get('n_quiet')} jendela diam; batas ketelitian {qc['noise_floor_db']:.1f} dB; "
                f"sentral garis latar {c.set_index('phase').offset_change.round(1).to_dict()}")
    return qc


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
        offset = s.get("offset_blocks", s["offset_sec"])
        ctx["offset"] = offset
        reps = stage_phases(P, cfg, tl, pose, f("phases"))
        ctx["reps"] = reps
        offset = stage_onset_check(P, cfg, raw, reps, offset, f("sync"))
        ctx["offset"] = offset
        if "preprocess" in stages:
            clean = stage_preprocess(P, cfg, raw, tl, offset, f("preprocess"))
            ctx["clean"] = clean
            if "erd" in stages:
                ctx["erd"] = stage_erd(P, cfg, clean, reps, offset, f("erd"))
            if "spectral" in stages and P.out("move-epo.fif").exists():
                ctx["spectral"] = stage_spectral(P, cfg, f("spectral"))
            if "romberg" in stages:
                ctx["romberg"] = stage_romberg(P, cfg, clean, tl, offset, f("romberg"))
            if "baseline" in stages:
                ctx["baseline"] = stage_baseline(P, cfg, f("baseline"))
            if "segmen" in stages:
                ctx["segmen"] = stage_segmen(P, cfg, clean, reps, tl, pose, offset, raw, f("segmen"))
    except QCStop as e:
        ctx["problems"].append(str(e))
        _log(pid, f"BERHENTI: {e}")
    path = report.write(ctx, cfg)
    _log(pid, f"laporan QC: {path}")
    return ctx
