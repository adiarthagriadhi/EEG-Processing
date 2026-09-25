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


def test_asr_sendiri():
    from gerakeeg.lonjakan import asr_kalibrasi, asr_proses
    rng = np.random.default_rng(0)
    A = rng.normal(size=(8, 8))
    cal, x = A @ rng.normal(0, 5, (8, 6000)), A @ rng.normal(0, 5, (8, 20000))
    art = np.zeros_like(x)
    art[:, 5000:5100] = np.outer(rng.normal(size=8), 100 * np.hanning(100) * np.sin(np.arange(100) / 3))
    M, T = asr_kalibrasi(cal, 100.0, 20)
    y, _ = asr_proses(x + art, 100.0, M, T)
    assert np.mean([np.corrcoef(x[i, 6000:], y[i, 6000:])[0, 1] for i in range(8)]) > 0.999   # bersih utuh
    assert np.sum((y - x)[:, 4900:5200] ** 2) < 0.25 * np.sum(art ** 2)                         # artefak besar turun


def test_kohort_ambang_75():
    import pandas as pd
    from gerakeeg import verifikasi
    P = pd.DataFrame(dict(participant_id=[f"P{i:02d}" for i in range(8)], K0_data=[True] * 7 + [False]))
    for k in verifikasi.KRITERIA[1:]:
        P[k] = True
    P.loc[[0, 1], "K4_ASR20"] = False            # 5/7 = 0,71 < 0,75 → TINJAU
    P.loc[[0], "K3_A2"] = False                  # 6/7 = 0,86 → dipertahankan
    K = verifikasi.kohort(P).set_index("kriteria")
    assert K.loc["K4_ASR20", "keputusan"].startswith("TINJAU") and K.loc["K4_ASR20", "n"] == 7
    assert K.loc["K3_A2", "keputusan"] == "dipertahankan"
    assert K.loc["K0_data", "lolos"] == 7


def test_cca_otot_buang_komponen_bising():
    from gerakeeg import mata_otot
    rng = np.random.default_rng(3)
    t = np.arange(100) / 100
    lambat = np.vstack([np.sin(2 * np.pi * f * t + p) for f, p in zip([3, 5, 7, 9, 11, 6], rng.uniform(0, 6, 6))])
    A = rng.normal(size=(8, 6))
    otot = rng.normal(0, 1, 100)                             # derau putih ≈ otot (datar spektrum)
    x = A @ lambat * 10 + np.outer(rng.normal(size=8), otot) * 10
    y = mata_otot.cca_otot(x, np.zeros(8), 100.0, ambang=0.5)
    r = lambda a, b: abs(np.corrcoef(a, b)[0, 1])
    assert np.mean([r(y[i] - (A @ lambat * 10)[i], otot) for i in range(8)]) < \
        np.mean([r(x[i] - (A @ lambat * 10)[i], otot) for i in range(8)])         # porsi otot berkurang


def test_aturan_cakupan_dan_pilihan():
    import pandas as pd
    from gerakeeg import aturan
    # satu repetisi Gerak, rentang 4 jendela (0; 0,25; 0,5; 0,75 → 1,75 dtk); 2 jendela bersih di awal
    est = pd.DataFrame(dict(participant_id="P99", gerakan="Ngeed", rep=1, fase="Gerak", kanal="C3",
                            mulai=[0.0, 0.25, 0.5, 0.75], bersih=[True, True, False, False],
                            theta_db=[1.0, 1.0, np.nan, np.nan], mu_db=[0.0, 0.0, np.nan, np.nan],
                            beta_db=[0.0, 0.0, np.nan, np.nan], otot_db=[0.0, 0.0, np.nan, np.nan]))
    nr = aturan.nilai_repetisi(est)
    r = nr.iloc[0]
    assert r.n_bersih == 2 and np.isclose(r.detik_bersih, 1.25) and np.isclose(r.rentang_detik, 1.75)
    assert np.isclose(r.cakupan, 1.25 / 1.75)
    assert bool(aturan._lolos_R1(nr, 0.5).iloc[0]) and not bool(aturan._lolos_R1(nr, 0.75).iloc[0])
    h = pd.DataFrame(dict(c_min=[0.0, 0.5, 0.75], r_min=3, fase="Gerak", pct_sel_lolos_R2=[100, 80, 60]))
    assert aturan.pilih_c(h) == 0.5


def test_label_buka_mata():
    from gerakeeg import aturan
    seq = _satu_rep("AKA", 5) + _satu_rep("AKA", 21) + [("BM", 370), ("TT", 415)]
    rep, tt, masalah = jendela.repetisi(_ts(seq))
    assert masalah == [] and rep.attrs["BM"] == 370 and tt == 415
    W = jendela.jendela(rep, tt).set_index("fase")
    assert tuple(W.loc["Buka Mata", ["mulai", "selesai"]]) == (369.5, 400)        # BM + 30 < TT
    rep2, _, _ = jendela.repetisi(_ts(_satu_rep("AKA", 5) + [("BM", 370), ("TT", 390)]))
    W2 = jendela.jendela(rep2, 390).set_index("fase")
    assert W2.loc["Buka Mata", "selesai"] == 390                                  # berhenti di TT
    M = aturan.potong_mata(jendela.jendela(rep, tt), 500.0)
    assert set(M.fase) == {"Buka Mata", "Tutup Mata"} and M[M.fase == "Buka Mata"].mulai.min() == 371
    _, _, m3 = jendela.repetisi(_ts(_satu_rep("AKA", 5) + [("TT", 380), ("BM", 390)]))
    assert any("BM" in x for x in m3)                                             # urutan salah dicatat


def test_buka_mata_dari_tt_minus_45():
    from gerakeeg import aturan
    seq = _satu_rep("AKA", 5) + _satu_rep("AKA", 21) + _satu_rep("N", 280) + [("TT", 330)]
    rep, tt, masalah = jendela.repetisi(_ts(seq))
    assert masalah == [] and rep.attrs["BM"] == 285 and rep.attrs["BM_sumber"].startswith("TT")
    W = jendela.jendela(rep, tt).set_index("fase")
    bm = W.loc["Buka Mata"]
    assert (bm.onset, bm.selesai) == (285, 315)                        # BM + 30 = TT − 15
    assert bm.mulai_analisis == 287.5 + 8                              # B terakhir (287,5) + 8 dtk > BM + 1
    M = aturan.potong_mata(jendela.jendela(rep, tt), 500.0)
    assert M[M.fase == "Buka Mata"].mulai.min() == 295.5
