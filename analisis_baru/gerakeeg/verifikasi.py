"""Verifikasi rencana beku (RENCANA_BEKU.md) pada partisipan baru. Parameter di sini TIDAK boleh diubah tanpa
mencatat revisi di RENCANA_BEKU.md.

Per partisipan dihitung kriteria K0–K5; per kriteria kohort: dipertahankan bila lolos pada ≥ 75% partisipan yang
lolos K0.
"""
import re

import numpy as np
import pandas as pd

from . import data, epoch, jendela, kanal, kualitas, lonjakan, referensi
from .istilah import FASE_REPETISI

# ---- parameter beku ------------------------------------------------------------------------------------------------
MIN_REP_LENGKAP = 8          # K0
MIN_FASE_LOLOS = 3           # K1–K4: dari 4 fase repetisi
R_MEKANISME = 0.30           # K2b: korelasi dalam belahan (referensi telinga) saat Gerak
TOL_OTOT_DB = 0.10           # K3: A2 boleh lebih buruk ≤ 0,1 dB
MAKS_DIKELUARKAN = 10.0      # K3: % kanal-jendela dikeluarkan sebagai pencilan
MAKS_DISTORSI_MED_DB = 0.25  # K4: median |perubahan| power Istirahat antar-kanal (≈ ¼ efek ERD ±1 dB yang dicari)
MAKS_DISTORSI_KANAL_DB = 1.0 # K4: |perubahan| kanal terburuk (< galat baku estimasi ≈ 1,3 dB)
TOL_RELIABILITAS = 0.10      # K4: ASR boleh menurunkan reliabilitas ≤ 0,10
MAKS_REKONSTRUKSI = 40.0     # K4: % waktu direkonstruksi per belahan
MIN_KANAL_REP3 = 75.0        # K5: % kanal dengan ≥ 3 repetisi bersih agar fase layak dianalisis
AMBANG_KOHORT = 0.75
ASR_K = 20


def _hari(pid):
    try:
        v = pd.read_csv(data.TIMESTAMP / f"{pid}_timestamps.csv").get("nama_video")
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(v.iloc[0])) if v is not None else None
        return m.group(1) if m else ""
    except Exception:
        return ""


def _fase(R, col):
    return R.set_index("fase").reindex(FASE_REPETISI)[col]


def _nasib(xf, datar, sf, eTE, f):
    n = dikeluarkan = 0
    for e in eTE.itertuples():
        i0, i1 = int(round(e.mulai * sf)), int(round(e.selesai * sf))
        if i1 > xf.shape[1]:
            continue
        fd0 = datar[:, i0:i1].mean(axis=1)
        _, fd1 = f(xf[:, i0:i1], fd0)
        n += len(fd0)
        dikeluarkan += int(((fd0 < 0.1) & (fd1 >= 0.1)).sum())
    return 100 * dikeluarkan / max(n, 1)


