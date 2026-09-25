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


def epoch_banding(R, path):
    """Empat ukuran per fase, B vs E; titik = partisipan, garis penghubung per partisipan."""
    from .istilah import FASE_REPETISI
    ukuran = [("detik_bersih_median_kanal", "Detik data bersih\nper kanal (median)", None),
              ("cakupan_fase_median", "Cakupan jendela\nobservasi (median)", (0, 1.05)),
              ("se_db_median", "Galat baku estimasi\npower (dB; kecil = presisi)", None),
              ("reliabilitas_belah_dua", "Reliabilitas belah-dua\n(pola kanal × pita)", (-0.5, 1.05))]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
    x = np.arange(len(FASE_REPETISI))
    for ax, (col, lab, lim) in zip(axes, ukuran):
        for pid, g in R.groupby("participant_id"):
            b = g[g.metode == "B"].set_index("fase").reindex(FASE_REPETISI)[col].values
            e = g[g.metode == "E"].set_index("fase").reindex(FASE_REPETISI)[col].values
            for i in range(len(x)):
                ax.plot([x[i] - 0.15, x[i] + 0.15], [b[i], e[i]], color=GRID, lw=1.2, zorder=1)
            ax.scatter(x - 0.15, b, s=34, facecolor=SURFACE, edgecolor=REPO, linewidth=1.8, zorder=2)
            ax.scatter(x + 0.15, e, s=26, color=BARU, edgecolor=SURFACE, linewidth=1, zorder=3)
        ax.set_xticks(x, FASE_REPETISI)
        ax.set_title(lab, fontsize=9, loc="left", color=INK)
        if lim:
            ax.set_ylim(*lim)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        _rapikan(ax)
    h = [plt.Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=REPO, markeredgewidth=2,
                    markersize=8),
         plt.Line2D([], [], marker="o", ls="", color=BARU, markersize=6)]
    fig.legend(h, ["B: epoch tetap 1,5 dtk dari onset − 0,5", "E: jendela geser 1 dtk berlabel fase"],
               loc="upper left", ncol=2, frameon=False, bbox_to_anchor=(0.01, 1.08), fontsize=8.5)
    fig.text(0.01, -0.04, "Titik hilang = tidak dapat dihitung (kurang dari 3 repetisi bersih; B pada P32 Gerak/Tahan/Berdiri).", fontsize=7.5, color=INK2)
    fig.suptitle("Epoching B vs E — per fase, 4 partisipan (titik), sebelum koreksi artefak", x=0.01, y=1.17,
                 ha="left", fontsize=11)
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
