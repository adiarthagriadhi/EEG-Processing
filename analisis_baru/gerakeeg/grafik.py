"""Grafik tahap 1 (PNG). Warna: status (ok/tinggi/ekstrem) + abu-abu untuk data hilang; biru berurutan untuk %;
biru/oranye untuk repo vs metode baru. Teks selalu memakai tinta teks, bukan warna seri."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from .istilah import KANAL, LABEL_FASE, URUTAN_FASE

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
STATUS = {"ok": ("#0ca30c", "ok (≤ 100 µV)"), "tinggi": ("#fab219", "tinggi (100–150 µV)"),
          "ekstrem": ("#d03b3b", "ekstrem (> 150 µV)"), "datar": ("#a9a8a2", "datar (sinyal hilang)")}
BIRU = LinearSegmentedColormap.from_list("biru", ["#cde2fb", "#86b6ef", "#2a78d6", "#1c5cab", "#0d366b"])
REPO, BARU = "#2a78d6", "#eb6834"

plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": GRID, "font.size": 9})


def _rapikan(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def komposisi(rs, path, judul):
    """Batang bertumpuk horizontal: % potongan 1 dtk × kanal per status, per fase; satu panel per partisipan."""
    pids = sorted(rs.participant_id.unique())
    fig, axes = plt.subplots(1, len(pids), figsize=(3.3 * len(pids), 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    fases = [f for f in URUTAN_FASE if f in set(rs.fase)]
    for ax, pid in zip(axes, pids):
        g = rs[rs.participant_id == pid].set_index("fase").reindex(fases)
        y = np.arange(len(fases))[::-1]
        kiri = np.zeros(len(fases))
        for st, (col, _) in STATUS.items():
            v = g[f"pct_{st}"].fillna(0).values
            ax.barh(y, v, left=kiri, color=col, height=0.62, edgecolor=SURFACE, linewidth=2)
            kiri += v
        for yi, v in zip(y, g.pct_ok.fillna(0).values):
            ax.text(101, yi, f"{v:.0f}%", va="center", ha="left", fontsize=8, color=INK)
        ax.set_yticks(y, [LABEL_FASE[f] for f in fases])
        ax.set_xlim(0, 114)
        ax.set_xticks([0, 50, 100], ["0", "50", "100%"])
        ax.set_title(pid, fontsize=10, loc="left", color=INK)
        _rapikan(ax)
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for c, _ in STATUS.values()]
    fig.legend(h, [l for _, l in STATUS.values()], loc="upper left", ncol=4, frameon=False,
               bbox_to_anchor=(0.01, 1.02), fontsize=8)
    fig.suptitle(judul, x=0.01, y=1.10, ha="left", fontsize=11, color=INK)
    fig.text(0.01, -0.04, "Angka di kanan = % ok. *Istirahat = jeda antar-blok (turunan, tanpa timestamp), dipakai "
             "sebagai acuan.", fontsize=7.5, color=INK2)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def peta_kanal(pot, path, judul):
    """Peta kanal × fase: % potongan ok, satu panel per partisipan (biru berurutan)."""
    pids = sorted(pot.participant_id.unique())
    fases = [f for f in URUTAN_FASE if f in set(pot.fase)]
    fig, axes = plt.subplots(1, len(pids), figsize=(2.9 * len(pids), 5.2), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, pid in zip(axes, pids):
        g = pot[pot.participant_id == pid]
        M = (g.assign(ok=g.label == "ok").pivot_table(index="kanal", columns="fase", values="ok", aggfunc="mean")
             .reindex(index=KANAL, columns=fases) * 100)
        im = ax.imshow(M.values, vmin=0, vmax=100, cmap=BIRU, aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M.values[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                            color="white" if v > 55 else INK)
        ax.axhline(7.5, color=SURFACE, lw=3)
        ax.set_xticks(range(len(fases)), [LABEL_FASE[f] for f in fases], rotation=40, ha="right", fontsize=7.5)
        ax.set_yticks(range(len(KANAL)), KANAL, fontsize=7.5)
        ax.set_title(pid, fontsize=10, loc="left")
        _rapikan(ax)
    cb = fig.colorbar(im, ax=axes, shrink=0.6, pad=0.02)
    cb.set_label("% potongan 1 dtk ok", color=INK2)
    cb.outline.set_visible(False)
    fig.suptitle(judul, x=0.01, ha="left", fontsize=11)
    fig.text(0.01, -0.06, "Atas garis putih: belahan kiri (referensi A1); bawah: kanan (A2). "
             "*Istirahat = jeda antar-blok (turunan).", fontsize=7.5, color=INK2)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def banding(rb, path, judul):
    """% ok per fase: analisis repo (video/pose) vs metode baru (timestamp manual), per partisipan."""
    pids = sorted(rb.participant_id.unique())
    fases = ["Gerak", "Tahan", "Naik"]
    fig, axes = plt.subplots(1, len(pids), figsize=(3.0 * len(pids), 2.6), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, pid in zip(axes, pids):
        g = rb[rb.participant_id == pid].set_index(["sumber", "fase"])
        y = np.arange(len(fases))[::-1]
        for yi, f in zip(y, fases):
            a, b = g.pct_ok.get(("repo_video", f), np.nan), g.pct_ok.get(("timestamp_manual", f), np.nan)
            ax.plot([a, b], [yi, yi], color=GRID, lw=2, zorder=1)
            ax.scatter([a], [yi], s=90, facecolor=SURFACE, edgecolor=REPO, linewidth=2.2, zorder=2)
            ax.scatter([b], [yi], s=38, color=BARU, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.set_yticks(y, [LABEL_FASE[f] for f in fases])
        ax.set_xlim(0, 60)
        ax.set_ylim(-0.6, len(fases) - 0.4)
        ax.set_xticks([0, 20, 40, 60], ["0", "20", "40", "60%"])
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.set_title(pid, fontsize=10, loc="left")
        _rapikan(ax)
    h = [plt.Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=REPO, markeredgewidth=2,
                    markersize=9),
         plt.Line2D([], [], marker="o", ls="", color=BARU, markersize=6)]
    fig.legend(h, ["analisis repo (fase dari video/pose, offset repo)", "metode baru (timestamp manual, −0,5 dtk)"],
               loc="upper left", ncol=2, frameon=False, bbox_to_anchor=(0.01, 1.04), fontsize=8)
    fig.suptitle(judul, x=0.01, y=1.14, ha="left", fontsize=11)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


METODE = {"B": ("#2a78d6", "B: tetap 1,5 dtk dari onset − 0,5"),
          "T": ("#1baf7a", "T: terarah 1,5 dtk di bagian informatif"),
          "TE": ("#4a3aa7", "TE: jendela geser di bagian informatif"),
          "E": ("#eb6834", "E: jendela geser 1 dtk berlabel fase")}


def epoch_banding(R, path):
    """Lima ukuran per fase untuk tiap metode; titik = partisipan, garis tipis menghubungkan metode per partisipan."""
    from .istilah import FASE_REPETISI
    ukuran = [("detik_bersih_median_kanal", "Detik data bersih\nper kanal (median)", None),
              ("otot_db_median", "Kontaminasi otot 20–34 Hz\n(dB vs Istirahat; kecil = baik)", None),
              ("pct_kanal_rep_valid_ge3", "% kanal dengan ≥ 3\nrepetisi bersih", (-5, 105)),
              ("se_db_median", "Galat baku power\n(dB; kecil = presisi)", None),
              ("reliabilitas_belah_dua", "Reliabilitas belah-dua\n(pola kanal × pita)", (-0.8, 1.05))]
    met = [m for m in METODE if m in set(R.metode)]
    off = dict(zip(met, np.linspace(-0.22, 0.22, len(met))))
    fig, axes = plt.subplots(1, len(ukuran), figsize=(16, 3.6))
    x = np.arange(len(FASE_REPETISI))
    for ax, (col, lab, lim) in zip(axes, ukuran):
        for pid, g in R.groupby("participant_id"):
            V = {m: g[g.metode == m].set_index("fase").reindex(FASE_REPETISI)[col].values for m in met}
            for i in range(len(x)):
                ax.plot([x[i] + off[m] for m in met], [V[m][i] for m in met], color=GRID, lw=1, zorder=1)
            for m in met:
                ax.scatter(x + off[m], V[m], s=26, color=METODE[m][0], edgecolor=SURFACE, linewidth=1, zorder=3)
        for m in met:                                            # median antar-partisipan
            md = R[R.metode == m].groupby("fase")[col].median().reindex(FASE_REPETISI).values
            ax.scatter(x + off[m], md, s=120, marker="_", color=INK, linewidth=2, zorder=4)
        ax.set_xticks(x, FASE_REPETISI, fontsize=8)
        ax.set_title(lab, fontsize=9, loc="left", color=INK)
        if lim:
            ax.set_ylim(*lim)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        _rapikan(ax)
    h = [plt.Line2D([], [], marker="o", ls="", color=METODE[m][0], markersize=6) for m in met]
    h.append(plt.Line2D([], [], marker="_", ls="", color=INK, markersize=12, markeredgewidth=2))
    fig.legend(h, [METODE[m][1] for m in met] + ["median 4 partisipan"], loc="upper left", ncol=5, frameon=False,
               bbox_to_anchor=(0.01, 1.07), fontsize=8)
    fig.suptitle("Epoching B vs T vs TE vs E — per fase, 4 partisipan, sebelum koreksi artefak", x=0.01,
                 y=1.15, ha="left", fontsize=11)
    fig.text(0.01, -0.04, "Gerak dan Naik: B dan T identik (keduanya inisiasi). Titik hilang = < 3 repetisi bersih.",
             fontsize=7.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


PESERTA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


def profil_bagian(R, path):
    """Profil per bagian fase (pra-onset/awal/tengah/akhir): baris = ukuran, kolom = fase; garis per partisipan
    (label langsung) + median (tinta tebal)."""
    from .istilah import FASE_REPETISI
    from .posisi import BAGIAN
    uk = [("pct_bersih_05dtk", "% potongan 0,5 dtk bersih", None),
          ("otot_db", "Otot 20–34 Hz (dB vs Istirahat)", None),
          ("mu_sm_db", "Mu C3/C4 (dB vs Istirahat;\n< 0 = ERD)", None),
          ("beta_sm_db", "Beta C3/C4 (dB vs Istirahat;\n< 0 = ERD)", None)]
    pids = sorted(R.participant_id.unique())
    fig, axes = plt.subplots(len(uk), len(FASE_REPETISI), figsize=(12.5, 10), sharey="row")
    x = np.arange(len(BAGIAN))
    for i, (col, lab, _) in enumerate(uk):
        for j, f in enumerate(FASE_REPETISI):
            ax = axes[i, j]
            g = R[R.fase == f]
            for c, pid in zip(PESERTA, pids):
                v = g[g.participant_id == pid].set_index("bagian").reindex(BAGIAN)[col].values
                ax.plot(x, v, color=c, lw=1.6, marker="o", markersize=4.5, markeredgecolor=SURFACE, zorder=2)
                if j == len(FASE_REPETISI) - 1 and np.isfinite(v[-1]):
                    ax.annotate(pid, (x[-1], v[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                                fontsize=7, color=INK2)
            med = g.groupby("bagian", observed=False)[col].median().reindex(BAGIAN).values
            ax.plot(x, med, color=INK, lw=2.6, zorder=3)
            if col != "pct_bersih_05dtk":
                ax.axhline(0, color=INK2, lw=0.8, ls=(0, (3, 3)), zorder=1)
            ax.set_xticks(x, BAGIAN if i == len(uk) - 1 else [""] * len(BAGIAN), fontsize=8, rotation=0)
            if i == 0:
                ax.set_title(f, fontsize=10.5, loc="left", color=INK)
            if j == 0:
                ax.set_ylabel(lab, fontsize=8.5)
            ax.grid(axis="y", color=GRID, lw=0.6)
            ax.set_axisbelow(True)
            _rapikan(ax)
    h = [plt.Line2D([], [], color=c, lw=1.6, marker="o", markersize=4.5) for c in PESERTA[:len(pids)]]
    h.append(plt.Line2D([], [], color=INK, lw=2.6))
    fig.legend(h, pids + ["median"], loc="upper left", ncol=5, frameon=False, bbox_to_anchor=(0.01, 1.035),
               fontsize=8.5)
    fig.suptitle("Bagian fase mana yang paling informatif? (sebelum koreksi artefak)", x=0.01, y=1.06, ha="left",
                 fontsize=11.5)
    fig.text(0.01, -0.015, "pra-onset = 0,5 dtk sebelum timestamp; awal/tengah/akhir = sepertiga fase. Jendela 1 dtk "
             "(otot, mu, beta) dimasukkan menurut pusatnya, jadi bagian bertetangga pada fase pendek bercampur.",
             fontsize=7.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=125, bbox_inches="tight")
    plt.close(fig)


SKEMA_WARNA = {"D_telinga": ("#2a78d6", "D telinga A1/A2 (asli)"), "A_belahan": ("#eb6834", "A rata-rata per belahan"),
               "B_rata16": ("#1baf7a", "B rata-rata 16 kanal"), "C_bipolar": ("#4a3aa7", "C bipolar tetangga")}


def tahap2(R, K, BG, path):
    """Baris 1: % kanal bersih, otot, reliabilitas per fase; baris 2: korelasi dalam belahan, antar belahan,
    efek Berger. Titik = partisipan; garis hitam pendek = median."""
    from .istilah import FASE_REPETISI
    sk = [s for s in SKEMA_WARNA if s in set(R.skema)]
    off = dict(zip(sk, np.linspace(-0.27, 0.27, len(sk))))
    x = np.arange(len(FASE_REPETISI))
    panel = [(R, "pct_kanal_epoch_bersih", "% kanal-jendela bersih", None),
             (R, "otot_db_median", "Otot 20–34 Hz (dB vs Istirahat)", None),
             (R, "reliabilitas_belah_dua", "Reliabilitas belah-dua", (-0.8, 1.05)),
             (K, "r_kiri_kanan", "Korelasi DALAM belahan\n(rata-rata kiri & kanan)", (-0.3, 1.0)),
             (K, "r_antar", "Korelasi ANTAR belahan", (-0.6, 0.6))]
    K = K.assign(r_kiri_kanan=K[["r_kiri", "r_kanan"]].mean(axis=1))
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.2))
    axes = axes.ravel()
    for ax, (D, col, lab, lim) in zip(axes, panel):
        D = K if D is not R else R
        for s in sk:
            g = D[D.skema == s]
            for pid, gp in g.groupby("participant_id"):
                v = gp.set_index("fase").reindex(FASE_REPETISI)[col].values
                ax.scatter(x + off[s], v, s=20, color=SKEMA_WARNA[s][0], edgecolor=SURFACE, linewidth=0.8, zorder=3)
            md = g.groupby("fase")[col].median().reindex(FASE_REPETISI).values
            ax.scatter(x + off[s], md, s=110, marker="_", color=INK, linewidth=2, zorder=4)
        ax.set_xticks(x, FASE_REPETISI, fontsize=8.5)
        ax.set_title(lab, fontsize=9.5, loc="left")
        if lim:
            ax.set_ylim(*lim)
        if col in ("otot_db_median", "r_antar"):
            ax.axhline(0, color=INK2, lw=0.8, ls=(0, (3, 3)))
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        _rapikan(ax)
    ax = axes[5]
    xs = np.arange(len(sk))
    for i, s in enumerate(sk):
        v = BG[BG.skema == s].berger_alpha_rel_db.values
        ax.scatter(np.full(len(v), i), v, s=26, color=SKEMA_WARNA[s][0], edgecolor=SURFACE, zorder=3)
        ax.scatter([i], [np.nanmedian(v)], s=160, marker="_", color=INK, linewidth=2, zorder=4)
    ax.axhline(0, color=INK2, lw=0.8, ls=(0, (3, 3)))
    ax.set_xticks(xs, [s.split("_")[0] for s in sk])
    ax.set_title("Efek Berger: alpha RELATIF oksipital\nTutup Mata vs Istirahat (dB; > 0 = sesuai)", fontsize=9.5,
                 loc="left")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    _rapikan(ax)
    h = [plt.Line2D([], [], marker="o", ls="", color=SKEMA_WARNA[s][0], markersize=6) for s in sk]
    h.append(plt.Line2D([], [], marker="_", ls="", color=INK, markersize=12, markeredgewidth=2))
    fig.legend(h, [SKEMA_WARNA[s][1] for s in sk] + ["median 4 partisipan"], loc="upper left", ncol=5,
               frameon=False, bbox_to_anchor=(0.01, 1.04), fontsize=8.5)
    fig.suptitle("Tahap 2 — skema referensi, dinilai dengan epoch TE (sebelum koreksi artefak lain)", x=0.01, y=1.08,
                 ha="left", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(path, dpi=125, bbox_inches="tight")
    plt.close(fig)


VARIAN_WARNA = {"A0_dasar": ("#2a78d6", "A0 dasar (Tahap 2)"), "A1_rekaman": ("#eb6834", "A1 kanal buruk per rekaman"),
                "A2_robust": ("#1baf7a", "A2 robust per jendela"), "A3_median": ("#eda100", "A3 referensi median"),
                "A4_robust_int": ("#4a3aa7", "A4 robust + interpolasi")}


def tahap3(R, path):
    from .istilah import FASE_REPETISI
    vs = [v for v in VARIAN_WARNA if v in set(R.varian)]
    off = dict(zip(vs, np.linspace(-0.3, 0.3, len(vs))))
    x = np.arange(len(FASE_REPETISI))
    panel = [("pct_kanal_epoch_bersih", "% kanal-jendela bersih", None),
             ("otot_db_median", "Otot 20–34 Hz (dB vs Istirahat)", None),
             ("detik_bersih_median_kanal", "Detik data bersih per kanal", None),
             ("se_db_median", "Galat baku power (dB)", None),
             ("reliabilitas_belah_dua", "Reliabilitas belah-dua", (-0.8, 1.05))]
    fig, axes = plt.subplots(1, len(panel), figsize=(17, 3.8))
    for ax, (col, lab, lim) in zip(axes, panel):
        for v in vs:
            g = R[R.varian == v]
            for pid, gp in g.groupby("participant_id"):
                y = gp.set_index("fase").reindex(FASE_REPETISI)[col].values
                ax.scatter(x + off[v], y, s=16, color=VARIAN_WARNA[v][0], edgecolor=SURFACE, linewidth=0.6, zorder=3)
            md = g.groupby("fase")[col].median().reindex(FASE_REPETISI).values
            ax.scatter(x + off[v], md, s=90, marker="_", color=INK, linewidth=2, zorder=4)
        ax.set_xticks(x, FASE_REPETISI, fontsize=8.5)
        ax.set_title(lab, fontsize=9.5, loc="left")
        if lim:
            ax.set_ylim(*lim)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        _rapikan(ax)
    h = [plt.Line2D([], [], marker="o", ls="", color=VARIAN_WARNA[v][0], markersize=6) for v in vs]
    h.append(plt.Line2D([], [], marker="_", ls="", color=INK, markersize=12, markeredgewidth=2))
    fig.legend(h, [VARIAN_WARNA[v][1] for v in vs] + ["median 4 partisipan"], loc="upper left", ncol=6,
               frameon=False, bbox_to_anchor=(0.01, 1.07), fontsize=8.5)
    fig.suptitle("Tahap 3 — kanal buruk & sinyal datar (referensi A, epoch TE)", x=0.01, y=1.15, ha="left",
                 fontsize=11.5)
    fig.tight_layout()
    fig.savefig(path, dpi=125, bbox_inches="tight")
    plt.close(fig)


T4_WARNA = {"T4_tandai": ("#2a78d6", "tandai saja (150 µV)"), "T4_ASR20": ("#eb6834", "ASR k = 20"),
            "T4_ASR10": ("#1baf7a", "ASR k = 10"), "T4_ASR5": ("#eda100", "ASR k = 5"),
            "T4_adaptif": ("#4a3aa7", "ambang adaptif per partisipan")}


def tahap_varian(R, path, warna, judul):
    """Lima panel ukuran per fase untuk varian dalam `warna` (kolom R.varian)."""
    from .istilah import FASE_REPETISI
    vs = [v for v in warna if v in set(R.varian)]
    off = dict(zip(vs, np.linspace(-0.3, 0.3, len(vs))))
    x = np.arange(len(FASE_REPETISI))
    panel = [("pct_kanal_epoch_bersih", "% kanal-jendela bersih", None),
             ("otot_db_median", "Otot 20–34 Hz (dB vs Istirahat)", None),
             ("detik_bersih_median_kanal", "Detik data bersih per kanal", None),
             ("se_db_median", "Galat baku power (dB)", None),
             ("reliabilitas_belah_dua", "Reliabilitas belah-dua", None)]
    fig, axes = plt.subplots(1, len(panel), figsize=(17, 3.8))
    for ax, (col, lab, lim) in zip(axes, panel):
        for v in vs:
            g = R[R.varian == v]
            for pid, gp in g.groupby("participant_id"):
                y = gp.set_index("fase").reindex(FASE_REPETISI)[col].values
                ax.scatter(x + off[v], y, s=16, color=warna[v][0], edgecolor=SURFACE, linewidth=0.6, zorder=3)
            md = g.groupby("fase")[col].median().reindex(FASE_REPETISI).values
            ax.scatter(x + off[v], md, s=90, marker="_", color=INK, linewidth=2, zorder=4)
        ax.set_xticks(x, FASE_REPETISI, fontsize=8.5)
        ax.set_title(lab, fontsize=9.5, loc="left")
        if lim:
            ax.set_ylim(*lim)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        _rapikan(ax)
    h = [plt.Line2D([], [], marker="o", ls="", color=warna[v][0], markersize=6) for v in vs]
    h.append(plt.Line2D([], [], marker="_", ls="", color=INK, markersize=12, markeredgewidth=2))
    fig.legend(h, [warna[v][1] for v in vs] + ["median 4 partisipan"], loc="upper left", ncol=len(vs) + 1,
               frameon=False, bbox_to_anchor=(0.01, 1.07), fontsize=8.5)
    fig.suptitle(judul, x=0.01, y=1.15, ha="left", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(path, dpi=125, bbox_inches="tight")
    plt.close(fig)


FASE_WARNA = {"Gerak": "#2a78d6", "Tahan": "#1baf7a", "Naik": "#eb6834", "Berdiri": "#eda100"}
MERAH = "#d03b3b"


def gelombang(pid, tahapan, datar, sf, W, TE, gerakan, rep, path, jarak_uv=120.0):
    """Gelombang 16 kanal satu repetisi (Gerak − 3 dtk … Gerak berikutnya + 1 dtk) untuk beberapa tahap proses.
    tahapan: [(judul, x kanal × sampel µV, fd kanal × sampel (≥ 0,1 = hilang))]. Potongan 1 dtk (grid 0,5 dtk) yang
    gagal aturan bersih (> 150 µV) digambar merah; bagian hilang tidak digambar."""
    from .istilah import FASE_REPETISI, KANAL
    w = W[(W.gerakan == gerakan) & (W.rep == rep)].set_index("fase")
    t0 = w.loc["Gerak", "onset"] - 3.0
    t1 = w.loc["Berdiri", "selesai"] + 1.0 if "Berdiri" in w.index else w.loc["Naik", "selesai"] + 3
    i0, i1 = int(t0 * sf), int(t1 * sf)
    t = np.arange(i0, i1) / sf
    n = len(tahapan)
    fig, axes = plt.subplots(n, 1, figsize=(13, 4.3 * n), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (judul, x, fd) in zip(axes, tahapan):
        for f in FASE_REPETISI:
            if f in w.index:
                a, b = max(w.loc[f, "onset"], t0), min(w.loc[f, "selesai"], t1)
                ax.axvspan(a, b, color=FASE_WARNA[f], alpha=0.10, lw=0)
                if ax is axes[0]:
                    ax.text((a + b) / 2, len(KANAL) * jarak_uv + 70, f, ha="center", va="bottom", fontsize=9,
                            color=INK)
        te = TE[(TE.gerakan == gerakan) & (TE.rep == rep)]
        for f, g in te.groupby("fase"):
            ax.plot([g.mulai.min(), g.selesai.max()], [len(KANAL) * jarak_uv + 25] * 2, color=FASE_WARNA[f], lw=4,
                    solid_capstyle="butt")
        for k, c in enumerate(KANAL):
            off = (len(KANAL) - 1 - k) * jarak_uv
            y = x[k, i0:i1].astype(float).copy()
            hil = fd[k, i0:i1] >= 0.1
            y[hil] = np.nan
            # tanda merah per potongan 1 dtk bergeser 0,5 dtk yang > 150 µV
            buruk = np.zeros(len(y), bool)
            for s in range(0, len(y) - int(sf) + 1, int(sf / 2)):
                seg = y[s:s + int(sf)]
                if np.isfinite(seg).sum() > sf / 2 and np.nanmax(seg) - np.nanmin(seg) > 150:
                    buruk[s:s + int(sf)] = True
            yk = np.clip(y, -jarak_uv * 0.9, jarak_uv * 0.9) + off
            ax.plot(t, np.where(buruk, np.nan, yk), color=INK, lw=0.55)
            ax.plot(t, np.where(buruk, yk, np.nan), color=MERAH, lw=0.55)
            ax.plot(t, np.where(hil, off, np.nan), color="#a9a8a2", lw=2.5, solid_capstyle="butt")
        ax.set_yticks([(len(KANAL) - 1 - k) * jarak_uv for k in range(len(KANAL))], KANAL, fontsize=7.5)
        ax.axhline((len(KANAL) / 2 - 0.5) * jarak_uv, color=GRID, lw=1.5)
        ax.set_ylim(-jarak_uv, len(KANAL) * jarak_uv + 120)
        ax.set_title(judul, fontsize=10, loc="left", color=INK)
        ax.plot([t1 - 0.3] * 2, [-0.8 * jarak_uv, -0.8 * jarak_uv + 100], color=INK, lw=2)
        ax.text(t1 - 0.4, -0.8 * jarak_uv + 50, "100 µV", ha="right", va="center", fontsize=7.5, color=INK2)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
    axes[-1].set_xlabel("waktu EEG (dtk)")
    fig.suptitle(f"{pid} — {gerakan} repetisi {rep}: gelombang EEG per tahap proses", x=0.01, ha="left",
                 fontsize=11.5, y=1.0)
    fig.text(0.01, -0.02, "Latar = fase (timestamp manual). Batang di atas = rentang epoch TE yang dianalisis. Hitam = "
             "potongan 1 dtk ≤ 150 µV; merah = > 150 µV (tidak bersih); abu-abu tebal = sinyal datar/kanal hilang. "
             "Kanal dipotong ±108 µV untuk tampilan. Garis horizontal memisahkan belahan kiri (A1) dan kanan (A2).",
             fontsize=7.5, color=INK2, wrap=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


T5_WARNA = {"T5_dasar": ("#2a78d6", "dasar (ASR + A2)"), "T5_ICA_mata": ("#eb6834", "ICA mata"),
            "T5_ICA_mata_otot": ("#1baf7a", "ICA mata + otot"), "T5_CCA_otot": ("#eda100", "CCA otot"),
            "T5_regresi_mata": ("#e87ba4", "regresi mata (Fp)"), "T5_ICAmata_CCAotot": ("#4a3aa7", "ICA mata + CCA otot")}


def tahap6(pres, sdr, hasil, path):
    """Kiri: galat nilai repetisi vs jumlah jendela bersih (per fase) + garis setengah SD antar-repetisi.
    Kanan: % sel partisipan × fase × kanal lolos R2 vs n_min, untuk r_min 2/3/4 (median fase)."""
    from .istilah import FASE_REPETISI
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.9))
    ax = axes[0]
    for f in FASE_REPETISI:
        g = pres[pres.fase == f]
        if g.empty:
            continue
        ax.plot(g.n, g.semua, marker="o", color=FASE_WARNA[f], lw=2, markersize=5)
        ax.annotate(f, (g.n.iloc[-1], g.semua.iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=8, color=INK2)
    half = 0.5 * sdr.semua.median()
    ax.axhline(half, color=INK2, lw=1, ls=(0, (4, 3)))
    ax.text(pres.n.max(), half, f"½ SD antar-repetisi ({half:.1f} dB)", ha="right", va="bottom", fontsize=8, color=INK2)
    ax.set_xlabel("jumlah jendela bersih (1 dtk, geser 0,25 dtk)")
    ax.set_ylabel("galat RMS nilai repetisi (dB)")
    ax.set_title("R1: presisi nilai repetisi", fontsize=10, loc="left")
    ax.set_xticks(sorted(pres.n.unique()))
    ax.grid(axis="y", color=GRID, lw=0.6)
    _rapikan(ax)
    ax = axes[1]
    warna = {2: "#2a78d6", 3: "#eb6834", 4: "#1baf7a"}
    for r, g in hasil.groupby("r_min"):
        m = g.groupby("c_min").pct_sel_lolos_R2.median()
        m.index = (100 * m.index).astype(int)
        ax.plot(m.index, m.values, marker="o", lw=2, markersize=5, color=warna.get(r, INK))
        ax.annotate(f"≥ {r} repetisi", (m.index[-1], m.values[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK2)
    ax.set_xlabel("R1: cakupan minimum rentang TE oleh jendela bersih (%)")
    ax.set_ylabel("% sel partisipan × fase × kanal lolos R2")
    ax.set_title("R2: data yang tersisa (median 4 fase)", fontsize=10, loc="left")
    ax.set_xticks(sorted((100 * hasil.c_min.unique()).astype(int)))
    ax.axhline(75, color=INK2, lw=1, ls=(0, (4, 3)))
    ax.text(0, 72, "batas pemilihan 75%", fontsize=8, color=INK2, va="top")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", color=GRID, lw=0.6)
    _rapikan(ax)
    fig.suptitle("Tahap 6 — aturan pakai (cakupan, presisi & jumlah data; tanpa melihat nilai ERD)", x=0.01, ha="left",
                 fontsize=11.5, y=1.03)
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