def evaluasi(pid):
    """→ (baris lolos/gagal + angka, tabel ringkas per varian × fase)."""
    raw = data.muat_edf(pid)
    rep, tt, masalah = jendela.repetisi(data.muat_timestamp(pid))
    W = jendela.jendela(rep, tt)
    _, xf, datar, sf = kualitas.sinyal(raw)
    T = xf.shape[1] / sf
    Wr = W[W.fase.isin(FASE_REPETISI)]
    r = dict(participant_id=pid, hari_rekaman=_hari(pid), n_rep=len(rep), n_rep_lengkap=int(rep.lengkap.sum()),
             masalah_timestamp="; ".join(masalah), durasi_edf=round(T, 1),
             akhir_repetisi=round(float(rep.onset_Berdiri.max()), 1),
             pct_datar_total=round(100 * float(datar.mean()), 1))
    for fase, kol in (("Buka Mata", "cakupan_buka_mata"), ("Tutup Mata", "cakupan_tutup_mata")):
        m = W[W.fase == fase]
        r[kol] = (round(float(min(1, max(0, (T - m.onset.iloc[0]) / (m.selesai.iloc[0] - m.onset.iloc[0])))), 2)
                  if len(m) else np.nan)
    r["K0_data"] = bool(not masalah and r["n_rep_lengkap"] >= MIN_REP_LENGKAP and r["akhir_repetisi"] <= T)

    def jalankan(nama, ep, x=xf, skema=None, panjang=epoch.E_PANJANG, geser=epoch.E_GESER):
        ref, _ = epoch.acuan(x, datar, sf, W, panjang, geser, skema)
        est = epoch.estimasi(x, datar, sf, ep, ref, "TE", skema)
        return epoch.ringkas(pid, Wr, {"TE": ep}, est, epoch.per_repetisi(est)).assign(varian=nama), ref

    eTE, eE = epoch.potong_TE(W, T), epoch.potong_E(W, T)
    hasil = {}
    hasil["D_TE"], refD = jalankan("D_TE", eTE)
    hasil["D_E"], _ = jalankan("D_E", eE)
    hasil["A0_TE"], _ = jalankan("A0_TE", eTE, skema="A_belahan")
    hasil["A2_TE"], refA2 = jalankan("A2_TE", eTE, skema=kanal.robust)
    xa, info = lonjakan.asr(xf, datar, sf, W, ASR_K)
    hasil["A2_ASR20_TE"], refASR = jalankan("A2_ASR20_TE", eTE, x=xa, skema=kanal.robust)
    H = pd.concat(hasil.values())

    # K1 TE vs E (referensi telinga, seperti saat keputusan)
    a, b = _fase(hasil["D_TE"], "otot_db_median"), _fase(hasil["D_E"], "otot_db_median")
    r["K1_n_fase"] = int((a <= b).sum())
    r["K1_TE"] = r["K1_n_fase"] >= MIN_FASE_LOLOS
    # K2 referensi A vs D
    a, b = _fase(hasil["A0_TE"], "pct_kanal_epoch_bersih"), _fase(hasil["D_TE"], "pct_kanal_epoch_bersih")
    r["K2a_n_fase"] = int((a >= b).sum())
    kor, _ = referensi.evaluasi_tambahan(pid, xf, datar, sf, W.iloc[:0], eTE[eTE.fase == "Gerak"], "D_telinga", refD)
    r["r_dalam_belahan_gerak"] = round(float(kor[["r_kiri", "r_kanan"]].mean(axis=1).median()), 2) if len(kor) else np.nan
    r["K2a_A_lebih_bersih"] = r["K2a_n_fase"] >= MIN_FASE_LOLOS
    r["K2b_mekanisme_telinga"] = bool(r["r_dalam_belahan_gerak"] >= R_MEKANISME)
    # K3 A2 vs A0
    a, b = _fase(hasil["A2_TE"], "otot_db_median"), _fase(hasil["A0_TE"], "otot_db_median")
    r["K3_n_fase"] = int((a <= b + TOL_OTOT_DB).sum())
    r["pct_dikeluarkan_A2"] = round(_nasib(xf, datar, sf, eTE, kanal.robust), 1)
    r["K3_A2"] = r["K3_n_fase"] >= MIN_FASE_LOLOS and r["pct_dikeluarkan_A2"] <= MAKS_DIKELUARKAN
    # K4 ASR20 vs tanpa koreksi (keduanya A2)
    r["kalibrasi_min_dtk"] = min(info.get("kalibrasi_kiri_dtk", 0), info.get("kalibrasi_kanan_dtk", 0))
    r["rekonstruksi_maks_pct"] = max(info.get("pct_waktu_direkonstruksi_kiri", 0) or 0,
                                     info.get("pct_waktu_direkonstruksi_kanan", 0) or 0)
    dist = [np.abs(10 * np.log10(refASR[bnd] / refA2[bnd])) for bnd in ("theta", "mu", "beta", "otot")]
    r["distorsi_istirahat_median_db"] = round(float(max(np.nanmedian(d) for d in dist)), 3)
    r["distorsi_istirahat_maks_db"] = round(float(max(np.nanmax(d) for d in dist)), 3)
    a, b = _fase(hasil["A2_ASR20_TE"], "reliabilitas_belah_dua"), _fase(hasil["A2_TE"], "reliabilitas_belah_dua")
    r["K4_n_fase_reliabilitas"] = int((a >= b - TOL_RELIABILITAS).sum())
    r["K4_ASR20"] = bool(r["kalibrasi_min_dtk"] >= lonjakan.MIN_KALIBRASI_DTK
                         and r["distorsi_istirahat_median_db"] <= MAKS_DISTORSI_MED_DB
                         and r["distorsi_istirahat_maks_db"] <= MAKS_DISTORSI_KANAL_DB
                         and r["K4_n_fase_reliabilitas"] >= MIN_FASE_LOLOS
                         and r["rekonstruksi_maks_pct"] <= MAKS_REKONSTRUKSI)
    # K5 hasil akhir pipeline beku
    fin = hasil["A2_ASR20_TE"].set_index("fase").reindex(FASE_REPETISI)
    for f in FASE_REPETISI:
        r[f"K5_{f}_layak"] = bool(fin.loc[f, "pct_kanal_rep_valid_ge3"] >= MIN_KANAL_REP3)
        r[f"detik_bersih_{f}"] = fin.loc[f, "detik_bersih_median_kanal"]
    r["K5_semua_fase_layak"] = all(r[f"K5_{f}_layak"] for f in FASE_REPETISI)
    return r, H.assign(participant_id=pid)


