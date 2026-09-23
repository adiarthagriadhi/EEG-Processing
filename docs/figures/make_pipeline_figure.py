"""Menggambar diagram alur pipeline (Methods) sebagai PNG 300 dpi.
Jalankan: python docs/figures/make_pipeline_figure.py"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BOX = {  # nama: (x, y, teks, warna)
    "V": (0.8, 3.65, "Video\n(screen + webcam)", "#fde0c5"),
    "E": (0.8, 1.6, "EEG Trial EDF\n(16 ch, 100 Hz)", "#d6e9f8"),
    "O": (3.3, 4.35, "Task timeline\nOCR of on-screen\ninstructions", "#fde0c5"),
    "P": (3.3, 2.95, "Pose estimation\ntrunk trajectory", "#fde0c5"),
    "R": (3.3, 0.35, "Preprocessing\nbad channels, ICA", "#d6e9f8"),
    "S": (5.8, 3.65, "EEG\u2013video\nsynchronisation", "#e5e5e5"),
    "F": (8.3, 3.65, "Movement phases\nper repetition", "#e5e5e5"),
    "D": (8.3, 2.0, "ERD/ERS and LI\nper phase", "#d9f0d3"),
    "G": (8.3, 0.35, "Romberg\nspectral features", "#d9f0d3"),
    "T": (10.8, 1.175, "Group statistics\nPapers A, B, D", "#e7d4e8"),
}
# (dari, ke, port asal, port tujuan, bentuk garis)
EDGES = [("V", "O", "r", "l", "arc3"), ("V", "P", "r", "l", "arc3"),
         ("O", "S", "r", "l", "arc3"), ("P", "S", "r", "l", "arc3"),
         ("E", "S", "r", "b", "angle,angleA=0,angleB=90,rad=0"),
         ("E", "R", "r", "l", "arc3"), ("S", "F", "r", "l", "arc3"),
         ("F", "D", "b", "t", "arc3"), ("R", "D", "r", "l", "arc3"),
         ("R", "G", "r", "l", "arc3"), ("D", "T", "r", "l", "arc3"),
         ("G", "T", "r", "l", "arc3")]
W, H = 1.9, 0.95


def main(out=Path(__file__).with_name("pipeline.png")):
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    for x, y, txt, col in BOX.values():
        ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H,
                                    boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=col, ec="#333333", lw=1.2))
        ax.text(x, y, txt, ha="center", va="center", fontsize=10.5)
    def port(k, side):
        x, y = BOX[k][:2]
        return {"r": (x + W / 2, y), "l": (x - W / 2, y), "t": (x, y + H / 2),
                "b": (x, y - H / 2)}[side]

    for a, b, pa, pb, conn in EDGES:
        ax.add_patch(FancyArrowPatch(port(a, pa), port(b, pb), arrowstyle="-|>",
                                     mutation_scale=14, lw=1.2, color="#333333",
                                     connectionstyle=conn, shrinkA=2, shrinkB=2))
    ax.set_xlim(-0.3, 11.9)
    ax.set_ylim(-0.3, 4.95)
    ax.axis("off")
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
