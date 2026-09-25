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


def test_epoch_B_dan_E():
    from gerakeeg import epoch
    seq = _satu_rep("AKA", 5) + _satu_rep("AKA", 21) + [("TT", 400)]
    rep, tt, _ = jendela.repetisi(_ts(seq))
    W = jendela.jendela(rep, tt)
    B = epoch.potong_B(W).set_index(["rep", "fase"])
    assert tuple(B.loc[(1, "Gerak"), ["mulai", "selesai"]]) == (4.5, 6.0) and B.muat.all()
    E = epoch.potong_E(W, 500.0)
    g = E[(E.rep == 1) & (E.fase == "Naik")]          # jendela observasi Naik 10,5 … 12,5 → awal 10,5 … 11,5
    assert np.allclose(g.mulai.values, [10.5, 10.75, 11.0, 11.25, 11.5])
    assert ((E.selesai - E.mulai) == 1.0).all()


def test_epoch_terarah_T_dan_TE():
    from gerakeeg import epoch
    seq = _satu_rep("AKA", 5) + _satu_rep("AKA", 21) + [("TT", 400)]
    rep, tt, _ = jendela.repetisi(_ts(seq))
    W = jendela.jendela(rep, tt)
    T = epoch.potong_T(W).set_index(["rep", "fase"])
    assert tuple(T.loc[(1, "Gerak"), ["mulai", "selesai"]]) == (4.5, 6.0)           # inisiasi
    assert tuple(T.loc[(1, "Tahan"), ["mulai", "selesai"]]) == (8.25, 9.75)         # tengah Tahan 7…11
    assert tuple(T.loc[(1, "Berdiri"), ["mulai", "selesai"]]) == (18.5, 20.0)       # akhir = B + 8 = 20,5 → 2,0…0,5 dtk sebelumnya
    TE = epoch.potong_TE(W, 500.0)
    g = TE[(TE.rep == 1) & (TE.fase == "Tahan")]                                   # tengah + akhir: 8,33 … 11
    assert g.mulai.min() >= 7 + 4 / 3 - 1e-9 and g.selesai.max() <= 11 + 1e-9


def test_skema_referensi():
    from gerakeeg import referensi
    from gerakeeg.istilah import KANAL
    rng = np.random.default_rng(1)
    x = rng.normal(0, 5, (16, 100))
    x[:8] += 50 * np.sin(np.linspace(0, 6, 100))              # artefak bersama belahan kiri (A1)
    fd = np.zeros(16)
    y, _ = referensi.terapkan("A_belahan", x, fd)
    assert np.abs(y[:8].mean(axis=0)).max() < 1e-9           # komponen bersama belahan hilang
    assert np.ptp(y[:8], axis=1).max() < 60                  # artefak 100 µV ptp terhapus
    fd[2] = 0.5                                              # C3 datar → tidak ikut referensi
    y2, fd2 = referensi.terapkan("B_rata16", x, fd)
    ok = [i for i in range(16) if i != 2]
    assert np.allclose(y2[0], x[0] - x[ok].mean(axis=0)) and fd2[2] == 0.5
    yb, fb = referensi.terapkan("C_bipolar", x, fd)
    assert referensi.nama("C_bipolar")[1] == "F3-C3" and fb[1] == 0.5 and fb[2] == 0.5
    assert np.allclose(yb[0], x[KANAL.index("Fp1")] - x[KANAL.index("F3")])


def test_kanal_robust_dan_interpolasi():
    from gerakeeg import kanal
    rng = np.random.default_rng(2)
    x = rng.normal(0, 5, (16, 100))
    x[2] += 400 * np.sin(np.linspace(0, 3, 100))              # C3 pencilan besar
    fd = np.zeros(16)
    y0, _ = kanal.rata_belahan(x, fd)
    y2, fd2 = kanal.robust(x, fd)
    assert fd2[2] >= 1.0 and (fd2[[0, 1, 3, 4, 5, 6, 7]] < 0.1).all()       # hanya C3 dikeluarkan
    assert np.ptp(y2[0]) < 0.5 * np.ptp(y0[0])                               # Fp1 tak lagi tercemar C3
    y4, fd4 = kanal.robust_interp(x, fd)
    assert fd4[2] == kanal.TANDA_INTERP and np.isfinite(y4[2]).all() and np.ptp(y4[2]) < 100
