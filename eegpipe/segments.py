"""Tahap `segmen` — pendekatan v2 (keputusan pengguna 2026-09-23; lihat CLAUDE.md "Audit segmen").

Prinsip:
- Waktu SETIAP subfase (TURUN/TAHAN/NAIK) dari video (pose) per repetisi; EEG dipetakan dengan
  offset (tetap 0,85 dtk kecuali keputusan manual). Tidak ada kalkulasi dari detik instruksi.
- SEMUA segmen dipakai: TAHAN singkat & repetisi yang tidak diam sebelum gerak TIDAK dibuang
  (variasi perilaku normal bukan alasan eksklusi). Batas fase dipangkas min(0,25 dtk; 15% durasi).
- Acuan GABUNGAN per partisipan: 50% jendela 2 dtk paling diam (gerak tubuh + pergelangan di video)
  selama BERDIRI RILEKS + ISTIRAHAT UTAMA.
- Specparam (aperiodik vs periodik) per kanal, area (pasangan kiri+kanan) dan belahan; gabungan
  12 segmen ("SEMUA") + per gerakan (4 segmen; eksploratif). Batas ketelitian per partisipan dari
  suntikan noise 1/f pada jendela acuan.
Keluaran (results/): PXX_segments.csv (segmen × kanal, power dB rel. acuan), PXX_area_map.csv,
PXX_durasi.csv (durasi subfase per repetisi), PXX_romberg_area.csv (Romberg EO/EC per area)."""
import numpy as np
import pandas as pd
from mne.time_frequency import psd_array_multitaper

from . import sync
from .spectral import LEFT, RIGHT, _inject

CH = LEFT + RIGHT                     # urutan kanal: 8 kiri (−A1) lalu 8 kanan (−A2)
GRID = np.arange(2, 30.01, 0.5)
BANDS = {"theta": (4, 8), "mu": (8, 13), "beta": (13, 30)}
PHASE_COLS = {"TURUN": ("act_turun", "act_tahan"), "TAHAN": ("act_tahan", "act_naik"),
              "NAIK": ("act_naik", "act_end")}


def spectra(x, sf):
    """Spektrum multitaper per kanal pada GRID. Lebar pita ≥ 2/T agar ≥ 1 taper pada jendela pendek."""
    T = x.shape[-1] / sf
    p, f = psd_array_multitaper(x, sf, fmin=1.5, fmax=31, bandwidth=max(2.5, 2.0 / T), verbose=False)
    return np.stack([np.interp(GRID, f, pp) for pp in p.reshape(-1, p.shape[-1])]).reshape(
        p.shape[:-1] + (len(GRID),))


def band_db(P):
    """log-power pita (dB) dari spektrum [..., GRID]."""
    out = {b: 10 * np.log10(P[..., (GRID >= lo) & (GRID < hi)].mean(-1)) for b, (lo, hi) in BANDS.items()}
    out["broad"] = 10 * np.log10(P[..., (GRID >= 2) & (GRID <= 30)].mean(-1))
    return out


def fit(P):
    """specparam (fixed): offset (dB), eksponen, tonjolan periodik per pita (dB di atas garis latar)."""
    from fooof import FOOOF
    fm = FOOOF(peak_width_limits=[2, 8], max_n_peaks=4, aperiodic_mode="fixed", verbose=False)
    fm.fit(GRID, P, [2, 30])
    flat = np.log10(P) - fm._ap_fit
    r = dict(offset=10 * fm.aperiodic_params_[0], exponent=fm.aperiodic_params_[1],
             r2=fm.r_squared_)
    for b, (lo, hi) in BANDS.items():
        r[b] = 10 * flat[(GRID >= lo) & (GRID < hi)].mean()
    return r


def _pool(S, sc):
    """Gabungan spektrum antar-segmen: 'mean' (baku) atau 'median' (tahan nilai ekstrem; uji sensitivitas)."""
    return np.median(S, 0) if sc.get("pool", "mean") == "median" else S.mean(0)


def phase_windows(m, cfg):
    """Jendela analisis (detik VIDEO) satu repetisi: {fase: (a, b, durasi_fase)}; None = tak terukur."""
    sc = cfg["segments"]
    arm = m.act_arm if np.isfinite(m.get("act_arm", np.nan)) else m.act_turun
    pw, po = cfg["erd"]["pre_window"], cfg["erd"]["post_window"]
    W = {"PRA": (arm + pw[0], arm + pw[1], pw[1] - pw[0]) if np.isfinite(arm) else None}
    for ph, (c0, c1) in PHASE_COLS.items():
        a, b = m[c0], m[c1]
        if not np.isfinite([a, b]).all() or b <= a:
            W[ph] = None
            continue
        tr = min(sc["trim_sec"], sc["trim_max_frac"] * (b - a))
        W[ph] = (a + tr, b - tr, b - a) if (b - a - 2 * tr) >= sc["min_win_sec"] else None
    W["POST"] = ((m.act_end + po[0], m.act_end + po[1], po[1] - po[0])
                 if np.isfinite(m.act_end) else None)
    return {ph: W[ph] for ph in sc["phases"]}


