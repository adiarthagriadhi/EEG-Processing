"""Uji metode baru (tanpa data partisipan): .venv/bin/python -m pytest -q analisis_baru/tes"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gerakeeg import data, jendela, kualitas  # noqa: E402


def _ts(pairs):
    return data.bersihkan_timestamp(pd.DataFrame(dict(urutan=range(1, len(pairs) + 1),
                                                      waktu_detik=[t for _, t in pairs],
                                                      label=[l for l, _ in pairs])))


def _satu_rep(lab, t0):
    return [(lab, t0), (" T", t0 + 2), ("N ", t0 + 6), ("B", t0 + 7.5)]


def test_istilah_blok_dan_nomor_rep():
    seq = _satu_rep("AKA", 5) + _satu_rep("AKA", 21) + _satu_rep("N", 280) + _satu_rep("N", 296) + [("TT", 400)]
    rep, tt, masalah = jendela.repetisi(_ts(seq))
    assert masalah == [] and tt == 400
    assert rep.gerakan.tolist() == ["Agem Kanan", "Agem Kanan", "Ngeed", "Ngeed"]
    assert rep.rep.tolist() == [1, 2, 3, 4] and rep.blok.tolist() == [1, 1, 2, 2]
    r = rep.iloc[0]
    assert (r.onset_Gerak, r.onset_Tahan, r.onset_Naik, r.onset_Berdiri) == (5, 7, 11, 12.5)
    assert (r.durasi_Gerak, r.durasi_Tahan, r.durasi_Naik, r.durasi_Berdiri) == (2, 4, 1.5, 8.5)
    assert np.isnan(rep.durasi_Berdiri.iloc[1])        # repetisi terakhir blok: tak ada Gerak berikut di blok sama


def test_jendela_maju_05_dan_batas():
    seq = _satu_rep("AKI", 5) + _satu_rep("AKI", 21) + _satu_rep("N", 280) + [("TT", 400)]
    rep, tt, _ = jendela.repetisi(_ts(seq))
    W = jendela.jendela(rep, tt).set_index(["gerakan", "rep", "fase"])
    assert tuple(W.loc[("Agem Kiri", 1, "Gerak"), ["mulai", "selesai"]]) == (4.5, 7)
    assert tuple(W.loc[("Agem Kiri", 1, "Tahan"), ["mulai", "selesai"]]) == (6.5, 11)
    assert tuple(W.loc[("Agem Kiri", 1, "Naik"), ["mulai", "selesai"]]) == (10.5, 12.5)
    assert tuple(W.loc[("Agem Kiri", 1, "Berdiri"), ["mulai", "selesai"]]) == (12, 20.5)   # maks. B + 8
    assert tuple(W.loc[("-", 0, "Tutup Mata"), ["mulai", "selesai"]]) == (399.5, 430)
    ist = W.xs("Istirahat", level="fase").iloc[0]
    assert (ist.mulai, ist.selesai) == (28.5 + 8, 275)


def test_urutan_menyimpang_dicatat():
    rep, _, masalah = jendela.repetisi(_ts([("N", 5), ("T", 7), ("N", 10), ("AKA", 20), ("T", 22), ("N", 25),
                                            ("B", 26), ("B", 27)]))
    assert rep.lengkap.tolist() == [False, True] and len(masalah) == 2


def test_penanda_datar():
    x = np.random.default_rng(0).normal(0, 20, (2, 1000))
    x[0, 200:400] = 0.05
    m = kualitas.penanda_datar(x, 100.0)
    assert m[0, 220:380].all() and not m[1].any() and m[0, :180].sum() == 0
