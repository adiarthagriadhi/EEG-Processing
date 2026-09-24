"""Uji sintetis fungsi inti (tanpa data partisipan). Jalankan: pytest -q"""
import numpy as np
import pandas as pd
import pytest

from eegpipe import ocr, phases, sync
from eegpipe.config import load_config
from eegpipe.romberg import iaf


@pytest.mark.parametrize("text,expected", [
    ("NGEED\n~\n1\nTURUN\n", ("NGEED", "TURUN")),
    ("NGEED | ~N | 1 | Turon", ("NGEED", "TURUN")),
    ("AGEM KANAN\n(Z)\nNAIK\n", ("AGEM KANAN", "NAIK")),
    ("AGEM KIRI\n4\nTAHAN", ("AGEM KIRI", "TAHAN")),
    ("ISTIRAHAT UTAMA\nzZ 57\n\ns\nreMiT COTES\nfoam", ("ISTIRAHAT UTAMA", None)),
    ("Berdiri\nMata Tertutup\n(30 Detik)\n", ("BERDIRI MATA TERTUTUP", None)),
    ("Berdiri\nIstirahat\n(15 Detik)", ("BERDIRI ISTIRAHAT", None)),
    ("Berdiri Fokus Mata Terbuka (30 Detik)", ("BERDIRI FOKUS MATA TERBUKA", None)),
    ("57\nNo", ("UNKNOWN", None)),
])
def test_parse_label(text, expected):
    assert ocr.parse_label(text) == expected


def test_segments_fill_missing_subphase_and_number_reps():
    rows = []
    for rep_start in (0.0, 16.0):
        for k in range(40):                      # 8 dtk @ 0,2 dtk
            t = rep_start + k * 0.2
            sub = "TURUN" if t - rep_start < 3 else "TAHAN" if t - rep_start < 5 else "NAIK"
            if k % 5 == 3:
                sub = None                       # OCR gagal membaca sub-fase
            rows.append(dict(t=t, task="NGEED", subphase=sub))
        for k in range(40):
            rows.append(dict(t=rep_start + 8 + k * 0.2, task="BERDIRI RILEKS", subphase=None))
    seg = ocr.segments(pd.DataFrame(rows))
    mv = seg[seg.subphase.notna()]
    assert list(mv.subphase) == ["TURUN", "TAHAN", "NAIK"] * 2
    assert list(mv.rep) == [1, 1, 1, 2, 2, 2]


def test_segment_phases_accuracy():
    rng = np.random.default_rng(0)
    errs = []
    for _ in range(30):
        t = np.arange(0, 12, 1 / 29.4)
        k = [0, 2, 3.5, 6, 7.5, 12]
        y = np.interp(t, k, [300, 300, 380, 380, 300, 300]) + rng.normal(0, 3, len(t))
        r = phases.segment_phases(t, y)
        got = np.array([r[c] for c in phases.PHASE_COLS])
        errs.append(got - np.array([2.15, 3.35, 6.15, 7.35]))   # persilangan 10%/90%
    assert np.nanmax(np.abs(errs)) < 0.25


def test_segment_phases_ignores_preparatory_bump():
    """Gerak persiapan kecil (~12% kedalaman) sebelum turun tidak boleh jadi onset."""
    t = np.arange(0, 12, 1 / 30)
    y = np.interp(t, [0, 0.5, 0.8, 1.2, 2, 3.5, 6, 7.5, 12],
                  [300, 300, 310, 300, 300, 380, 380, 300, 300])
    r = phases.segment_phases(t, y)
    assert r["act_turun"] == pytest.approx(2.15, abs=0.1)


def test_segment_phases_no_movement():
    t = np.arange(0, 10, 1 / 30)
    r = phases.segment_phases(t, 300 + np.random.default_rng(0).normal(0, 2, len(t)))
    assert np.isnan(r["act_turun"])


def test_xcorr_offset_recovers_shift():
    rng = np.random.default_rng(0)
    onsets = np.sort(rng.uniform(20, 420, 36))
    tv = np.arange(0, 450, 0.1)
    te = np.arange(0, 462, 0.1)
    v = 0.1 + sum(5 * ((tv >= o) & (tv < o + 2)) for o in onsets)
    e = 0.2 + sum(3 * ((te >= o + 1.3) & (te < o + 3.3)) for o in onsets) + rng.random(len(te))
    off, r, _, _ = sync.xcorr_offset(v, e, 10, 5)
    assert off == pytest.approx(1.3, abs=0.1)


