"""Kohort SIMULASI untuk mendemonstrasikan analisis grup (Paper A/B/D) sebelum data riil
lengkap. SEMUA baris is_simulated=True dan laporan diberi label [SIMULATED RESULTS].
Besaran efek di sini KARANGAN untuk demo, BUKAN hipotesis atau hasil."""
import numpy as np
import pandas as pd


def cohort(n_dancer=24, n_non=14, seed=7):
    rng = np.random.default_rng(seed)
    rng_age = np.random.default_rng(seed + 1)
    rows = []

    def one(pid, group, age, timepoint, shift=0.0, trait=None):
        trait = trait if trait is not None else rng.normal(0, 1)
        d = group == "penari"
        erd_beta = -40 - 15 * d - 12 * shift + 8 * trait - 0.08 * (age - 40) + rng.normal(0, 6)
        r = dict(participant_id=pid, group=group, age=round(age), timepoint=timepoint)
        # pola fase KARANGAN: ERD mulai pra-gerak, terkuat saat TAHAN
        for ph, w in [("PRA", 0.35), ("TURUN", 0.7), ("TAHAN", 1.0), ("NAIK", 0.6)]:
            base = w * (erd_beta + 5)
            r[f"erd_beta_{ph}"] = base + rng.normal(0, 7)
            r[f"erd_mu_{ph}"] = base - 10 * w + rng.normal(0, 7)
            r[f"theta_front_{ph}"] = w * (15 + 10 * d + 5 * shift) + rng.normal(0, 12)
            r[f"li_mu_{ph}"] = w * (0.10 + 0.12 * d + 0.06 * shift) + rng.normal(0, 0.12)
        r.update(
                 alpha_occ_EC=0.28 + 0.05 * d - 0.002 * (age - 40) + rng.normal(0, 0.06),
                 alpha_reactivity_EC_EO=1.9 + 0.4 * d - 0.006 * (age - 40) + rng.normal(0, 0.4),
                 mu_sm_EC=0.20 + 0.03 * d + rng.normal(0, 0.05),
                 mu_sm_EO=0.15 + 0.03 * d + rng.normal(0, 0.05),
                 theta_front_EC=0.18 - 0.02 * d + 0.001 * (age - 40) + rng.normal(0, 0.04),
                 theta_alpha_ratio_EC=0.9 - 0.15 * d + rng.normal(0, 0.2),
                 iaf_occ_EC=10.2 - 0.02 * (age - 40) + rng.normal(0, 0.5),
                 stork_time_sec=max(1.0, 22 + 12 * d - 0.15 * (age - 40) + 4 * shift
                                    + rng.normal(0, 7)),
                 is_simulated=True)
        r["erd_beta_TAHAN_odd"] = r["erd_beta_TAHAN"] + rng.normal(0, 7)
        r["erd_beta_TAHAN_even"] = r["erd_beta_TAHAN"] + rng.normal(0, 7)
        return r

    ages = np.clip(np.concatenate([rng_age.normal(32, 12, n_dancer - 1), [78]]), 15, 102)
    for i, a in enumerate(ages):
        rows.append(one(f"S{i + 1:02d}", "penari", a, "pre"))
    ages = np.clip(np.concatenate([rng_age.normal(35, 12, n_non - 1), [102]]), 15, 102)
    for i, a in enumerate(ages):
        pid, trait = f"S{n_dancer + i + 1:02d}", rng.normal(0, 1)
        rows.append(one(pid, "non-penari", a, "pre", 0.0, trait))
        rows.append(one(pid, "non-penari", a, "post", 1.0, trait))   # 6 minggu latihan
    return pd.DataFrame(rows)
