"""More generated QE teaching diagrams (batch 2) -> media/diagrams/.

Run with: python3 media/diagrams_more.py
Same convention as diagrams.py: each key maps to media/diagrams/<key>.png and is
referenced from content/*.json via media.image.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon, Circle
import numpy as np
from pathlib import Path

OUT_DIR = Path(__file__).parent / "diagrams"
DPI = 150
np.random.seed(11)

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.size": 13, "axes.titlesize": 15, "axes.titleweight": "bold",
    "savefig.bbox": "tight", "savefig.pad_inches": 0.25,
})

NAVY, BLUE, GREEN, RED, GOLD, PURPLE = "#1f4e79", "#2e75b6", "#2e7d32", "#c00000", "#bf9000", "#a64d79"


def _flow(path, steps, title, colors=None):
    """Generic numbered horizontal flow of labelled boxes with arrows."""
    n = len(steps)
    colors = colors or [NAVY, BLUE, "#2e9e7f", GREEN, GOLD, "#d06f1a", PURPLE][:n]
    while len(colors) < n:
        colors += colors
    fig, ax = plt.subplots(figsize=(min(2.0 * n, 11), 2.8))
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, label in enumerate(steps):
        ax.add_patch(Rectangle((i + 0.04, 0.28), 0.92, 0.46, fc=colors[i], ec="white"))
        ax.text(i + 0.5, 0.51, label, ha="center", va="center", color="white",
                fontsize=10, fontweight="bold")
        if i < n - 1:
            ax.annotate("", (i + 1.02, 0.51), (i + 0.96, 0.51),
                        arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.6))
    ax.set_title(title, fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def histogram(path):
    data = np.random.normal(50, 8, 600)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.hist(data, bins=24, color="#cfe2f3", edgecolor="#6fa8dc")
    ax.axvline(data.mean(), color=RED, ls="--", lw=2, label=f"mean ≈ {data.mean():.0f}")
    ax.set_title("Histogram — the Shape of the Data")
    ax.set_xlabel("Measured value")
    ax.set_ylabel("Count")
    ax.legend()
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def pareto(path):
    cats = ["Scratch", "Dent", "Misalign", "Burr", "Color", "Other"]
    counts = np.array([120, 85, 60, 30, 18, 12])
    cum = np.cumsum(counts) / counts.sum() * 100
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(cats, counts, color=BLUE, edgecolor="white")
    ax.set_ylabel("Defect count")
    ax.set_title("Pareto Chart — the Vital Few")
    ax2 = ax.twinx()
    ax2.plot(cats, cum, "-o", color=RED, lw=2)
    ax2.axhline(80, color=GOLD, ls="--", lw=1.4)
    ax2.text(len(cats) - 1, 82, "80%", color=GOLD, ha="right", fontsize=11)
    ax2.set_ylabel("Cumulative %")
    ax2.set_ylim(0, 105)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def variation_causes(path):
    stable = 50 + np.random.normal(0, 2, 16)
    shifted = 57 + np.random.normal(0, 2, 9)   # special-cause shift
    y = np.concatenate([stable, shifted])
    x = np.arange(1, len(y) + 1)
    cl = stable.mean(); sd = stable.std()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(x, y, "-o", color=NAVY, ms=5)
    ax.axhline(cl, color=GREEN, lw=1.6)
    ax.axhline(cl + 3 * sd, color=RED, ls="--"); ax.axhline(cl - 3 * sd, color=RED, ls="--")
    ax.axvspan(0.5, 16.5, color="#e8f5e9", alpha=0.6)
    ax.axvspan(16.5, 25.5, color="#fdecea", alpha=0.6)
    ax.text(8, ax.get_ylim()[1] * 0.98, "Common cause\n(stable, random)", ha="center",
            va="top", color=GREEN, fontsize=10)
    ax.text(21, ax.get_ylim()[1] * 0.98, "Special cause\n(a shift appears)", ha="center",
            va="top", color=RED, fontsize=10)
    ax.set_title("Common Cause vs. Special Cause Variation")
    ax.set_xlabel("Sample #"); ax.set_ylabel("Value")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def p_chart(path):
    k = 20
    p = np.random.normal(0.05, 0.012, k).clip(0.005, None)
    p[12] = 0.11
    n = 200
    pbar = p.mean()
    sd = np.sqrt(pbar * (1 - pbar) / n)
    ucl, lcl = pbar + 3 * sd, max(0, pbar - 3 * sd)
    x = np.arange(1, k + 1)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(x, p, "-o", color=NAVY, ms=5)
    ooc = p > ucl
    ax.plot(x[ooc], p[ooc], "o", color=RED, ms=11)
    ax.axhline(pbar, color=GREEN, lw=1.6); ax.axhline(ucl, color=RED, ls="--"); ax.axhline(lcl, color=RED, ls="--")
    ax.text(k + 0.2, ucl, "UCL", color=RED, va="center"); ax.text(k + 0.2, pbar, "p̄", color=GREEN, va="center")
    ax.set_title("Attributes Control Chart (p-chart): Fraction Defective")
    ax.set_xlabel("Subgroup #"); ax.set_ylabel("Proportion defective")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def stress_strain(path):
    e1 = np.linspace(0, 0.01, 50); s1 = e1 * 20000          # elastic
    e2 = np.linspace(0.01, 0.06, 60); s2 = 200 + (e2 - 0.01) * 1200  # plastic to UTS
    e3 = np.linspace(0.06, 0.09, 40); s3 = 260 - (e3 - 0.06) * 1500  # necking to fracture
    e = np.concatenate([e1, e2, e3]); s = np.concatenate([s1, s2, s3])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(e, s, color=NAVY, lw=2.2)
    ax.plot(0.01, 200, "o", color=GREEN); ax.annotate("Yield", (0.01, 200), (0.012, 150), color=GREEN)
    imax = s.argmax(); ax.plot(e[imax], s[imax], "o", color=GOLD)
    ax.annotate("Ultimate tensile\nstrength (UTS)", (e[imax], s[imax]), (0.04, 290), color=GOLD)
    ax.plot(e[-1], s[-1], "x", color=RED, ms=10); ax.annotate("Fracture", (e[-1], s[-1]), (0.08, 230), color=RED)
    ax.annotate("Elastic region\n(slope = E, Young's modulus)", (0.005, 100), (0.018, 60), color=BLUE,
                arrowprops=dict(arrowstyle="->", color=BLUE))
    ax.set_title("Stress–Strain Curve"); ax.set_xlabel("Strain (ε)"); ax.set_ylabel("Stress (σ)")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def accuracy_precision(path):
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2))
    titles = ["Accurate &\nPrecise", "Precise,\nnot accurate", "Accurate,\nnot precise", "Neither"]
    centers = [(0, 0), (0.55, 0.55), (0, 0), (0.5, -0.4)]
    spreads = [0.08, 0.08, 0.32, 0.34]
    for ax, t, c, sp in zip(axes, titles, centers, spreads):
        for r, col in [(1.0, "#bbbbbb"), (0.66, "#dddddd"), (0.33, "#f0f0f0")]:
            ax.add_patch(Circle((0, 0), r, fc=col, ec="#999", zorder=1))
        pts = np.random.normal(0, sp, (10, 2)) + np.array(c)
        ax.scatter(pts[:, 0], pts[:, 1], color=RED, zorder=3, s=22)
        ax.plot(0, 0, "+", color="black", ms=12, mew=2, zorder=2)
        ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2); ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(t, fontsize=11)
    fig.suptitle("Accuracy vs. Precision", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(path, dpi=DPI); plt.close(fig)


def gauge_rr(path):
    comps = ["Part-to-Part", "Repeatability", "Reproducibility", "Total Gauge R&R"]
    vals = [82, 9, 6, 15]
    colors = [GREEN, BLUE, "#2e9e7f", RED]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(comps, vals, color=colors, edgecolor="white")
    ax.axhline(10, color=GREEN, ls="--", lw=1.3); ax.axhline(30, color=RED, ls="--", lw=1.3)
    ax.text(3.4, 10, "10% good", color=GREEN, va="center", fontsize=9)
    ax.text(3.4, 30, "30% max", color=RED, va="center", fontsize=9)
    ax.set_ylabel("% of total variation")
    ax.set_title("Gauge R&R — Where the Variation Comes From")
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v}%", ha="center", fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def fishbone(path):
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
    ax.annotate("", (8.6, 3), (0.6, 3), arrowprops=dict(arrowstyle="-|>", color="black", lw=2.2))
    ax.add_patch(Rectangle((8.6, 2.4), 1.3, 1.2, fc=NAVY, ec="white"))
    ax.text(9.25, 3.0, "Effect\n(problem)", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    bones = [("Man", 1.7, True), ("Machine", 4.0, True), ("Method", 6.3, True),
             ("Material", 1.7, False), ("Measurement", 4.0, False), ("Environment", 6.3, False)]
    for label, xb, up in bones:
        y0 = 3; y1 = 5.2 if up else 0.8
        x1 = xb - 1.1
        ax.plot([xb, x1], [y0, y1], color=BLUE, lw=1.8)
        ax.text(x1 - 0.05, y1 + (0.15 if up else -0.15), label, ha="right",
                va="bottom" if up else "top", color=BLUE, fontsize=11, fontweight="bold")
    ax.set_title("Cause-and-Effect (Ishikawa / Fishbone) — the 6 M's", fontsize=14)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def vision_pipeline(path):
    _flow(path, ["Part", "Lighting +\nCamera", "Image\ncapture", "Processing\n& algorithm",
                 "Pass / Fail\ndecision"], "Machine-Vision Inspection Pipeline")


def gdt_zone_compare(path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.6))
    for ax in (ax1, ax2):
        ax.set_xlim(-2, 2); ax.set_ylim(-2, 2); ax.set_aspect("equal"); ax.axis("off")
        ax.plot(0, 0, "+", color="black", ms=14, mew=2)
    ax1.add_patch(Rectangle((-1, -1), 2, 2, fill=False, ec=RED, lw=2))
    ax1.set_title("± coordinate tolerance\n(square zone)", fontsize=12)
    ax2.add_patch(Circle((0, 0), 1.13, fill=False, ec=GREEN, lw=2))
    ax2.set_title("True position\n(round zone, ~57% bigger)", fontsize=12)
    # show corners the square rejects but circle would too / accepts more area
    fig.suptitle("Why GD&T Position Beats Coordinate Tolerancing", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92]); fig.savefig(path, dpi=DPI); plt.close(fig)


def gdt_form(path):
    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
    x = np.linspace(1, 9, 200)
    surf = 2 + 0.18 * np.sin(2.2 * x) + 0.06 * np.sin(7 * x)
    ax.fill_between([1, 9], 2.45, 1.55, color="#fff2cc", alpha=0.7)
    ax.axhline(2.45, 1 / 10, 9 / 10, color=RED, ls="--"); ax.axhline(1.55, 1 / 10, 9 / 10, color=RED, ls="--")
    ax.plot(x, surf, color=NAVY, lw=2)
    ax.annotate("", (9.4, 2.45), (9.4, 1.55), arrowprops=dict(arrowstyle="<->", color=RED))
    ax.text(9.5, 2.0, "0.1 wide\ntolerance zone", color=RED, va="center", fontsize=10)
    ax.set_title("Form Control — Flatness: the surface must lie between two parallel planes", fontsize=12.5)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def gdt_orientation(path):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.set_xlim(0, 8); ax.set_ylim(0, 6); ax.axis("off")
    ax.add_patch(Rectangle((1, 1), 6, 0.5, fc="#cccccc", ec="black"))   # datum A
    ax.text(7.1, 1.25, "Datum A", va="center", fontsize=10)
    ax.fill_betweenx([1.5, 5.3], 3.7, 4.3, color="#fff2cc", alpha=0.8)   # tolerance zone
    ax.axvline(3.7, 1.5 / 6, 5.3 / 6, color=RED, ls="--"); ax.axvline(4.3, 1.5 / 6, 5.3 / 6, color=RED, ls="--")
    ax.plot([4.05, 4.18], [1.6, 5.2], color=NAVY, lw=2.4)               # actual feature (slightly off)
    ax.annotate("", (3.7, 5.4), (4.3, 5.4), arrowprops=dict(arrowstyle="<->", color=RED))
    ax.text(4.0, 5.6, "0.2 zone", color=RED, ha="center", fontsize=10)
    # right-angle marker
    ax.plot([3.7, 3.7, 3.95], [1.5, 1.75, 1.75], color="black", lw=1.2)
    ax.text(2.0, 3.5, "feature must be\n⊥ to datum A", color=BLUE, fontsize=10)
    ax.set_title("Orientation Control — Perpendicularity", fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def gdt_runout(path):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.set_xlim(0, 8); ax.set_ylim(0, 6); ax.axis("off")
    ax.add_patch(Circle((3.2, 3), 1.7, fc="#dbe5f1", ec=NAVY, lw=2))
    ax.add_patch(Circle((3.2, 3), 0.12, fc="black"))
    ax.plot([0.8, 5.6], [3, 3], color="black", ls="-.", lw=1)
    ax.text(0.8, 3.25, "datum axis", fontsize=9)
    ax.annotate("", (4.0, 4.6), (2.4, 4.6), arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.6,
                connectionstyle="arc3,rad=0.5"))
    ax.text(3.2, 5.2, "part rotates 360°", ha="center", color=GREEN, fontsize=10)
    # dial indicator
    ax.add_patch(Rectangle((5.6, 2.6), 1.4, 0.8, fc=GOLD, ec="black"))
    ax.text(6.3, 3.0, "indicator", ha="center", va="center", fontsize=9)
    ax.plot([4.9, 5.6], [3, 3], color="black", lw=2)
    ax.text(4.0, 1.2, "Runout = full indicator movement (FIM)\nas the part spins about the datum axis",
            ha="center", color=BLUE, fontsize=10)
    ax.set_title("Runout — Wobble Relative to the Datum Axis", fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def fmea_7step(path):
    _flow(path, ["1 Planning\n& Prep", "2 Structure\nanalysis", "3 Function\nanalysis",
                 "4 Failure\nanalysis", "5 Risk\nanalysis", "6 Optim-\nization", "7 Results\n& docs"],
          "The 7-Step FMEA Approach (AIAG-VDA)")


def sevenD_flow(path):
    labels = ["1 Define", "2 Verify", "3 Contain", "4 Root\ncause",
              "5 Correct", "6 Confirm", "7 Prevent"]
    n = len(labels)
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.set_xlim(0, n); ax.set_ylim(0, 2); ax.axis("off")
    cols = [NAVY, BLUE, "#2e9e7f", GREEN, GOLD, "#d06f1a", PURPLE]
    for i, lab in enumerate(labels):
        cx = i + 0.5
        diamond = Polygon([(cx, 1.7), (cx + 0.46, 1.0), (cx, 0.3), (cx - 0.46, 1.0)],
                          fc=cols[i], ec="white")
        ax.add_patch(diamond)
        ax.text(cx, 1.0, lab, ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
        if i < n - 1:
            ax.annotate("", (i + 1.06, 1.0), (i + 0.96, 1.0),
                        arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.4))
    ax.set_title("The GM 7-Diamond Structured Problem-Solving Flow", fontsize=14)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def control_plan(path):
    cols = ["Process\nStep", "Characteristic", "Spec /\nTolerance", "Measurement\nMethod",
            "Sample\nSize / Freq", "Control\nMethod", "Reaction\nPlan"]
    rows = [
        ["OP20\nDrill", "Hole Ø", "8.0 ±0.1", "Bore gauge", "5 / hour", "X̄-R chart", "Quarantine\n& adjust"],
        ["OP30\nMill", "Slot width", "12.0 ±0.05", "Caliper", "3 / hour", "Check sheet", "Stop & call\nsupervisor"],
    ]
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 2.4)
    for j in range(len(cols)):
        c = tbl[0, j]; c.set_facecolor(NAVY); c.set_text_props(color="white", fontweight="bold")
    ax.set_title("Anatomy of a Control Plan", fontsize=14, pad=14)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def oc_curve(path):
    from math import comb
    n, c = 50, 2
    ps = np.linspace(0, 0.16, 220)
    Pa = np.array([sum(comb(n, k) * p**k * (1 - p)**(n - k) for k in range(c + 1)) for p in ps])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ps * 100, Pa, color=NAVY, lw=2.4)
    aql = ps[np.argmin(np.abs(Pa - 0.95))] * 100
    rql = ps[np.argmin(np.abs(Pa - 0.10))] * 100
    ax.axvline(aql, color=GREEN, ls="--", lw=1.2); ax.axvline(rql, color=RED, ls="--", lw=1.2)
    ax.axhline(0.95, color=GREEN, ls=":", lw=1); ax.axhline(0.10, color=RED, ls=":", lw=1)
    ax.annotate(f"AQL ≈ {aql:.1f}%\n(α = producer's risk)", (aql, 0.95), (aql + 2, 0.78),
                color=GREEN, fontsize=9, arrowprops=dict(arrowstyle="->", color=GREEN))
    ax.annotate(f"RQL/LTPD ≈ {rql:.1f}%\n(β = consumer's risk)", (rql, 0.10), (rql + 1, 0.28),
                color=RED, fontsize=9, arrowprops=dict(arrowstyle="->", color=RED))
    ax.set_xlabel("Incoming lot quality (% defective)")
    ax.set_ylabel("Probability of accepting the lot")
    ax.set_title(f"Operating-Characteristic (OC) Curve  (n={n}, accept if ≤ {c} defective)")
    ax.set_ylim(0, 1.02)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def iq_oq_pq(path):
    _flow(path, ["DQ\nDesign\nQualification", "IQ\nInstallation\nQualification",
                 "OQ\nOperational\nQualification", "PQ\nPerformance\nQualification"],
          "Process Validation: DQ → IQ → OQ → PQ")


def doe_interaction(path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.3), sharey=True)
    A = [0, 1]
    ax1.plot(A, [2, 4], "-o", color=NAVY, label="B low")
    ax1.plot(A, [3, 5], "-o", color=RED, label="B high")
    ax1.set_title("No interaction\n(parallel lines)")
    ax2.plot(A, [2, 5], "-o", color=NAVY, label="B low")
    ax2.plot(A, [5, 2.5], "-o", color=RED, label="B high")
    ax2.set_title("Interaction\n(lines cross / diverge)")
    for ax in (ax1, ax2):
        ax.set_xticks([0, 1]); ax.set_xticklabels(["A low", "A high"])
        ax.set_xlabel("Factor A"); ax.legend(fontsize=9); ax.grid(alpha=0.25)
    ax1.set_ylabel("Response")
    fig.suptitle("Interaction Plots — why one-factor-at-a-time fails", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(path, dpi=DPI); plt.close(fig)


def doe_cube(path):
    fig, ax = plt.subplots(figsize=(6.6, 6))
    ax.axis("off"); ax.set_xlim(-0.6, 3.6); ax.set_ylim(-0.6, 3.4)

    def P(a, b, c):
        return (a * 1.7 + c * 0.95, b * 1.7 + c * 0.6)
    corners = {(a, b, c): P(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)}
    for (a, b, c), (x, y) in corners.items():
        for (da, db, dc) in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
            n = (a + da, b + db, c + dc)
            if n in corners:
                x2, y2 = corners[n]
                ax.plot([x, x2], [y, y2], color="#9fb4cc", lw=1.4, zorder=1)
    for (a, b, c), (x, y) in corners.items():
        ax.plot(x, y, "o", color=NAVY, ms=10, zorder=3)
        sign = lambda v: "+" if v else "−"
        ax.text(x, y + 0.16, f"({sign(a)}{sign(b)}{sign(c)})", ha="center", fontsize=10, zorder=4)
    o = P(0, 0, 0)
    for corner, col, lab, off in [((1, 0, 0), BLUE, "A", (0.15, -0.28)),
                                  ((0, 1, 0), GREEN, "B", (-0.32, 0.0)),
                                  ((0, 0, 1), "#d06f1a", "C", (0.34, 0.12))]:
        tip = P(*corner)
        mid = ((o[0] + tip[0]) / 2, (o[1] + tip[1]) / 2)
        ax.annotate("", tip, o, arrowprops=dict(arrowstyle="->", color=col, lw=2), zorder=2)
        ax.text(mid[0] + off[0], mid[1] + off[1], lab, color=col, fontsize=14, fontweight="bold")
    ax.set_title("Full Factorial 2³ — all 8 factor combinations\n(− = low, + = high for A,B,C)", fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def msa_components(path):
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis("off")

    def box(x, y, w, h, text, color, fs=10):
        ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="white"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                color="white", fontsize=fs, fontweight="bold")

    box(4, 6.7, 4, 1, "Total Measurement\nSystem Variation", NAVY)
    box(1.3, 4.5, 3.4, 1, "Location\n(Accuracy)", BLUE)
    box(7.3, 4.5, 3.4, 1, "Spread\n(Precision)", "#2e9e7f")
    ax.plot([6, 3.0], [6.7, 5.5], color="#999", lw=1.3)
    ax.plot([6, 9.0], [6.7, 5.5], color="#999", lw=1.3)
    acc = [("Bias", 0.3), ("Linearity", 2.0), ("Stability", 3.7)]
    for t, x in acc:
        box(x, 2.3, 1.55, 0.95, t, "#6fa8dc", 9)
        ax.plot([3.0, x + 0.77], [4.5, 3.25], color="#999", lw=1.1)
    prec = [("Repeatability\n(equipment, EV)", 6.6), ("Reproducibility\n(appraiser, AV)", 8.9)]
    for t, x in prec:
        box(x, 2.3, 2.1, 0.95, t, "#52b39a", 8.5)
        ax.plot([9.0, x + 1.05], [4.5, 3.25], color="#999", lw=1.1)
    ax.text(6, 1.4, "Plus resolution/discrimination — the gauge must read fine enough to see the variation",
            ha="center", fontsize=9, style="italic", color="#444")
    ax.set_title("Anatomy of Measurement Error", fontsize=15)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def variation_algorithm(path):
    _flow(path, ["1 Define\nproblem\n+ baseline", "2 Check\nmeasurement\nsystem",
                 "3 Find the\ndominant\ncause", "4 Assess\nfeasibility",
                 "5 Apply a\nreduction\napproach", "6 Validate &\nhold the\ngains"],
          "Statistical Engineering — Variation-Reduction Algorithm")


def variation_families(path):
    # multivari chart: 4 time points x 3 parts x 3 within-part positions
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    times = ["8:00", "10:00", "12:00", "14:00"]
    rng = np.random.default_rng(3)
    x = 0
    for ti, t in enumerate(times):
        base = 50 + rng.normal(0, 0.6)          # small time-to-time family
        for p in range(3):
            pmean = base + (p - 1) * 3.2 + rng.normal(0, 0.3)   # large part-to-part family
            pts = pmean + rng.normal(0, 0.4, 3)                  # small within-part family
            xs = [x, x, x]
            ax.plot([x, x], [pts.min(), pts.max()], color=BLUE, lw=1.4)
            ax.plot(xs, pts, "o", color=NAVY, ms=4)
            ax.plot(x, pmean, "_", color=RED, ms=16, mew=2)
            x += 1
        x += 0.6
    ax.set_title("Families of Variation (multivari)")
    ax.set_ylabel("Measurement")
    ax.set_xticks([1, 4.6, 8.2, 11.8])
    ax.set_xticklabels(times)
    ax.set_xlabel("Time  →  (each cluster = 3 parts; dashes = part means)")
    ax.text(0.02, 0.97, "Part-to-part = big\nWithin-part & time-to-time = small\n→ hunt the cause in the part-to-part family",
            transform=ax.transAxes, va="top", fontsize=9.5,
            bbox=dict(boxstyle="round", fc="#fff2cc", ec="#bf9000"))
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


DIAGRAMS = {
    "doe_interaction": doe_interaction,
    "doe_cube": doe_cube,
    "msa_components": msa_components,
    "oc_curve": oc_curve,
    "iq_oq_pq": iq_oq_pq,
    "variation_algorithm": variation_algorithm,
    "variation_families": variation_families,
    "histogram": histogram,
    "pareto": pareto,
    "variation_causes": variation_causes,
    "p_chart": p_chart,
    "stress_strain": stress_strain,
    "accuracy_precision": accuracy_precision,
    "gauge_rr": gauge_rr,
    "fishbone": fishbone,
    "vision_pipeline": vision_pipeline,
    "gdt_zone_compare": gdt_zone_compare,
    "gdt_form": gdt_form,
    "gdt_orientation": gdt_orientation,
    "gdt_runout": gdt_runout,
    "fmea_7step": fmea_7step,
    "sevenD_flow": sevenD_flow,
    "control_plan": control_plan,
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, fn in DIAGRAMS.items():
        fn(OUT_DIR / f"{key}.png")
        print(f"  {key}")
    print(f"\nWrote {len(DIAGRAMS)} more diagrams to {OUT_DIR}")


if __name__ == "__main__":
    main()