def flat_mask(raw_unfiltered, cfg):
    """Kanal × sampel: True = sinyal datar/hilang (reset amplifier). Dihitung dari EDF MENTAH."""
    sc, sf = cfg["segments"], raw_unfiltered.info["sfreq"]
    x = raw_unfiltered.get_data(picks=CH) * 1e6
    w = max(2, int(sc["flat_win_sec"] * sf))
    n = x.shape[1] // w
    sd = x[:, :n * w].reshape(len(CH), n, w).std(2)
    m = np.zeros(x.shape, bool)
    m[:, :n * w] = np.repeat(sd < sc["flat_sd_uv"], w, axis=1)
    pad = int(sc["flat_pad_sec"] * sf)
    if pad:
        from scipy.ndimage import binary_dilation
        m = binary_dilation(m, structure=np.ones((1, 2 * pad + 1), bool))
    return m


def body_motion(pose):
    """Indeks gerak tubuh video: kecepatan batang tubuh + pergelangan (masing-masing / median)."""
    s1 = sync.pose_speed(pose)[1]
    s2 = sync.wrist_speed(pose)
    m = s1 / np.nanmedian(s1)
    return m + s2 / np.nanmedian(s2) if s2 is not None else m


def quiet_windows(tl, pose, offset, T, cfg):
    """Awal jendela acuan (detik EEG) paling diam + ringkasan QC."""
    sc = cfg["segments"]
    pt, mot = pose["t"], body_motion(pose)
    W = []
    for _, r in tl[tl.task.isin(sc["baseline_tasks"])].iterrows():
        for a in np.arange(r.start + 0.5, r.end - sc["baseline_win_sec"] - 0.5 + 1e-9,
                           sc["baseline_step_sec"]):
            ae = float(sync.to_eeg(a, offset))
            if 0 <= ae and ae + sc["baseline_win_sec"] <= T:
                k = (pt >= a) & (pt < a + sc["baseline_win_sec"])
                if k.any():
                    W.append((ae, float(np.nanmedian(mot[k]))))
    if not W:
        return [], dict(n_candidates=0)
    W = np.array(W)
    thr = np.quantile(W[:, 1], sc["baseline_quiet_frac"])
    keep = W[W[:, 1] <= thr, 0]
    return list(keep), dict(n_candidates=len(W), n_quiet=len(keep), motion_thr=round(float(thr), 3))


