"""Metode baru: EEG saat gerak berbasis timestamp manual.

    .venv/bin/python analisis_baru/jalankan.py tahap1 P08 P09 P31 P32

Keluaran: analisis_baru/hasil/tahap1_kualitas/
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerakeeg import (data, epoch, grafik, jendela, kanal, kualitas, lonjakan, pembanding,  # noqa: E402
                      posisi, referensi, verifikasi)

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


def epoch_banding(pids):
    """Bandingkan epoching B (tetap 1,5 dtk dari onset − 0,5), T (terarah 1,5 dtk di bagian informatif)
    dan E (jendela geser 1 dtk berlabel fase)."""
    out = HASIL / "epoch_banding"
    out.mkdir(parents=True, exist_ok=True)
    R, REP = [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        _, xf, datar, sf = kualitas.sinyal(raw)
        T = xf.shape[1] / sf
        ep = {"B": epoch.potong_B(W), "T": epoch.potong_T(W), "TE": epoch.potong_TE(W, T),
              "E": epoch.potong_E(W, T)}
        ref15, _ = epoch.acuan(xf, datar, sf, W, epoch.B_PANJANG, epoch.B_PANJANG)
        ref10, _ = epoch.acuan(xf, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER)
        est = pd.concat([epoch.estimasi(xf, datar, sf, e, ref10 if m in ("E", "TE") else ref15, m) for m, e in ep.items()])
        rp = epoch.per_repetisi(est)
        R.append(epoch.ringkas(pid, W[W.fase.isin(epoch.FASE_REPETISI)], ep, est, rp))
        REP.append(rp.assign(participant_id=pid))
        print(f"[{pid}] B {len(ep['B'])} ({(~ep['B'].muat).sum()} tak muat); T {len(ep['T'])} "
              f"({(~ep['T'].muat).sum()} tak muat); TE {len(ep['TE'])}; E {len(ep['E'])} jendela")
    R = pd.concat(R)
    R.to_csv(out / "ringkasan_epoch.csv", index=False)
    pd.concat(REP).round(3).to_csv(out / "estimasi_per_repetisi.csv", index=False)
    grafik.epoch_banding(R, out / "epoch_banding.png")
    pd.set_option("display.width", 250)
    print(R.drop(columns=["n_repetisi"]).to_string(index=False))


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


def tahap2(pids):
    """Tahap 2: bandingkan skema referensi (D telinga asli, A rata-rata belahan, B rata-rata 16, C bipolar)
    dengan epoch TE."""
    out = HASIL / "tahap2_referensi"
    out.mkdir(parents=True, exist_ok=True)
    R, K, BG, IS, REP = [], [], [], [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        _, xf, datar, sf = kualitas.sinyal(raw)
        eTE = epoch.potong_TE(W, xf.shape[1] / sf)
        Wr = W[W.fase.isin(epoch.FASE_REPETISI)]
        for sk in referensi.SKEMA:
            ref, m_ist = epoch.acuan(xf, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER, sk)
            est = epoch.estimasi(xf, datar, sf, eTE, ref, "TE", sk)
            rp = epoch.per_repetisi(est)
            R.append(epoch.ringkas(pid, Wr, {"TE": eTE}, est, rp).assign(skema=sk))
            REP.append(rp.assign(participant_id=pid, skema=sk))
            kor, ber = referensi.evaluasi_tambahan(pid, xf, datar, sf, W, eTE, sk, ref)
            K.append(kor)
            BG.append(ber)
            IS.append(dict(participant_id=pid, skema=sk, pct_istirahat_bersih=round(100 * float(np.median(m_ist)), 1)))
        print(f"[{pid}] {len(eTE)} jendela TE × {len(referensi.SKEMA)} skema")
    R, K, BG, IS = pd.concat(R), pd.concat(K), pd.DataFrame(BG), pd.DataFrame(IS)
    R.to_csv(out / "ringkasan_skema_fase.csv", index=False)
    K.round(3).to_csv(out / "korelasi_belahan.csv", index=False)
    BG.merge(IS, on=["participant_id", "skema"]).round(2).to_csv(out / "berger_istirahat.csv", index=False)
    pd.concat(REP).round(3).to_csv(out / "estimasi_per_repetisi.csv", index=False)
    grafik.tahap2(R, K, BG, out / "tahap2_referensi.png")
    pd.set_option("display.width", 250)
    kol = ["pct_kanal_epoch_bersih", "otot_db_median", "detik_bersih_median_kanal", "pct_kanal_rep_valid_ge3",
           "se_db_median", "reliabilitas_belah_dua"]
    print(R.groupby(["fase", "skema"], sort=False)[kol].median().round(2).to_string())
    print(K.groupby(["fase", "skema"], sort=False)[["r_kiri", "r_kanan", "r_antar", "bersih_kiri",
                                                    "bersih_kanan"]].median().round(2).to_string())
    print(BG.merge(IS).round(2).to_string(index=False))


def tahap3(pids):
    """Tahap 3: kanal buruk & sinyal datar di atas referensi A + epoch TE."""
    out = HASIL / "tahap3_kanal"
    out.mkdir(parents=True, exist_ok=True)
    R, K, KB, REP, NASIB = [], [], [], [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        _, xf, datar, sf = kualitas.sinyal(raw)
        eTE = epoch.potong_TE(W, xf.shape[1] / sf)
        Wr = W[W.fase.isin(epoch.FASE_REPETISI)]
        buruk, z = kanal.kanal_buruk_rekaman(xf, datar, sf, W)
        KB.append(dict(participant_id=pid, kanal_buruk_rekaman=";".join(kanal.KANAL[k] for k in buruk),
                       **{f"z_{c}": round(float(v), 2) for c, v in zip(kanal.KANAL, z)}))
        for v in kanal.VARIAN:
            f = kanal.pembuat(v, buruk)
            ref, _ = epoch.acuan(xf, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER, f)
            est = epoch.estimasi(xf, datar, sf, eTE, ref, "TE", f)
            rp = epoch.per_repetisi(est)
            R.append(epoch.ringkas(pid, Wr, {"TE": eTE}, est, rp).assign(varian=v))
            REP.append(rp.assign(participant_id=pid, varian=v))
            # nasib kanal-jendela: datar asli / dikeluarkan metode / diinterpolasi
            n = dict(datar_asli=0, dikeluarkan=0, interpolasi=0, total=0)
            for e in eTE.itertuples():
                i0, i1 = int(round(e.mulai * sf)), int(round(e.selesai * sf))
                if i1 > xf.shape[1]:
                    continue
                fd0 = datar[:, i0:i1].mean(axis=1)
                _, fd1 = f(xf[:, i0:i1], fd0)
                n["total"] += len(fd0)
                n["datar_asli"] += int((fd0 >= 0.1).sum())
                n["dikeluarkan"] += int(((fd0 < 0.1) & (fd1 >= 0.1)).sum())
                n["interpolasi"] += int((fd1 == kanal.TANDA_INTERP).sum())
            NASIB.append(dict(participant_id=pid, varian=v, **{k: round(100 * n[k] / n["total"], 1)
                                                               for k in ("datar_asli", "dikeluarkan", "interpolasi")}))
        print(f"[{pid}] kanal buruk per rekaman: {[kanal.KANAL[k] for k in buruk]}")
    R, KB, NASIB = pd.concat(R), pd.DataFrame(KB), pd.DataFrame(NASIB)
    R.to_csv(out / "ringkasan_varian_fase.csv", index=False)
    KB.to_csv(out / "kanal_buruk_rekaman.csv", index=False)
    NASIB.to_csv(out / "nasib_kanal_jendela.csv", index=False)
    pd.concat(REP).round(3).to_csv(out / "estimasi_per_repetisi.csv", index=False)
    grafik.tahap3(R, out / "tahap3_kanal.png")
    pd.set_option("display.width", 250)
    kol = ["pct_kanal_epoch_bersih", "otot_db_median", "detik_bersih_median_kanal", "pct_kanal_rep_valid_ge3",
           "se_db_median", "reliabilitas_belah_dua"]
    print(R.groupby(["fase", "varian"], sort=False)[kol].median().round(2).to_string())
    print(NASIB.to_string(index=False))
    print(KB[["participant_id", "kanal_buruk_rekaman"]].to_string(index=False))


def tahap4(pids):
    """Tahap 4: lonjakan artefak gerak (ASR / ambang adaptif / tandai) di atas TE + A2."""
    out = HASIL / "tahap4_lonjakan"
    out.mkdir(parents=True, exist_ok=True)
    rujuk = kanal.robust
    R, REP, INFO, DIST = [], [], [], []
    for pid in pids:
        raw = data.muat_edf(pid)
        rep, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
        W = jendela.jendela(rep, tt)
        _, xf, datar, sf = kualitas.sinyal(raw)
        eTE = epoch.potong_TE(W, xf.shape[1] / sf)
        Wr = W[W.fase.isin(epoch.FASE_REPETISI)]
        ref0, _ = epoch.acuan(xf, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER, rujuk)
        for v in lonjakan.VARIAN:
            x, amb, info = xf, None, {}
            if v.startswith("T4_ASR"):
                x, info = lonjakan.asr(xf, datar, sf, W, int(v[6:]))
            elif v == "T4_adaptif":
                amb = lonjakan.ambang_adaptif(xf, datar, sf, W, rujuk)
                info = {f"ambang_{c}": round(float(a), 1) for c, a in zip(kanal.KANAL, amb)}
            ref, _ = epoch.acuan(x, datar, sf, W, epoch.E_PANJANG, epoch.E_GESER, rujuk, amb)
            est = epoch.estimasi(x, datar, sf, eTE, ref, "TE", rujuk, amb)
            rp = epoch.per_repetisi(est)
            R.append(epoch.ringkas(pid, Wr, {"TE": eTE}, est, rp).assign(varian=v))
            REP.append(rp.assign(participant_id=pid, varian=v))
            INFO.append(dict(participant_id=pid, varian=v, **info))
            # distorsi: perubahan power acuan Istirahat (potongan bersih) terhadap tanpa koreksi, dB
            DIST.append(dict(participant_id=pid, varian=v, **{
                f"istirahat_{b}_db": round(float(np.nanmedian(10 * np.log10(ref[b] / ref0[b]))), 2)
                for b in ("theta", "mu", "beta", "otot")}))
        print(f"[{pid}] selesai; kalibrasi ASR {INFO[-4]}")
    R = pd.concat(R)
    R.to_csv(out / "ringkasan_varian_fase.csv", index=False)
    pd.DataFrame(INFO).to_csv(out / "info_varian.csv", index=False)
    pd.DataFrame(DIST).to_csv(out / "distorsi_istirahat.csv", index=False)
    pd.concat(REP).round(3).to_csv(out / "estimasi_per_repetisi.csv", index=False)
    grafik.tahap_varian(R, out / "tahap4_lonjakan.png", grafik.T4_WARNA,
                        "Tahap 4 — lonjakan artefak gerak (epoch TE, referensi A2)")
    pd.set_option("display.width", 250)
    kol = ["pct_kanal_epoch_bersih", "otot_db_median", "detik_bersih_median_kanal", "pct_kanal_rep_valid_ge3",
           "se_db_median", "reliabilitas_belah_dua"]
    print(R.groupby(["fase", "varian"], sort=False)[kol].median().round(2).to_string())
    print(pd.DataFrame(DIST).to_string(index=False))


def semua_pid():
    """Partisipan yang punya EDF Trial DAN timestamp manual."""
    ts = {p.name.split("_")[0] for p in data.TIMESTAMP.glob("P*_timestamps.csv")}
    edf = {p.name for p in data.RAW.glob("P*") if list(p.glob("*Trial*.[Ee][Dd][Ff]"))}
    return sorted(ts & edf), sorted(ts ^ edf)


def verifikasi_beku(pids):
    """Verifikasi rencana beku (RENCANA_BEKU.md): lolos/gagal K0–K5 per partisipan + ringkasan kohort."""
    out = HASIL / "verifikasi"
    out.mkdir(parents=True, exist_ok=True)
    if not pids or pids == ["semua"]:
        pids, tak_lengkap = semua_pid()
        if tak_lengkap:
            print(f"hanya punya EDF atau timestamp saja (dilewati): {tak_lengkap}")
    rows, H = [], []
    for pid in pids:
        try:
            r, h = verifikasi.evaluasi(pid)
        except Exception as e:                      # dicatat, tidak menghentikan kohort
            r, h = dict(participant_id=pid, K0_data=False, masalah_timestamp=f"GALAT: {e}"), None
        rows.append(r)
        if h is not None:
            H.append(h)
        print(f"[{pid}] " + " ".join(f"{k.split('_')[0]}={'ya' if r.get(k) else 'TIDAK'}"
                                    for k in verifikasi.KRITERIA))
    P = pd.DataFrame(rows)
    for k in verifikasi.KRITERIA:
        P[k] = P.get(k, False)
        P[k] = P[k].fillna(False).astype(bool)
    peserta = None
    for f in (data.ROOT / "data" / "participants.csv", data.ROOT / "hasil_analisis" / "participants.csv"):
        if f.exists():
            peserta = pd.read_csv(f)
            break
    K = verifikasi.kohort(P, peserta)
    P.to_csv(out / "lolos_gagal_per_partisipan.csv", index=False)
    K.to_csv(out / "ringkasan_kohort.csv", index=False)
    if H:
        pd.concat(H).to_csv(out / "ukuran_per_varian_fase.csv", index=False)
    verifikasi.laporan(P, K, out / "LAPORAN.md")
    pd.set_option("display.width", 250)
    print(K.to_string(index=False))


if __name__ == "__main__":
    cmd, *pids = sys.argv[1:]
    {"tahap1": tahap1, "epoch": epoch_banding, "bagian": bagian, "tahap2": tahap2, "tahap3": tahap3, "tahap4": tahap4, "verifikasi": verifikasi_beku}[cmd](pids or ["P08", "P09", "P31", "P32"])
