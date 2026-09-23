"""Kohort SINTETIS yang diturunkan dari partisipan riil (template per grup).

Nilai pusat tiap grup = endpoint partisipan template (mis. P02 → penari, P10 →
non-penari); sebaran antar-partisipan = SD antar-repetisi partisipan riil (ERD, dalam
skala log-rasio agar nilai tidak < −100%). Semua baris is_simulated=True. Stork Test
belum tersedia → nilai HIPOTETIS (kolom stork_is_hypothetical=True).
Hasil statistik dari kohort ini TIDAK BOLEH dikutip sebagai temuan."""
import numpy as np
import pandas as pd

from .endpoints import CONTRA, PHASES, collect

ROMBERG = ["alpha_occ_EC", "alpha_reactivity_EC_EO", "mu_sm_EC", "mu_sm_EO",
           "theta_front_EC", "theta_alpha_ratio_EC"]


def _log(x):
    return np.log1p(np.asarray(x, float) / 100)


def _unlog(z):
    return (np.expm1(z)) * 100


def rep_sd(results_dir, pids):
    """SD antar-repetisi (log-rasio) per ukuran×fase, digabung dari partisipan riil."""
    out = {}
    for pid in pids:
        e = pd.read_csv(results_dir / f"{pid}_erd_ers.csv")
        e = e[e.task.isin(CONTRA)]
        c = e[e.apply(lambda r: r.channel == CONTRA[r.task], axis=1)]
        th = e[(e.band == "theta") & e.channel.isin(["F3", "F4"])]
        for ph in PHASES:
            for band in ("mu", "beta"):
                v = _log(c[(c.phase == ph) & (c.band == band)].erd_pct.clip(lower=-99))
                out.setdefault(f"erd_{band}_{ph}", []).append(np.nanstd(v))
            v = _log(th[th.phase == ph].erd_pct.clip(lower=-99))
            out.setdefault(f"theta_front_{ph}", []).append(np.nanstd(v))
    return {k: float(np.nanmean(v)) for k, v in out.items()}


def to_db(erd_pct):
    """%ERD/ERS → dB (10·log10 rasio power); simetris, untuk statistik grup."""
    return 10 * np.log10(1 + np.asarray(erd_pct, float) / 100)


def cohort(results_dir, templates, participants=None, n=None, seed=11):
    """templates: {'penari': 'P02', 'non-penari': 'P10'}; n: {'penari': 24, ...}."""
    rng = np.random.default_rng(seed)
    n = n or {"penari": 24, "non-penari": 14}
    real = collect(results_dir, participants).set_index("participant_id")
    sd = rep_sd(results_dir, list(templates.values()))
    rows, k = [], 0
    for group, pid in templates.items():
        tpl = real.loc[pid]
        ages = np.clip(rng.normal(34, 13, n[group] - 1), 15, 90).tolist() + \
            [78.0 if group == "penari" else 102.0]
        for a in ages:
            k += 1
            r = dict(participant_id=f"SIM{k:02d}", group=group, timepoint="pre",
                     age=round(a), template=pid, is_simulated=True)
            for key, s in sd.items():
                # sebaran antar-partisipan = galat median 4 repetisi (s/√4) + variasi antar
                # individu yang diasumsikan sama besar → s/√2
                m = _log(max(tpl.get(key, np.nan), -99))
                r[key] = float(_unlog(m + rng.normal(0, s / np.sqrt(2)))) if np.isfinite(m) else np.nan
            for key in ROMBERG:
                v = tpl.get(key, np.nan)
                r[key] = float(v * np.exp(rng.normal(0, 0.3))) if np.isfinite(v) else np.nan
            # Stork Test: HIPOTETIS (belum ada data) — penari lebih lama, menurun dgn usia
            base = 35 if group == "penari" else 20
            r["stork_time_sec"] = max(2.0, base - 0.15 * (a - 35) + rng.normal(0, 8))
            r["stork_is_hypothetical"] = True
            # kualitas data per partisipan (dari rentang dua partisipan riil)
            r["sync_offset_sec"] = rng.normal(0.8, 0.15)
            r["n_bad_channels"] = int(rng.choice([1, 2]))
            r["romberg_ec_coverage"] = float(rng.uniform(0.13, 0.55))
            r["hold_agem_sec"] = float(np.exp(rng.normal(np.log(2.84 if group == "penari"
                                                                  else 0.94), 0.3)))
            rows.append(r)
    return pd.DataFrame(rows)
