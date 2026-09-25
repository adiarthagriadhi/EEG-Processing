"""Metode baru: EEG saat gerak berbasis timestamp manual.

    .venv/bin/python analisis_baru/jalankan.py tahap1 P08 P09 P31 P32

Keluaran: analisis_baru/hasil/tahap1_kualitas/
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerakeeg import data, epoch, grafik, jendela, kualitas, pembanding, posisi   # noqa: E402

HASIL = Path(__file__).resolve().parent / "hasil"


def tahap1(pids):
    out = HASIL / "tahap1_kualitas"
    out.mkdir(parents=True, exist_ok=True)
    P, JK, JW, REP, WIN, SEL, masalah = [], [], [], [], [], [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, m = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        masalah += [dict(participant_id=pid, masalah=x) for x in m]
        REP.append(rep.assign(participant_id=pid))
        WIN.append(W.assign(participant_id=pid))
        for sumber, w in (("timestamp_manual", W), ("repo_video", pembanding.jendela_repo(pid, W))):
            p, jk, jw = kualitas.inventaris(pid, raw, w, sumber)
            P.append(p), JK.append(jk), JW.append(jw)
        SEL.append(pembanding.selisih_onset(pid, rep))
        print(f"[{pid}] {int(rep.lengkap.sum())}/{len(rep)} repetisi lengkap; {len(W)} jendela; "
              f"rep per gerakan {rep.groupby('gerakan').rep.apply(list).to_dict()}" + (f"; MASALAH {m}" if m else ""))
    P, JK, JW = pd.concat(P), pd.concat(JK), pd.concat(JW)
    pd.concat(REP).to_csv(out / "repetisi.csv", index=False)
    pd.concat(WIN).round(3).to_csv(out / "jendela_observasi.csv", index=False)
    pd.DataFrame(masalah, columns=["participant_id", "masalah"]).to_csv(out / "masalah_timestamp.csv", index=False)
    baru = P.sumber == "timestamp_manual"
    P[baru].to_csv(out / "potongan_1dtk.csv", index=False)
    JK.round(3).to_csv(out / "jendela_kanal.csv", index=False)
    JW.round(3).to_csv(out / "jendela.csv", index=False)
    rs = kualitas.ringkas(P, JK, JW)
    rs.round(1).to_csv(out / "ringkasan_fase.csv", index=False)
    rg = kualitas.ringkas(P[baru], JK[JK.sumber == "timestamp_manual"], JW[JW.sumber == "timestamp_manual"],
                          ("participant_id", "gerakan", "fase"))
    rg.round(1).to_csv(out / "ringkasan_gerakan_fase.csv", index=False)
    pk = (P[baru].assign(ok=P[baru].label == "ok").groupby(["participant_id", "kanal"]).ok.mean() * 100)
    pk.round(1).unstack(0).to_csv(out / "ringkasan_kanal_pct_ok.csv")
    sel = pd.concat(SEL)
    sel.round(3).to_csv(out / "pembanding_selisih_onset.csv", index=False)
    rb = rs[rs.fase.isin(["Gerak", "Tahan", "Naik"])]
    rb.round(1).to_csv(out / "pembanding_repo_vs_baru.csv", index=False)
    rsb = rs[rs.sumber == "timestamp_manual"]
    grafik.komposisi(rsb, out / "komposisi_kualitas_per_fase.png",
                     "Kualitas sinyal per fase — % potongan 1 dtk × kanal (EEG 1–35 Hz, sebelum koreksi)")
    grafik.peta_kanal(P[baru], out / "peta_kanal_pct_ok.png", "% potongan 1 dtk ok per kanal × fase")
    grafik.banding(rb, out / "pembanding_repo_vs_baru.png", "% potongan ok: analisis repo vs metode baru")
    pd.set_option("display.width", 250)
    kol = ["participant_id", "fase", "n_jendela", "pct_ok", "pct_tinggi", "pct_ekstrem", "pct_datar",
           "pct_layak_ketat", "ptp_median_uv", "panjang_median_dtk", "delta_db", "emg_db", "r_kiri", "r_kanan", "r_antar", "cakupan"]
    print(rsb[kol].round(2).to_string(index=False))
    print(rb[["participant_id", "sumber", "fase", "n_jendela", "pct_ok", "pct_ekstrem", "pct_datar",
              "pct_layak_ketat", "panjang_median_dtk"]].round(1).to_string(index=False))
    print(sel.drop(columns=["gerakan", "rep"]).groupby("participant_id").median().round(2).to_string())


def epoch_BE(pids):
    """Bandingkan epoching B (tetap 1,5 dtk dari onset − 0,5) dan E (jendela geser 1 dtk berlabel fase)."""
    out = HASIL / "epoch_B_vs_E"
    out.mkdir(parents=True, exist_ok=True)
    R, EST, REP = [], [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        _, xf, datar, sf = kualitas.sinyal(raw)
        T = xf.shape[1] / sf
        eB, eE = epoch.potong_B(W), epoch.potong_E(W, T)
        refB, _ = epoch.acuan(xf, datar, sf, W, epoch.B_PANJANG, epoch.B_PANJANG)
        refE, _ = epoch.acuan(xf, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER)
        est = pd.concat([epoch.estimasi(xf, datar, sf, eB, refB, "B"),
                         epoch.estimasi(xf, datar, sf, eE, refE, "E")])
        rp = epoch.per_repetisi(est)
        R.append(epoch.ringkas(pid, W[W.fase.isin(epoch.FASE_REPETISI)], eB, eE, est, rp))
        EST.append(est.assign(participant_id=pid))
        REP.append(rp.assign(participant_id=pid))
        print(f"[{pid}] B {len(eB)} epoch ({(~eB.muat).sum()} fase < 1 dtk); E {len(eE)} jendela")
    R = pd.concat(R)
    R.to_csv(out / "ringkasan_B_vs_E.csv", index=False)
    pd.concat(REP).round(3).to_csv(out / "estimasi_per_repetisi.csv", index=False)
    grafik.epoch_banding(R, out / "epoch_B_vs_E.png")
    pd.set_option("display.width", 250)
    print(R.to_string(index=False))


def bagian(pids):
    """Profil kualitas & sinyal per bagian fase (pra-onset/awal/tengah/akhir)."""
    out = HASIL / "bagian_fase"
    out.mkdir(parents=True, exist_ok=True)
    Q, S = [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        _, xf, datar, sf = kualitas.sinyal(raw)
        q, s = posisi.profil(pid, xf, datar, sf, W)
        Q.append(q), S.append(s)
        print(f"[{pid}] {len(q)} jendela kualitas, {len(s)} jendela spektrum")
    Q, S = pd.concat(Q), pd.concat(S)
    S.round(3).to_csv(out / "jendela_1dtk_per_bagian.csv", index=False)
    R = posisi.ringkas(Q, S)
    R.round(2).to_csv(out / "ringkasan_bagian_fase.csv", index=False)
    grafik.profil_bagian(R, out / "profil_bagian_fase.png")
    M = R.groupby(["fase", "bagian"], observed=True)[
        ["pct_bersih_05dtk", "delta_db", "otot_db", "mu_sm_db", "mu_sm_t", "beta_sm_db", "beta_sm_t",
         "porsi_E_semua", "porsi_E_bersih"]].median()
    M.round(2).to_csv(out / "median_4_partisipan.csv")
    pd.set_option("display.width", 250)
    print(M.round(2).to_string())


if __name__ == "__main__":
    cmd, *pids = sys.argv[1:]
    {"tahap1": tahap1, "epoch": epoch_BE, "bagian": bagian}[cmd](pids or ["P08", "P09", "P31", "P32"])
