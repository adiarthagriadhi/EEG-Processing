"""Romberg (Buka Mata vs Tutup Mata): efek Berger dengan specparam dan tiga referensi, set penyetelan.
Pipeline sama sampai ASR k 20 (sebelum referensi). Jendela 1 dtk geser 0,25 (aturan.potong_mata); bersih = tidak datar
dan ptp ≤ 150 µV; ≥ 8 jendela bersih per kondisi. Spektrum kondisi = rata-rata power linear jendela bersih, lalu
rata-rata kanal area.
Ukuran: M0 = 10·log10(alpha 8–13 Tutup / Buka); SP = puncak periodik alpha specparam (dB di atas garis aperiodik,
maks 8–13 Hz), Tutup − Buka; ada_puncak = specparam menemukan puncak 7–14 Hz. IK 95% bootstrap blok (4 jendela), 300×."""
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.signal import welch

sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
from fooof import FOOOF  # noqa: E402

from gerakeeg import aturan, data, epoch, jendela, kanal, kualitas, lonjakan  # noqa: E402
from gerakeeg.istilah import BUKA_MATA, TUTUP_MATA  # noqa: E402
from gerakeeg.referensi import nama  # noqa: E402

PID = ["P08", "P09", "P31", "P32"]
F = np.arange(1, 35)
SKEMA = {"A2_belahan_robust": kanal.robust, "D_telinga": "D_telinga", "C_bipolar": "C_bipolar"}
AREA = {"oksipital": {"A2_belahan_robust": ["O1", "O2"], "D_telinga": ["O1", "O2"], "C_bipolar": ["P3-O1", "P4-O2"]},
        "parietal": {"A2_belahan_robust": ["P3", "P4"], "D_telinga": ["P3", "P4"], "C_bipolar": ["C3-P3", "C4-P4"]},
        "sentral": {"A2_belahan_robust": ["C3", "C4"], "D_telinga": ["C3", "C4"], "C_bipolar": ["F3-C3", "F4-C4"]}}
rng = np.random.default_rng(0)


def fooof_alpha(p):
    sel = (F >= 2) & (F <= 30)
    m = FOOOF(peak_width_limits=[1, 6], max_n_peaks=4, aperiodic_mode="fixed", verbose=False)
    m.fit(F[sel].astype(float), p[sel], [2, 30])
    flat = 10 * (np.log10(p[sel]) - m._ap_fit)
    ff = F[sel]
    pk = [cf for cf, _, _ in m.peak_params_ if 7 <= cf <= 14]
    return flat[(ff >= 8) & (ff <= 13)].max(), bool(pk), (pk[0] if pk else np.nan)


def alpha(p):
    return p[(F >= 8) & (F < 14)].mean()


rows = []
for pid in PID:
    raw = data.muat_edf(pid)
    rp, tt, _ = jendela.repetisi(data.muat_timestamp(pid))
    W = jendela.jendela(rp, tt)
    _, xf, datar, sf = kualitas.sinyal(raw)
    xa, _ = lonjakan.asr(xf, datar, sf, W, 20)
    ep = aturan.potong_mata(W, xf.shape[1] / sf)
    for sk, fn in SKEMA.items():
        nm = nama(sk if isinstance(fn, str) else None)
        spek = {BUKA_MATA: [], TUTUP_MATA: []}
        oks = {BUKA_MATA: [], TUTUP_MATA: []}
        for e in ep.itertuples():
            i0, i1 = int(round(e.mulai * sf)), int(round(e.selesai * sf))
            if i1 > xa.shape[1]:
                continue
            x, _, ok = epoch._potong(xa, datar, i0, i1, fn)
            f, p = welch(x, sf, nperseg=int(sf))
            spek[e.fase].append(p[:, np.isin(f, F)])
            oks[e.fase].append(ok)
        for area, chs in AREA.items():
            idx = [nm.index(c) for c in chs[sk]]
            per = {}
            for kond in (BUKA_MATA, TUTUP_MATA):
                P, O = np.array(spek[kond]), np.array(oks[kond])
                okw = O[:, idx].all(axis=1) if len(O) else np.array([], bool)
                per[kond] = P[okw][:, idx].mean(axis=1) if okw.sum() else np.empty((0, len(F)))
            n_b, n_t = len(per[BUKA_MATA]), len(per[TUTUP_MATA])
            r = dict(participant_id=pid, referensi=sk, area=area, n_buka=n_b, n_tutup=n_t)
            if min(n_b, n_t) >= 8:
                mb, mt = per[BUKA_MATA].mean(axis=0), per[TUTUP_MATA].mean(axis=0)
                sb, pb, cb = fooof_alpha(mb)
                st, pt, ct = fooof_alpha(mt)
                r.update(M0_tutup_minus_buka_db=10 * np.log10(alpha(mt) / alpha(mb)),
                         SP_buka_db=sb, SP_tutup_db=st, SP_tutup_minus_buka_db=st - sb,
                         puncak_buka=pb, puncak_tutup=pt, frek_puncak_tutup=ct)
                bM, bS = [], []
                for _ in range(300):
                    bb = []
                    for v in (per[BUKA_MATA], per[TUTUP_MATA]):
                        blk = [v[i:i + 4] for i in range(0, len(v) - 3, 4)]
                        bb.append(np.concatenate([blk[i] for i in rng.integers(0, len(blk), len(blk))]).mean(axis=0))
                    bM.append(10 * np.log10(alpha(bb[1]) / alpha(bb[0])))
                    bS.append(fooof_alpha(bb[1])[0] - fooof_alpha(bb[0])[0])
                r.update(M0_ik_bawah=np.percentile(bM, 2.5), M0_ik_atas=np.percentile(bM, 97.5),
                         SP_ik_bawah=np.percentile(bS, 2.5), SP_ik_atas=np.percentile(bS, 97.5))
            rows.append(r)
    print(pid, flush=True)
D = pd.DataFrame(rows).round(2)
D.to_csv("hasil/pilot_analisis/romberg_referensi_specparam.csv", index=False)
pd.set_option("display.width", 250)
print(D.drop(columns=["SP_buka_db", "SP_tutup_db"]).to_string(index=False))
