"""Generate the paper's figures (PDF) and key-number fragments from the study CSVs.

Reads report/data/*.csv (tidy per-design KPI means from the Hopper studies) and writes
report/figures/*.pdf. Every number the paper cites is also printed here so it can be traced.

    PYTHONPATH=src python tools/make_figures.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker

DATA = Path("report/data")
FIG = Path("report/figures")
FIG.mkdir(parents=True, exist_ok=True)
NREP = 300  # reps per design (for binomial CIs)

# Muted, print-friendly palette; diverging map reserved for the phase diagram.
BLUE, RED, AMBER, GREEN = "#2f6fed", "#e5484d", "#e8912a", "#1f9d57"
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9.5,
    "axes.titlesize": 10,
    "axes.labelsize": 9.5,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
})


def _ci(p, n=NREP):
    return 1.96 * np.sqrt(np.clip(p, 0, 1) * (1 - np.clip(p, 0, 1)) / n)


def fig_centerpiece_phase() -> None:
    d = pd.read_csv(DATA / "centerpiece_direct.csv")
    s = pd.read_csv(DATA / "centerpiece_supervisory.csv")
    m = d.merge(s, on=["comms_level", "n_blue"], suffixes=("_d", "_s"))
    m["delta"] = (m["success_rate_s"] - m["success_rate_d"]) * 100
    piv = m.pivot(index="n_blue", columns="comms_level", values="delta").sort_index()
    spans, comms = piv.index.values, piv.columns.values
    Z = piv.values

    fig, ax = plt.subplots(figsize=(5.4, 3.5))
    vmax = np.abs(Z).max()
    im = ax.imshow(Z, origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto",
                   extent=[comms.min() - .5, comms.max() + .5, -0.5, len(spans) - 0.5])
    ax.set_yticks(range(len(spans)))
    ax.set_yticklabels([f"1:{n}" for n in spans])
    ax.set_xticks(comms)
    ax.set_xlabel("Comms / EW degradation level (C0 clear $\\rightarrow$ C5 severe)")
    ax.set_ylabel("Span of control (operator : assets)")
    for i, n in enumerate(spans):
        for j, c in enumerate(comms):
            v = Z[i, j]
            ax.text(c, i, f"{v:+.0f}", ha="center", va="center", fontsize=7.5,
                    color="white" if abs(v) > 0.55 * vmax else "#222")
    # moving-optimum boundary: delta = 0 contour on a refined grid
    cc, nn = np.meshgrid(comms, np.arange(len(spans)))
    ax.contour(cc, nn, Z, levels=[0], colors="k", linewidths=1.6)
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("Supervisory $-$ Direct  success (pp)")
    bbox = dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.72)
    ax.text(0.15, 0.55, "direct\n(human in loop)\nwins", fontsize=7.5, color="#12429c",
            ha="left", va="center", bbox=bbox)
    ax.text(2.35, 4.75, "supervisory (autonomy) wins", fontsize=7.5, color="#8c1c22",
            ha="center", va="center", bbox=bbox)
    ax.set_title("Moving optimum: when to hand control to on-platform autonomy")
    fig.savefig(FIG / "centerpiece_phase.pdf")
    fig.savefig(FIG / "centerpiece_phase.png", dpi=170)
    plt.close(fig)
    # key numbers
    print("[centerpiece] crossover C* (first comms where supervisory >= direct) per span:")
    for n in spans:
        sub = m[m["n_blue"] == n].sort_values("comms_level")
        star = sub[sub["delta"] >= 0]["comms_level"].min()
        print(f"   1:{n}  C*={'never' if pd.isna(star) else int(star)}")


def fig_centerpiece_curves() -> None:
    d = pd.read_csv(DATA / "centerpiece_direct.csv")
    s = pd.read_csv(DATA / "centerpiece_supervisory.csv")
    spans = [2, 4, 8]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.7), sharey=True)
    for ax, n in zip(axes, spans):
        dd = d[d["n_blue"] == n].sort_values("comms_level")
        ss = s[s["n_blue"] == n].sort_values("comms_level")
        for df, col, lab, mk in [(dd, BLUE, "direct", "o"), (ss, RED, "supervisory", "s")]:
            p = df["success_rate"].values
            ax.plot(df["comms_level"], p * 100, color=col, marker=mk, ms=4, label=lab, lw=1.6)
            ax.fill_between(df["comms_level"], (p - _ci(p)) * 100, (p + _ci(p)) * 100,
                            color=col, alpha=0.15, lw=0)
        ax.set_title(f"span 1:{n}")
        ax.set_xlabel("comms level")
        ax.set_xticks(range(6))
    axes[0].set_ylabel("mission success (%)")
    axes[0].legend(loc="upper right")
    axes[0].set_ylim(0, 100)
    fig.suptitle("Direct control degrades with comms and span; supervisory autonomy is comms-robust",
                 fontsize=9.5, y=1.03)
    fig.savefig(FIG / "centerpiece_curves.pdf")
    fig.savefig(FIG / "centerpiece_curves.png", dpi=170)
    plt.close(fig)


def fig_uc3_frontier() -> None:
    f = pd.read_csv(DATA / "uc3_frontier.csv").sort_values("route_bias")
    # collapse duplicate route_bias (rounding) by averaging
    g = f.groupby("route_bias", as_index=False).mean(numeric_only=True)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.6, 3.1))

    # (a) success and attrition vs route_bias
    a0b = a0.twinx()
    a0.plot(g["route_bias"], g["success_rate"] * 100, color=GREEN, marker="o", ms=3.5, lw=1.7,
            label="success")
    a0b.plot(g["route_bias"], g["blue_losses"], color=RED, marker="s", ms=3.5, lw=1.7,
             label="blue losses")
    a0.set_xlabel("route bias (0 = fast corridor $\\rightarrow$ 1 = defilade)")
    a0.set_ylabel("mission success (%)", color=GREEN)
    a0b.set_ylabel("blue losses (of 8)", color=RED)
    a0.set_ylim(0, 100); a0b.set_ylim(0, 8)
    a0.tick_params(axis="y", colors=GREEN); a0b.tick_params(axis="y", colors=RED)
    a0.set_title("(a) Survivability rises with cover")
    a0b.grid(False)

    # (b) tempo vs attrition Pareto frontier, colored by route_bias
    sc = a1.scatter(g["t_obj_success"], g["blue_losses"], c=g["route_bias"], cmap="viridis",
                    s=30, zorder=3, edgecolor="k", linewidth=0.3)
    a1.plot(g["t_obj_success"], g["blue_losses"], color="#888", lw=0.8, zorder=2)
    a1.set_xlabel("time to objective when successful (s)")
    a1.set_ylabel("blue losses (of 8)")
    a1.set_title("(b) Speed$-$survivability frontier")
    cb = fig.colorbar(sc, ax=a1, pad=0.02); cb.set_label("route bias")
    fig.savefig(FIG / "uc3_frontier.pdf")
    fig.savefig(FIG / "uc3_frontier.png", dpi=170)
    plt.close(fig)
    lo, hi = g.iloc[0], g.iloc[-1]
    print(f"[uc3] rb0.0: success={lo.success_rate*100:.0f}% loss={lo.blue_losses:.1f} "
          f"t={lo.t_obj_success:.0f}s | rb1.0: success={hi.success_rate*100:.0f}% "
          f"loss={hi.blue_losses:.1f} t={hi.t_obj_success:.0f}s")


def fig_uc5() -> None:
    path = DATA / "uc5_swarm_jam.csv"
    if not path.exists():
        print("[uc5] CSV not present yet - skipping (re-run after Hopper retune)")
        return
    u = pd.read_csv(path)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.6, 3.1))
    comms_show = sorted(u["comms_level"].unique())
    cmap = plt.cm.viridis(np.linspace(0, 0.9, len(comms_show)))
    for c, col in zip(comms_show, cmap):
        sub = u[u["comms_level"] == c].sort_values("n_uas")
        a0.plot(sub["n_uas"], sub["detection_coverage"], marker="o", ms=3.5, color=col, lw=1.5,
                label=f"C{c}")
        a1.plot(sub["n_uas"], sub["success_rate"] * 100, marker="o", ms=3.5, color=col, lw=1.5,
                label=f"C{c}")
    a0.set_xlabel("swarm size (UAS)"); a0.set_ylabel("detection coverage")
    a0.set_title("(a) Coverage: diminishing returns + jam collapse")
    a1.set_xlabel("swarm size (UAS)"); a1.set_ylabel("mission success (%)")
    a1.set_title("(b) Cued assault outcome")
    a1.legend(title="comms", ncol=2, loc="best")
    a0.set_ylim(0, 1); a1.set_ylim(0, 100)
    fig.savefig(FIG / "uc5_swarm_jam.pdf")
    fig.savefig(FIG / "uc5_swarm_jam.png", dpi=170)
    plt.close(fig)
    print("[uc5] figure written")


def main() -> None:
    fig_centerpiece_phase()
    fig_centerpiece_curves()
    fig_uc3_frontier()
    fig_uc5()
    print("figures ->", FIG)


if __name__ == "__main__":
    main()