def test_coverage():
    assert sync.coverage(411.5, 29.5, 1.6, 416.0) == pytest.approx((416 - 413.1) / 29.5)
    assert sync.coverage(366.4, 30.0, 1.6, 416.0) == 1.0


def test_iaf_rejects_flat_and_finds_peak():
    f = np.arange(1, 40.5, 0.5)

    def S(spec):   # 1 jendela × 1 kanal, amplitudo bersih
        return dict(psd=spec[None, None, :], f=f, ptp=np.array([[50.0]]), chs=["O1"])

    assert np.isnan(iaf(S(1 / f ** 1.2), ["O1"], 150))
    peak = 1 / f ** 1.2 * (1 + 2.5 * np.exp(-(f - 10.5) ** 2 / 2))
    assert iaf(S(peak), ["O1"], 150) == pytest.approx(10.5, abs=0.1)
    # jendela ber-artefak pada kanal fitur ditolak → NaN
    bad = S(peak)
    bad["ptp"] = np.array([[400.0]])
    assert np.isnan(iaf(bad, ["O1"], 150))


def test_group_stats_simulated_runs():
    from eegpipe import simulate, stats as st
    d = simulate.cohort()
    assert d.is_simulated.all()
    a, sens = st.paper_a(d[d.timepoint == "pre"])
    assert len(a) == 16 and a.p_fdr.notna().all()
    b, ind, rel = st.paper_b(d)
    assert 0 < rel["rxx"] < 1 and len(ind) == 14


def test_config_loads():
    cfg = load_config()
    assert cfg["eeg"]["sfreq"] == 100
    assert cfg["phases"]["hud_protocol"]["END"] == 8.0


def test_hypothesis_direction():
    from eegpipe.hypotheses import test as htest
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"group": ["penari"] * 10 + ["non-penari"] * 10,
                       "x": np.r_[rng.normal(0, 1, 10), rng.normal(3, 1, 10)]})
    hyp = {"A": {"label": "", "endpoint": "x", "expect": "penari < non-penari"},
           "B": {"label": "", "endpoint": "x", "expect": "penari > non-penari"},
           "C": {"label": "", "endpoint": "x", "expect": "non-penari < penari"}}
    r = htest(df, hyp).set_index("hipotesis")
    assert r.loc["A", "p_one_sided"] < 0.01 and r.loc["B", "p_one_sided"] > 0.9
    assert r.loc["C", "p_one_sided"] > 0.9


def test_phase_windows_trim_and_short_hold_kept():
    import pandas as pd
    from eegpipe.config import load_config
    from eegpipe.segments import phase_windows
    cfg = load_config()
    m = pd.Series(dict(act_arm=9.5, act_turun=10.0, act_tahan=11.5, act_naik=12.1, act_end=13.6))
    w = phase_windows(m, cfg)
    assert w["TURUN"][:2] == pytest.approx((10.225, 11.275))       # pangkas 15% (0,225 < 0,25)
    assert w["TAHAN"] is not None                                    # tahan 0,6 dtk tetap dipakai
    assert w["TAHAN"][1] - w["TAHAN"][0] == pytest.approx(0.6 * 0.7)
    assert w["PRA"][:2] == pytest.approx((7.5, 9.5))                 # dikunci gerak pertama (lengan)
    m2 = m.copy(); m2["act_naik"] = 11.7                             # tahan 0,2 dtk → tanpa nilai EEG
    assert phase_windows(m2, cfg)["TAHAN"] is None


def test_sync_alarm_fixed_offset():
    from eegpipe.config import load_config
    from eegpipe.sync import alarm
    cfg = load_config()
    ok = dict(offset_sec=0.75, offset_se_sec=0.04, r_coarse=0.69, spread_sec=0.06)
    assert alarm(ok, cfg, 0.85) == (None, None)
    far = dict(offset_sec=33.3, offset_se_sec=0.25, r_coarse=0.21, spread_sec=0.8)   # P34
    assert alarm(far, cfg, 0.85)[0] is not None
    nocoupling = dict(offset_sec=-28.0, offset_se_sec=0.25, r_coarse=0.01, spread_sec=0.5)  # P35
    al, warn = alarm(nocoupling, cfg, 0.85)
    assert al is None and warn is not None
