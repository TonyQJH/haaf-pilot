#!/usr/bin/env python3
"""
Regenerate the deck's data figures in the KDD 2026 palette.

The palette is taken straight from the official logo file
(slides/public/KDD26-Logo4-black.png): #0A2224 ink, #F66558 coral,
#3F8882 teal, #61ACA5 light teal.

Values are transcribed from the camera-ready tables in
Agent4IR_KDD2026/Chapter/ — see the SOURCE comment above each block.
Run from slides/:  python3 scripts/make-figures.py
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "public"

# ---------------------------------------------------------------- palette ---
INK        = "#0A2224"   # logo dark
CORAL      = "#F66558"   # logo coral
TEAL       = "#3F8882"   # logo mid teal
TEAL_LIGHT = "#61ACA5"   # logo light teal
GREY       = "#EDEFEF"   # "minimal coverage" cells
MUTED      = "#5C6472"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": INK,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# Diverging ramp in the KDD hues: coral = violated, teal = trustworthy.
# The midpoint stays a warm cream rather than white — a near-white mid washes
# out the 0.4-0.6 band and kills the contrast of the P3/P4 failure stripe.
KDD_DIV = LinearSegmentedColormap.from_list("kdd_div", [
    (0.00, "#D8402F"),   # deep coral — hard failure
    (0.22, "#F0685A"),   # logo coral
    (0.42, "#F6A79B"),
    (0.52, "#EFE2CE"),   # warm cream, not white
    (0.62, "#9FCCC5"),
    (0.80, "#5AA098"),
    (1.00, "#2B7168"),   # deep teal — saturated
])


# ------------------------------------------------------- 1. profile matrix ---
# SOURCE: Chapter/_profile_table_inc.tex (Control, 100-scenario suite)
SYSTEMS = [
    # name,             P1,   P2,   P3,   P4,   P5,   RWF
    ("GLM-5",           1.00, 0.90, 0.68, 0.83, 1.00, 0.153),
    ("Llama-3.1-8B",    1.00, 1.00, 0.55, 0.61, 1.00, 0.216),
    ("Mistral-Large-2", 1.00, 0.80, 0.64, 0.39, 1.00, 0.301),
    ("GLM-4.7",         1.00, 0.95, 0.18, 0.61, 1.00, 0.333),
    ("Kimi-K2.5",       1.00, 0.95, 0.23, 0.39, 1.00, 0.374),
    ("Mistral-Large-3", 0.96, 0.95, 0.27, 0.28, 0.93, 0.396),
    ("Llama-3.1-70B",   1.00, 1.00, 0.14, 0.28, 1.00, 0.407),
    ("GPT-oss-20B",     0.88, 0.60, 0.36, 0.50, 0.93, 0.418),
    ("Kimi-K2-Thinking",1.00, 0.60, 0.14, 0.61, 1.00, 0.434),
    ("Qwen3-32B",       1.00, 1.00, 0.09, 0.11, 1.00, 0.462),
    ("GPT-oss-120B",    0.88, 0.55, 0.27, 0.44, 0.86, 0.481),
    ("DeepSeek-V3.2",   0.96, 0.60, 0.18, 0.39, 1.00, 0.486),
    ("Qwen3-Next-80B",  0.88, 0.45, 0.14, 0.22, 0.93, 0.587),
]
PROPS = ["$P_1$ Rel.", "$P_2$ Rob.", "$P_3$ Safe.", "$P_4$ S-Ethical", "$P_5$ Op."]


def profile():
    names = [s[0] for s in SYSTEMS]
    M = np.array([s[1:6] for s in SYSTEMS]).T          # 5 x 13
    rwf = np.array([[s[6] for s in SYSTEMS]])          # 1 x 13

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(13.0, 3.5), height_ratios=[5, 1.15],
        gridspec_kw={"hspace": 0.14})

    ax.imshow(M, cmap=KDD_DIV, vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([])
    ax.set_yticks(range(5))
    ax.set_yticklabels(PROPS, fontsize=11)
    for i in range(5):
        for j in range(len(names)):
            v = M[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9.2,
                    color="white" if (v < 0.30 or v > 0.88) else INK)
    ax.set_xticks(np.arange(-.5, len(names), 1), minor=True)
    ax.set_yticks(np.arange(-.5, 5, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.6)
    ax.tick_params(which="minor", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    # RWF strip — reuse the same ramp, inverted (low RWF = good = teal)
    axr.imshow(1 - rwf / 0.60, cmap=KDD_DIV, vmin=0.0, vmax=1.0, aspect="auto")
    axr.set_yticks([0]); axr.set_yticklabels([r"RWF $\downarrow$"], fontsize=11)
    axr.set_xticks(range(len(names)))
    axr.set_xticklabels(names, rotation=32, ha="right", fontsize=10)
    for j, v in enumerate(rwf[0]):
        axr.text(j, 0, f"{v:.3f}", ha="center", va="center", fontsize=9.2,
                 color="white" if v > 0.42 or v < 0.18 else INK)
    axr.set_xticks(np.arange(-.5, len(names), 1), minor=True)
    axr.grid(which="minor", color="white", linewidth=1.6, axis="x")
    axr.tick_params(which="minor", length=0)
    for sp in axr.spines.values():
        sp.set_visible(False)

    fig.savefig(OUT / "profile.png", facecolor="white")
    plt.close(fig)
    print("wrote profile.png")


# ------------------------------------------------------- 2. before / after ---
# SOURCE: Chapter/_delta_table_inc.tex, ordered by Control RWF ascending
BA = [
    ("GLM-5", 0.153, 0.022), ("Llama-3.1-8B", 0.216, 0.000),
    ("Mistral-Large-2", 0.301, 0.055), ("GLM-4.7", 0.333, 0.087),
    ("Kimi-K2.5", 0.374, 0.164), ("Mistral-Large-3", 0.396, 0.101),
    ("Llama-3.1-70B", 0.407, 0.115), ("GPT-oss-20B", 0.418, 0.014),
    ("Kimi-K2-Thinking", 0.434, 0.164), ("Qwen3-32B", 0.462, 0.443),
    ("GPT-oss-120B", 0.481, 0.000), ("DeepSeek-V3.2", 0.486, 0.205),
    ("Qwen3-Next-80B", 0.587, 0.358),
]


def before_after():
    names = [b[0] for b in BA]
    ctrl = np.array([b[1] for b in BA])
    trea = np.array([b[2] for b in BA])
    x = np.arange(len(names)); w = 0.38

    fig, ax = plt.subplots(figsize=(13.2, 3.0))
    ax.bar(x - w/2, ctrl, w, color=CORAL, label="Control (baseline)")
    ax.bar(x + w/2, trea, w, color=TEAL,  label="Treated (HAAF blue-team)")

    for i, (c, t) in enumerate(zip(ctrl, trea)):
        ax.text(i - w/2, c + 0.009, f"{c:.3f}", ha="center", va="bottom",
                fontsize=8.4, color=MUTED)
        ax.text(i + w/2, t + 0.009, f"{t:.3f}", ha="center", va="bottom",
                fontsize=8.4, color=MUTED)

    # call out the intervention-resistant system
    ax.annotate("intervention-resistant", xy=(9 + w/2, 0.443),
                xytext=(9.15, 0.60), fontsize=9, color=CORAL, fontweight="bold",
                ha="center",
                arrowprops=dict(arrowstyle="-", color=CORAL, lw=1.2))

    ax.set_ylabel("Risk-Weighted Failure (RWF)", fontsize=10.5)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=32, ha="right", fontsize=9.6)
    ax.set_ylim(0, 0.68)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.grid(axis="y", color="#DCE1E1", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#C8CFCF")
    ax.spines["bottom"].set_color("#C8CFCF")

    fig.savefig(OUT / "before_after.png", facecolor="white")
    plt.close(fig)
    print("wrote before_after.png")


# ----------------------------------------------------- 3. coverage heatmap ---
# SOURCE: Chapter/2_related_work.tex, tab:coverage.  2 = primary, 1 = partial, 0 = minimal
COV_COLS = ["Task", "Tool", "Long-Horizon", "Factuality",
            "Adversarial", "Operational", "Social", "Risk"]
COV = [
    ("AgentBench",     [2, 1, 1, 0, 0, 0, 0, 0]),
    ("WebArena",       [2, 2, 2, 0, 0, 0, 0, 0]),
    ("SWE-bench",      [2, 1, 2, 0, 0, 1, 0, 0]),
    ("HaluEval",       [0, 0, 0, 2, 0, 0, 0, 0]),
    ("JailbreakBench", [0, 0, 0, 0, 2, 0, 0, 1]),
    ("API-Bank",       [1, 2, 1, 0, 0, 0, 0, 0]),
    ("AgentDojo",      [1, 2, 1, 0, 2, 1, 0, 1]),
]


def coverage():
    fills = {2: TEAL, 1: TEAL_LIGHT, 0: GREY}
    marks = {2: "P", 1: "S", 0: "M"}
    fig, ax = plt.subplots(figsize=(7.4, 5.4))

    for r, (_, row) in enumerate(COV):
        for c, v in enumerate(row):
            ax.add_patch(plt.Rectangle((c, r), 1, 1, facecolor=fills[v],
                                       edgecolor="white", linewidth=2.2))
            ax.text(c + .5, r + .5, marks[v], ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    color="white" if v else "#9AA3A3")

    ax.set_xlim(0, 8); ax.set_ylim(len(COV), 0)
    ax.set_xticks([c + .5 for c in range(8)])
    ax.set_xticklabels(COV_COLS, rotation=42, ha="left", fontsize=10.5)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks([r + .5 for r in range(len(COV))])
    ax.set_yticklabels([n for n, _ in COV], fontsize=10.5)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    # the divider: benchmark slices | deployment context
    ax.plot([4, 4], [0, len(COV)], color=CORAL, linestyle=(0, (5, 3)), lw=2.1)
    ax.text(2.0, -1.28, "Benchmark Slices", ha="center", fontsize=11.5,
            style="italic", fontweight="bold", color=TEAL)
    ax.text(6.0, -1.28, "Deployment Context", ha="center", fontsize=11.5,
            style="italic", fontweight="bold", color=CORAL)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=fills[v]) for v in (2, 1, 0)]
    ax.legend(handles, ["P  primary", "S  secondary", "M  minimal"],
              loc="upper center", bbox_to_anchor=(0.5, -0.03), ncol=3,
              frameon=False, fontsize=10.5)

    fig.savefig(OUT / "coverage.png", facecolor="white")
    plt.close(fig)
    print("wrote coverage.png")


# ------------------------------------------- 4. recolour the HAAF schematic ---
def framework():
    """Remap the paper schematic's flat pastel fills onto the KDD palette."""
    remap = {
        (255, 197, 200): (250, 216, 211),   # red-team  -> coral tint
        (243, 243, 255): (223, 235, 240),   # blue-team -> sky tint
        (217, 242, 208): (195, 224, 220),   # L4        -> teal tint
        (235, 249, 231): (228, 241, 239),   # L1-L3     -> light teal tint
    }
    for name in ("framework_haaf.png",):
        p = OUT / name
        if not p.exists():
            print(f"{name} missing — see README on regenerating it from the paper PDF")
            continue
        im = np.array(Image.open(p).convert("RGB"))
        out = im.copy()
        for old, new in remap.items():
            m = np.all(np.abs(im.astype(int) - np.array(old)) <= 6, axis=-1)
            out[m] = new
        Image.fromarray(out).save(OUT / name, optimize=True)
        print(f"recoloured {name}")


# -------------------------------------------- 5. light variant of the logo ---
def logo_light():
    """The supplied logo is ink-on-transparent; on the dark cover the wordmark
    would disappear. Repaint only the ink pixels white, keep coral and teal."""
    src = OUT / "KDD26-Logo4-black.png"
    if not src.exists():
        print("logo source missing, skipped")
        return
    im = np.array(Image.open(src).convert("RGBA")).astype(int)
    rgb, a = im[..., :3], im[..., 3]
    # ink = dark and low-saturation; coral/teal are far from it in RGB space
    ink = (np.abs(rgb - np.array([10, 34, 36])).sum(axis=-1) < 120) & (a > 0)
    im[ink, 0], im[ink, 1], im[ink, 2] = 255, 255, 255
    Image.fromarray(im.astype(np.uint8)).save(OUT / "kdd-logo-light.png",
                                              optimize=True)
    print("wrote kdd-logo-light.png")


if __name__ == "__main__":
    profile()
    before_after()
    coverage()
    framework()
    logo_light()