def analyze(raw, reps, tl, pose, offset, pid, cfg, flat=None, seed=0):
    """Mengembalikan (segments, area_map, durasi, qc). flat: mask kanal×sampel (flat_mask)."""
    sc, sf = cfg["segments"], raw.info["sfreq"]
    X = raw.get_data(picks=CH) * 1e6
    T = raw.times[-1]
    if flat is None:
        flat = np.zeros(X.shape, bool)
    mx = sc["max_flat_frac"]
    ffrac = lambda a, b: flat[:, int(a * sf):int(b * sf)].mean(1)          # per kanal
    hemi = {c: ("kiri" if c in LEFT else "kanan") for c in CH}
    area_of = {c: a for a, chs in sc["areas"].items() for c in chs}

    # --- acuan gabungan
    starts, qc = quiet_windows(tl, pose, offset, T, cfg)
    wn = int(sc["baseline_win_sec"] * sf)
    B = np.stack([X[:, int(s * sf):int(s * sf) + wn] for s in starts])      # win × ch × t
    BV = np.stack([ffrac(s, s + sc["baseline_win_sec"]) <= mx for s in starts])   # win × ch valid
    PB = spectra(B, sf)                                                       # win × ch × f
    base_P = np.stack([PB[BV[:, k], k].mean(0) if BV[:, k].any() else np.full(len(GRID), np.nan)
                       for k in range(len(CH))])
    base_db = band_db(base_P)
    qc.update(baseline_valid_frac={c: round(float(BV[:, k].mean()), 2) for k, c in enumerate(CH)})

    # --- segmen
    rows, specs = [], []
    for _, m in reps.iterrows():
        if m.get("phase_source") == "hud_fallback" and not sc["include_hud_fallback"]:
            continue
        for ph, w in phase_windows(m, cfg).items():
            if w is None:
                continue
            a, b = float(sync.to_eeg(w[0], offset)), float(sync.to_eeg(w[1], offset))
            if not np.isfinite([a, b]).all() or a < 0 or b > T:
                continue
            P = spectra(X[:, int(a * sf):int(b * sf)], sf)                   # ch × f
            fr = ffrac(a, b)
            ok = fr <= mx
            specs.append((m.task, ph, P, ok))
            db = band_db(P)
            for k, c in enumerate(CH):
                r = dict(participant_id=pid, task=m.task, rep=m.rep, phase=ph, channel=c,
                         area=area_of[c], hemisphere=hemi[c], t0_video=round(w[0], 3),
                         t1_video=round(w[1], 3), dur_phase_sec=round(w[2], 3),
                         win_sec=round(b - a, 3), compliance=m.compliance,
                         phase_source=m.get("phase_source", "video"), flat_frac=round(float(fr[k]), 3),
                         valid=bool(ok[k]), is_simulated=cfg["is_simulated"])
                for bn in list(BANDS) + ["broad"]:
                    r[f"{bn}_db"] = db[bn][k] - base_db[bn][k] if ok[k] else np.nan
                rows.append(r)
    seg = pd.DataFrame(rows)

    # --- specparam: acuan vs gabungan segmen, per kanal / area / belahan
    fitn = lambda P: fit(P) if np.isfinite(P).all() else None
    fit_base_ch = [fitn(base_P[k]) for k in range(len(CH))]
    area_idx = {a: [CH.index(c) for c in chs] for a, chs in sc["areas"].items()}
    fit_base_ar = {a: fitn(np.nanmean(base_P[i], 0)) for a, i in area_idx.items()}
    out = []
    pools = {"SEMUA": None, **{t: t for t in sorted(reps.task.unique())}}
    for pool, task in pools.items():
        for ph in sc["phases"]:
            S = [(P, ok) for (t, p, P, ok) in specs if p == ph and (task is None or t == task)]
            if len(S) < 2:
                continue
            Ps, OK = np.stack([x[0] for x in S]), np.stack([x[1] for x in S])      # seg × ch × f, seg × ch
            base = dict(participant_id=pid, pool=pool, phase=ph, n_seg=len(S),
                        is_simulated=cfg["is_simulated"])
            minseg = sc["min_segments_flag"] if task is None else 3
            chrows = []
            for k, c in enumerate(CH):
                nv = int(OK[:, k].sum())
                f0 = fit_base_ch[k]
                if nv < 2 or f0 is None:
                    chrows.append(dict(base, level="kanal", unit=c, hemisphere=hemi[c], area=area_of[c],
                                       n_valid=nv, few_segments=True))
                    continue
                f1 = fit(_pool(Ps[OK[:, k], k], sc))
                chrows.append(dict(base, level="kanal", unit=c, hemisphere=hemi[c], area=area_of[c],
                                   n_valid=nv, few_segments=nv < minseg,
                                   **{f"{q}_change": f1[q] - f0[q] for q in ("offset", "exponent")},
                                   **{f"{b}_periodic_db": f1[b] - f0[b] for b in BANDS}, r2=f1["r2"]))
            ch = pd.DataFrame(chrows)
            for col in ["offset_change", "exponent_change"] + [f"{b}_periodic_db" for b in BANDS]:
                if col not in ch:
                    ch[col] = np.nan
            for h in ("kiri", "kanan"):                                   # tafsiran relatif per belahan
                hm = ch.hemisphere == h
                ch.loc[hm, "global_offset_db"] = ch.loc[hm, "offset_change"].median()
                for b in BANDS:
                    ch.loc[hm, f"{b}_relative_db"] = (ch.loc[hm, f"{b}_periodic_db"]
                                                      - ch.loc[hm, f"{b}_periodic_db"].median())
                out.append(dict(base, level="belahan", unit=h,
                                offset_change=ch.loc[hm, "offset_change"].median(),
                                exponent_change=ch.loc[hm, "exponent_change"].median(),
                                **{f"{b}_periodic_db": ch.loc[hm, f"{b}_periodic_db"].median()
                                   for b in BANDS}))
            out += ch.to_dict("records")
            for ar, i in area_idx.items():
                # spektrum area per segmen = rata-rata kanal VALID pasangan; segmen tanpa kanal valid dilewati
                v = OK[:, i]
                keep = v.any(1)
                f0 = fit_base_ar[ar]
                row = dict(base, level="area", unit=ar, area=ar, artifact_prone=ar in sc["artifact_prone"],
                           n_valid=int(keep.sum()))
                if keep.sum() >= 2 and f0 is not None:
                    Pa = _pool(np.stack([Ps[j][i][v[j]].mean(0) for j in np.where(keep)[0]]), sc)
                    f1 = fit(Pa)
                    row.update(few_segments=keep.sum() < minseg,
                               **{f"{q}_change": f1[q] - f0[q] for q in ("offset", "exponent")},
                               **{f"{b}_periodic_db": f1[b] - f0[b] for b in BANDS}, r2=f1["r2"])
                else:
                    row["few_segments"] = True
                out.append(row)
    amap = pd.DataFrame(out)

    # --- batas ketelitian: noise 1/f global per belahan (+8 dB) pada jendela acuan
    rng = np.random.default_rng(seed)
    allv = BV.all(1)                                   # jendela acuan tanpa kanal datar
    if allv.sum() >= 5:
        B0 = B[allv]
        P0 = spectra(B0, sf).mean(0)
        PN = spectra(np.stack([_inject(w, rng, sc["noise_inject_db"]) for w in B0]), sf).mean(0)
        floor = max(abs(fit(PN[k])[b] - fit(P0[k])[b]) for k in range(len(CH)) for b in ("mu", "beta"))
    else:
        floor = np.nan
    qc["n_baseline_allvalid"] = int(allv.sum())
    amap["noise_floor_db"] = floor
    fl = seg[seg.channel.isin(["C3", "C4"])].groupby("phase").valid.mean() if len(seg) else pd.Series(dtype=float)
    qc.update(noise_floor_db=round(float(floor), 2), n_segments=int(len(specs)),
              valid_frac_C3C4=fl.round(2).to_dict(),
              flat_pct_total={c: round(100 * float(flat[k].mean()), 1) for k, c in enumerate(CH)})

    # --- durasi subfase (perilaku, dari video)
    d = reps.copy()
    dur = pd.DataFrame(dict(participant_id=pid, task=d.task, rep=d.rep, compliance=d.compliance,
                            phase_source=d.get("phase_source", "video"),
                            dur_turun=d.act_tahan - d.act_turun, dur_tahan=d.act_naik - d.act_tahan,
                            dur_naik=d.act_end - d.act_naik, latency_hud=d.act_turun - d.hud_turun,
                            arm_lead=d.act_turun - d.get("act_arm", np.nan),
                            depth_px=d.get("depth_px", np.nan), is_simulated=cfg["is_simulated"]))
    return seg, amap, dur, qc


