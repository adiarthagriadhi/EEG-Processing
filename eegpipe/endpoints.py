"""Ringkasan tingkat partisipan (satu baris per partisipan × timepoint) dari
results/PXX_*.csv. Endpoint ERD utama = fase TAHAN (Pertanyaan 14, default)."""
import numpy as np
import pandas as pd

CONTRA = {"AGEM KANAN": "C3", "AGEM KIRI": "C4"}     # asumsi pemetaan sisi (Pertanyaan 8)


PHASES = ["PRA", "TURUN", "TAHAN", "NAIK", "POST"]


def participant_endpoints(erd, li, romberg):
    """Semua fase dimasukkan (permintaan pengguna: 'masukkan semua, lihat polanya')."""
    out = {}
    e = erd[erd.task.isin(CONTRA)]
    contra = e[e.apply(lambda r: r.channel == CONTRA[r.task], axis=1)] if len(e) else e
    for ph in PHASES:
        c = contra[contra.phase == ph]
        for band in ("mu", "beta"):
            out[f"erd_{band}_{ph}"] = c[c.band == band].erd_pct.median()
        th = e[(e.phase == ph) & (e.band == "theta") & e.channel.isin(["F3", "F4"])]
        out[f"theta_front_{ph}"] = th.erd_pct.median() if len(th) else np.nan
        if li is not None and len(li):
            out[f"li_mu_{ph}"] = li[(li.phase == ph) & (li.band == "mu")].li_erd.median()
    b = contra[(contra.phase == "TAHAN") & (contra.band == "beta")]
    out["erd_beta_TAHAN_odd"] = b[b.rep % 2 == 1].erd_pct.median()      # split-half (RCI)
    out["erd_beta_TAHAN_even"] = b[b.rep % 2 == 0].erd_pct.median()
    if romberg is not None:
        for k in ("alpha_occ_EC", "alpha_reactivity_EC_EO", "mu_sm_EC", "mu_sm_EO",
                  "theta_front_EC", "theta_alpha_ratio_EC", "iaf_occ_EC"):
            out[k] = romberg.get(k, np.nan)
    return out


def collect(results_dir, participants):
    """Gabungkan semua partisipan yang punya results/PXX_erd_ers.csv."""
    rows = []
    for f in sorted(results_dir.glob("*_erd_ers.csv")):
        pid = f.name.split("_erd_ers")[0]
        erd = pd.read_csv(f)
        lif = results_dir / f"{pid}_li.csv"
        rbf = results_dir / f"{pid}_romberg_features.csv"
        row = participant_endpoints(erd, pd.read_csv(lif) if lif.exists() else None,
                                    pd.read_csv(rbf).iloc[0].to_dict() if rbf.exists() else None)
        row.update(participant_id=pid, is_simulated=bool(erd.is_simulated.iloc[0]))
        rows.append(row)
    df = pd.DataFrame(rows)
    if participants is not None and len(df):
        df = df.merge(participants, on="participant_id", how="left")
    return df
