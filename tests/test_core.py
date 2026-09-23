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
    chs = ["O1"]
    flat = (1 / f ** 1.2)[None]
    assert np.isnan(iaf((flat, chs), f, ["O1"]))
    peak = (1 / f ** 1.2 * (1 + 2.5 * np.exp(-(f - 10.5) ** 2 / 2)))[None]
    assert iaf((peak, chs), f, ["O1"]) == pytest.approx(10.5, abs=0.1)


def test_config_loads():
    cfg = load_config()
    assert cfg["eeg"]["sfreq"] == 100
    assert cfg["phases"]["hud_protocol"]["END"] == 8.0
