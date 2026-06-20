"""Generate canonical QE teaching diagrams as PNGs.

Run with: python3 media/diagrams.py
Writes one PNG per diagram into media/diagrams/ and prints a manifest.

Each generator is a function f(path) -> None that draws one diagram. The DIAGRAMS
registry maps a stable key -> (generator, human title). Topics in content/*.json
reference these by key via their "media.image" field (path media/diagrams/<key>.png).
"""
import matplotlib
matplotlib.use("Agg")  # headless: no display needed
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrow
import numpy as np
from pathlib import Path

OUT_DIR = Path(__file__).parent / "diagrams"
DPI = 150
np.random.seed(7)  # reproducible charts

# Phone-friendly defaults
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 13,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.25,
})


# ---------------------------------------------------------------------------
# SPC: X-bar and R control chart with an out-of-control point
# ---------------------------------------------------------------------------
def spc_xbar_r(path):
    n = 5                       # subgroup size
    A2, D3, D4 = 0.577, 0.0, 2.114   # control-chart constants for n=5
    k = 20                      # subgroups
    means = 10 + np.random.normal(0, 0.08, k)
    ranges = np.abs(np.random.normal(0.30, 0.06, k))
    means[13] = 10.46           # force one point above UCL to flag a rule violation
    ranges[7] = 0.62

    xbar = means.mean()
    rbar = ranges.mean()
    ucl_x, lcl_x = xbar + A2 * rbar, xbar - A2 * rbar
    ucl_r, lcl_r = D4 * rbar, D3 * rbar
    x = np.arange(1, k + 1)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.4), sharex=True)

    def draw(ax, y, cl, ucl, lcl, title, ylab):
        ax.plot(x, y, "-o", color="#1f4e79", ms=5, lw=1.4, zorder=3)
        ooc = (y > ucl) | (y < lcl)
        ax.plot(x[ooc], y[ooc], "o", color="#c00000", ms=10, zorder=4,
                label="out of control")
        ax.axhline(cl, color="#2e7d32", lw=1.6)
        ax.axhline(ucl, color="#c00000", ls="--", lw=1.4)
        ax.axhline(lcl, color="#c00000", ls="--", lw=1.4)
        ax.text(k + 0.3, ucl, "UCL", color="#c00000", va="center", fontsize=11)
        ax.text(k + 0.3, lcl, "LCL", color="#c00000", va="center", fontsize=11)
        ax.text(k + 0.3, cl, "CL", color="#2e7d32", va="center", fontsize=11)
        ax.set_title(title)
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.25)
        if ooc.any():
            ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    draw(ax1, means, xbar, ucl_x, lcl_x,
         "X̄ (subgroup-mean) chart", "Mean")
    draw(ax2, ranges, rbar, ucl_r, lcl_r,
         "R (subgroup-range) chart", "Range")
    ax2.set_xlabel("Subgroup #")
    fig.suptitle("SPC Control Chart  (n = 5 per subgroup)", fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Process capability: histogram + normal fit vs spec limits, Cp / Cpk
# ---------------------------------------------------------------------------
def process_capability(path):
    LSL, USL, target = 9.6, 10.4, 10.0
    mu, sigma = 10.08, 0.10          # off-center on purpose -> Cpk < Cp
    data = np.random.normal(mu, sigma, 500)
    Cp = (USL - LSL) / (6 * sigma)
    Cpk = min(USL - mu, mu - LSL) / (3 * sigma)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(data, bins=30, density=True, color="#cfe2f3", edgecolor="#9fc5e8")
    xs = np.linspace(LSL - 0.3, USL + 0.3, 400)
    ax.plot(xs, np.exp(-0.5 * ((xs - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi)),
            color="#1f4e79", lw=2)
    for val, lab, col in [(LSL, "LSL", "#c00000"), (USL, "USL", "#c00000"),
                          (target, "Target", "#2e7d32"), (mu, "μ", "#1f4e79")]:
        ax.axvline(val, color=col, ls="--", lw=1.6)
        ax.text(val, ax.get_ylim()[1] * 0.92, lab, color=col, ha="center", fontsize=11)
    ax.set_title("Process Capability")
    ax.set_xlabel("Measurement")
    ax.set_ylabel("Density")
    ax.text(0.02, 0.97,
            f"Cp  = {Cp:.2f}   (spread vs. tolerance)\n"
            f"Cpk = {Cpk:.2f}   (centering-penalized)\n"
            f"Cpk < Cp → process is off-center",
            transform=ax.transAxes, va="top", fontsize=11,
            bbox=dict(boxstyle="round", fc="#fff2cc", ec="#bf9000"))
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Empirical rule: 68-95-99.7 under the normal curve
# ---------------------------------------------------------------------------
def empirical_rule(path):
    xs = np.linspace(-4, 4, 500)
    ys = np.exp(-0.5 * xs ** 2) / np.sqrt(2 * np.pi)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(xs, ys, color="#1f4e79", lw=2)
    bands = [(-1, 1, "#1f4e79", "68.2%"), (-2, -1, "#3d85c6", "95.4%"),
             (1, 2, "#3d85c6", None), (-3, -2, "#9fc5e8", "99.7%"),
             (2, 3, "#9fc5e8", None)]
    for lo, hi, col, lab in bands:
        m = (xs >= lo) & (xs <= hi)
        ax.fill_between(xs[m], ys[m], color=col, alpha=0.55)
    ax.annotate("68.2%", (0, 0.18), ha="center", fontsize=12, color="white", fontweight="bold")
    ax.annotate("95.4%", (0, 0.045), ha="center", fontsize=11)
    ax.annotate("99.7%", (0, 0.012), ha="center", fontsize=10)
    ax.set_xticks(range(-3, 4))
    ax.set_xticklabels([f"{s}σ" for s in range(-3, 4)])
    ax.set_yticks([])
    ax.set_title("The Empirical Rule (68–95–99.7)")
    ax.set_xlabel("Standard deviations from the mean")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# GD&T feature control frame (drawn as primitives) + tolerance-zone note
# ---------------------------------------------------------------------------
def gdt_position_frame(path):
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # compartment widths along a single row
    comps = [1.6, 2.6, 1.2, 1.2, 1.2]   # symbol | tolerance | A | B | C
    labels = [None, None, "A", "B", "C"]  # tolerance compartment drawn specially below
    x0, y0, h = 1.0, 1.4, 1.2
    x = x0
    for w, lab in zip(comps, labels):
        ax.add_patch(Rectangle((x, y0), w, h, fill=False, ec="black", lw=2))
        if lab is not None:
            ax.text(x + w / 2, y0 + h / 2, lab, ha="center", va="center", fontsize=15)
        x += w

    # draw the "position" geometric symbol (circle + crosshair) in compartment 1
    cx, cy, r = x0 + comps[0] / 2, y0 + h / 2, 0.34
    ax.add_patch(Circle((cx, cy), r, fill=False, ec="black", lw=2))
    ax.plot([cx - r * 1.4, cx + r * 1.4], [cy, cy], color="black", lw=2)
    ax.plot([cx, cx], [cy - r * 1.4, cy + r * 1.4], color="black", lw=2)

    # tolerance compartment: "Ø0.25" + circled-M (MMC), drawn so it always renders
    tol_cx = x0 + comps[0] + comps[1] / 2
    ax.text(tol_cx - 0.42, cy, "Ø0.25", ha="center", va="center", fontsize=15)
    mmc_cx = tol_cx + 0.74
    ax.add_patch(Circle((mmc_cx, cy), 0.27, fill=False, ec="black", lw=1.8))
    ax.text(mmc_cx, cy, "M", ha="center", va="center", fontsize=12, fontweight="bold")

    # callouts
    ax.annotate("geometric\ncharacteristic\n(Position)", (cx, y0 - 0.1),
                xytext=(cx, 0.2), ha="center", fontsize=9, color="#1f4e79",
                arrowprops=dict(arrowstyle="->", color="#1f4e79"))
    tol_x = x0 + comps[0] + comps[1] / 2
    ax.annotate("Ø tolerance zone + MMC modifier", (tol_x, y0 + h + 0.05),
                xytext=(tol_x, 3.7), ha="center", fontsize=9, color="#1f4e79",
                arrowprops=dict(arrowstyle="->", color="#1f4e79"))
    dat_x = x0 + sum(comps[:2]) + (comps[2] + comps[3] + comps[4]) / 2
    ax.annotate("datum reference frame (primary → tertiary)", (dat_x, y0 - 0.1),
                xytext=(dat_x, 0.2), ha="center", fontsize=9, color="#1f4e79",
                arrowprops=dict(arrowstyle="->", color="#1f4e79"))
    ax.set_title("Reading a GD&T Feature Control Frame", fontsize=15)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# FMEA risk matrix: Severity x Occurrence, with the RPN definition
# ---------------------------------------------------------------------------
def fmea_risk_matrix(path):
    sev = np.arange(1, 11)
    occ = np.arange(1, 11)
    grid = np.outer(occ, sev)          # rows = occurrence, cols = severity
    fig, ax = plt.subplots(figsize=(7.2, 6))
    im = ax.imshow(grid, origin="lower", cmap="RdYlGn_r",
                   extent=[0.5, 10.5, 0.5, 10.5])
    ax.set_xticks(sev)
    ax.set_yticks(occ)
    ax.set_xlabel("Severity (S)")
    ax.set_ylabel("Occurrence (O)")
    ax.set_title("FMEA Risk: Severity × Occurrence")
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("S × O  (higher = act first)")
    ax.text(0.5, -0.18,
            "RPN = Severity × Occurrence × Detection   (1–1000)\n"
            "High S×O = prioritize even before ranking Detection",
            transform=ax.transAxes, ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="#fff2cc", ec="#bf9000"))
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# APQP five phases timeline
# ---------------------------------------------------------------------------
def apqp_phases(path):
    phases = [
        ("1 Plan &\nDefine", "#1f4e79"),
        ("2 Product\nDesign & Dev", "#2e75b6"),
        ("3 Process\nDesign & Dev", "#2e9e7f"),
        ("4 Product & Process\nValidation", "#bf9000"),
        ("5 Feedback,\nAssessment, CA", "#a64d79"),
    ]
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.set_xlim(0, len(phases))
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, (label, col) in enumerate(phases):
        ax.add_patch(Rectangle((i + 0.04, 0.25), 0.92, 0.5, fc=col, ec="white"))
        ax.text(i + 0.5, 0.5, label, ha="center", va="center",
                color="white", fontsize=10.5, fontweight="bold")
        if i < len(phases) - 1:
            ax.annotate("", (i + 1.02, 0.5), (i + 0.96, 0.5),
                        arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.5))
    ax.set_title("APQP — Five Phases of Advanced Product Quality Planning",
                 fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


DIAGRAMS = {
    "spc_xbar_r": (spc_xbar_r, "SPC X̄/R control chart"),
    "process_capability": (process_capability, "Process capability (Cp/Cpk)"),
    "empirical_rule": (empirical_rule, "Empirical rule 68-95-99.7"),
    "gdt_position_frame": (gdt_position_frame, "GD&T feature control frame"),
    "fmea_risk_matrix": (fmea_risk_matrix, "FMEA severity x occurrence matrix"),
    "apqp_phases": (apqp_phases, "APQP five phases"),
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, (fn, title) in DIAGRAMS.items():
        out = OUT_DIR / f"{key}.png"
        fn(out)
        print(f"  {key:22s} -> {out.relative_to(OUT_DIR.parent.parent)}  ({title})")
    print(f"\nWrote {len(DIAGRAMS)} diagrams to {OUT_DIR}")


if __name__ == "__main__":
    main()