KRITERIA = ["K0_data", "K1_TE", "K2a_A_lebih_bersih", "K2b_mekanisme_telinga", "K3_A2", "K4_ASR20",
            "K5_semua_fase_layak"]


def kohort(P, peserta=None):
    """Ringkasan per kriteria: jumlah lolos di antara partisipan yang lolos K0; per grup bila tersedia."""
    if peserta is not None and "group" in peserta:
        P = P.merge(peserta[["participant_id", "group", "age"]], on="participant_id", how="left")
    ok = P[P.K0_data]
    rows = []
    for k in KRITERIA:
        basis = P if k == "K0_data" else ok
        n, lol = len(basis), int(basis[k].sum())
        row = dict(kriteria=k, n=n, lolos=lol, proporsi=round(lol / n, 2) if n else np.nan,
                   keputusan=("—" if k == "K0_data" else
                              "dipertahankan" if n and lol / n >= AMBANG_KOHORT else "TINJAU (revisi tercatat)"),
                   gagal=", ".join(basis.loc[~basis[k].astype(bool), "participant_id"]))
        if "group" in P:
            for g, gg in basis.groupby("group"):
                row[f"lolos_{g}"] = f"{int(gg[k].sum())}/{len(gg)}"
        rows.append(row)
    return pd.DataFrame(rows)


def _md(df):
    """Tabel markdown sederhana (tanpa ketergantungan tabulate)."""
    fmt = lambda v: "" if (isinstance(v, float) and np.isnan(v)) else ("ya" if v is True else "TIDAK" if v is False
                                                                      else str(v))
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, sep] + body)


def laporan(P, K, path):
    lines = ["# Laporan verifikasi rencana beku", "",
             f"Partisipan: {len(P)} ({', '.join(P.participant_id)}). Aturan: kriteria dipertahankan bila lolos pada "
             f"≥ {int(100 * AMBANG_KOHORT)}% partisipan yang lolos K0. Definisi kriteria: RENCANA_BEKU.md.",
             "P08, P09, P31, P32 = set PENYETELAN (pilihan ditetapkan dari data mereka); hasil mereka bukan verifikasi.",
             "",
             "## Ringkasan kohort", "", _md(K), "",
             "## Per partisipan", "",
             _md(P[["participant_id", "hari_rekaman", "pct_datar_total"] + KRITERIA
               + ["r_dalam_belahan_gerak", "pct_dikeluarkan_A2", "kalibrasi_min_dtk", "rekonstruksi_maks_pct",
                  "distorsi_istirahat_median_db", "distorsi_istirahat_maks_db"]]), "",
             "Kriteria yang ditandai TINJAU tidak diubah otomatis. Revisi hanya melalui catatan di RENCANA_BEKU.md."]
    path.write_text("\n".join(lines))