def romberg_area(raw, tl, offset, pid, cfg, flat=None):
    """Romberg EO/EC per area: specparam jendela 2 dtk bersih (≤ romberg_reject_uv per area),
    offset yang sama dengan gerak. Reaktivitas = periodik EC − EO."""
    sc, sf, T = cfg["segments"], raw.info["sfreq"], raw.times[-1]
    pad = cfg["romberg"]["pad_sec"]
    rows = []
    for cond, lab in cfg["romberg"]["labels"].items():
        r = tl[tl.task.str.upper() == lab]
        if r.empty:
            continue
        a0 = float(sync.to_eeg(r.start.iloc[0], offset)) + pad
        b0 = float(sync.to_eeg(r.end.iloc[-1], offset)) - pad
        a, b = max(a0, 0), min(b0, T)
        cov = max(0.0, b - a) / (b0 - a0)
        for ar, chs in sc["areas"].items():
            x = raw.get_data(picks=chs) * 1e6
            fm = flat[[CH.index(c) for c in chs]] if flat is not None else np.zeros(x.shape, bool)
            W = [(x[:, int(s * sf):int(s * sf) + int(2 * sf)], fm[:, int(s * sf):int(s * sf) + int(2 * sf)])
                 for s in np.arange(a, b - 2 + 1e-9, 1.0)]
            W = [w for w, f in W if np.ptp(w, axis=1).max() <= sc["romberg_reject_uv"]
                 and f.mean(1).max() <= sc["max_flat_frac"]]
            row = dict(participant_id=pid, kondisi=cond, area=ar, cakupan=round(cov, 3),
                       n_win=len(W), artifact_prone=ar in sc["artifact_prone"],
                       is_simulated=cfg["is_simulated"])
            if len(W) >= 2:
                f1 = fit(spectra(np.array(W), sf).mean((0, 1)))
                row.update(offset_db=f1["offset"], exponent=f1["exponent"],
                           **{f"{b}_periodic_db": f1[b] for b in BANDS})
            rows.append(row)
    return pd.DataFrame(rows)
