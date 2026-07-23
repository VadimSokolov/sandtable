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
from matplotlib.colors import BoundaryNorm, ListedColormap

from sandtable import bayes_te as bt

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
    # moving-optimum boundary: the delta = 0 crossover. Draw only the longest contour segment, so
    # the tiny near-zero island around a single cell (within Monte-Carlo noise) is not shown.
    cc, nn = np.meshgrid(comms, np.arange(len(spans)))
    segs = ax.contour(cc, nn, Z, levels=[0], alpha=0).allsegs[0]
    if len(segs):
        main = max(segs, key=lambda p: np.hypot(*np.diff(p, axis=0).T).sum())
        ax.plot(main[:, 0], main[:, 1], color="k", lw=1.7, zorder=5)
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("Supervisory $-$ Direct  success (pp)")
    # opaque label boxes (so the contour cannot show through), placed clear of the crossover
    lbl = dict(fontsize=7.5, ha="center", va="center", zorder=6,
               bbox=dict(boxstyle="round,pad=0.26", fc="white", ec="none"))
    ax.text(0.0, 1.5, "direct control\nwins", color="#12429c", **lbl)
    ax.text(2.35, 4.75, "supervisory autonomy wins", color="#8c1c22", **lbl)
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
        ax.set_xlabel("comms / EW level")
        ax.set_xticks(range(6))
        ax.set_xticklabels([f"C{i}" for i in range(6)])
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

    # (a) success and attrition vs route_bias. Colorblind-safe pair (blue vs amber), and the two
    # series also differ by marker (o vs s), so hue is never the sole channel.
    a0b = a0.twinx()
    a0.plot(g["route_bias"], g["success_rate"] * 100, color=BLUE, marker="o", ms=3.5, lw=1.7,
            label="success")
    a0b.plot(g["route_bias"], g["blue_losses"], color=AMBER, marker="s", ms=3.5, lw=1.7,
             label="blue losses")
    a0.set_xlabel("route bias (0 = fast corridor $\\rightarrow$ 1 = defilade)")
    a0.set_ylabel("mission success (%)", color=BLUE)
    a0b.set_ylabel("blue losses (of 8)", color=AMBER)
    a0.set_ylim(0, 100); a0b.set_ylim(0, 8)
    a0.tick_params(axis="y", colors=BLUE); a0b.tick_params(axis="y", colors=AMBER)
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


def fig_killweb_sweeps() -> None:
    """Two opt-in kill-web mechanics on UC-3, each swept from its off state. Both panels share the
    convention: amber = attacker losses (left axis), blue = mission success (right axis)."""
    sp, mp = DATA / "suppression_sweep.csv", DATA / "munitions_sweep.csv"
    if not (sp.exists() and mp.exists()):
        print("[killweb] sweep CSVs not present - skipping (run tools/make_killweb_numbers.py)")
        return
    S = pd.read_csv(sp).sort_values("supp_fire")
    M = pd.read_csv(mp).sort_values("ammo_load")
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.6, 3.1))

    # (a) suppression strength. supp_fire = 0 is byte-identical to the fixed-Pk baseline.
    a0b = a0.twinx()
    a0.plot(S["supp_fire"], S["blue_losses"], color=AMBER, marker="s", ms=3.5, lw=1.7)
    a0b.plot(S["supp_fire"], S["success"] * 100, color=BLUE, marker="o", ms=3.5, lw=1.7)
    a0.set_xlabel("suppression strength (0 = off)")
    a0.set_ylabel("blue losses (of 8)", color=AMBER)
    a0b.set_ylabel("mission success (%)", color=BLUE)
    a0.set_ylim(0, 8); a0b.set_ylim(0, 100)
    a0.tick_params(axis="y", colors=AMBER); a0b.tick_params(axis="y", colors=BLUE)
    a0.set_title("(a) Suppression aids the maneuver force")
    a0b.grid(False)

    # (b) defender basic load (log). ammo -> inf recovers the fixed-Pk baseline (dashed).
    a1b = a1.twinx()
    a1.plot(M["ammo_load"], M["blue_losses"], color=AMBER, marker="s", ms=3.5, lw=1.7)
    a1b.plot(M["ammo_load"], M["success"] * 100, color=BLUE, marker="o", ms=3.5, lw=1.7)
    base = float(M[M.ammo_load == M.ammo_load.max()]["blue_losses"].iloc[0])
    a1.axhline(base, ls="--", lw=1.0, color="#888")
    a1.text(M["ammo_load"].min() * 1.1, base - 0.5, "fixed-Pk baseline\n(ammo $\\rightarrow\\infty$)",
            fontsize=7.0, color="#555", va="top")
    a1.set_xscale("log")
    a1.set_xlabel("defender basic load (rounds)")
    a1.set_ylabel("blue losses (of 8)", color=AMBER)
    a1b.set_ylabel("mission success (%)", color=BLUE)
    a1.set_ylim(0, 8); a1b.set_ylim(0, 100)
    a1.tick_params(axis="y", colors=AMBER); a1b.tick_params(axis="y", colors=BLUE)
    a1.set_title("(b) Munitions set a sustainment ceiling")
    a1b.grid(False)

    fig.savefig(FIG / "killweb_sweeps.pdf")
    fig.savefig(FIG / "killweb_sweeps.png", dpi=170)
    plt.close(fig)
    sf0, sf1 = S.iloc[0], S.iloc[-1]
    print(f"[killweb] suppression: loss {sf0.blue_losses:.1f}->{sf1.blue_losses:.1f}, "
          f"success {sf0.success*100:.0f}%->{sf1.success*100:.0f}%")
    print(f"[killweb] munitions: loss {M.iloc[0].blue_losses:.1f} (ammo {int(M.iloc[0].ammo_load)}) "
          f"-> {M.iloc[-1].blue_losses:.1f} (ammo {int(M.iloc[-1].ammo_load)}, = baseline)")


def fig_bayes_te() -> None:
    """Bayesian test-and-evaluation. (a) The decision chart: for every (trials, successes) state, the
    cost-aware rule says accept, reject, or keep testing, with three example designs' evidence walks
    overlaid to their stopping point. (b) SandTable as a discounted prior: the mean credible-interval
    width starts far tighter and stays tighter across the expensive high-fidelity runs when a cheap M&S
    prior informs the test than when it does not."""
    pp, cp = DATA / "bayes_te_paths.csv", DATA / "bayes_te_prior_curve.csv"
    if not (pp.exists() and cp.exists()):
        print("[bayes_te] CSVs not present - skipping (run tools/make_bayes_te_numbers.py)")
        return
    paths = pd.read_csv(pp)
    n_max = int(paths.k.max() + 1)
    chart = bt.decision_chart(n_max, cost=0.02, util=bt.Utility(p_cut=0.60))

    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.6, 3.2))

    # (a) decision chart over (trials n = h+m, successes h); color by action.
    grid = np.full((n_max + 1, n_max + 1), np.nan)      # grid[h, n]
    for n in range(n_max + 1):
        for h in range(n + 1):
            grid[h, n] = chart[h, n - h]
    cmap = ListedColormap([RED, GREEN, "#d6d6d6"])       # 0 reject, 1 accept, 2 test
    a0.imshow(grid, origin="lower", aspect="auto", cmap=cmap,
              norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N), interpolation="nearest")
    gx = np.arange(n_max + 1)
    for val, ec in [(1, "#0f5c33"), (0, "#7a1015")]:     # outline accept/reject: an edge cue that survives colorblindness
        a0.contour(gx, gx, (grid == val).astype(float), levels=[0.5], colors=ec, linewidths=0.9)
    stop = pd.read_csv(DATA / "bayes_te_stopping.csv")
    nused = stop[stop.cost == stop.cost.min()].set_index("design")["n_used"].to_dict()
    styles = {"compliant": ("-", BLUE, "compliant (accept)"),
              "borderline": ("--", "#111", "borderline (reject)"),
              "noncompliant": ("-.", "#8a5000", "failing (reject)")}
    zoom = 34                                            # walks stop early; crop to the decision region (grid runs to n_max)
    for name, sub in paths.groupby("design"):
        sub = sub.sort_values("k")
        sub = sub[sub.k <= int(nused[name])]
        ls, col, disp = styles.get(name, ("-", "#333", name))
        a0.plot(sub.k, sub.hits, ls, color=col, lw=1.9, label=disp)
        a0.plot(sub.k.iloc[-1], sub.hits.iloc[-1], "o", color=col, ms=6, zorder=5)
    a0.set_xlim(0, zoom); a0.set_ylim(0, zoom)
    a0.set_xlabel("trials"); a0.set_ylabel("successes")
    a0.set_title("(a) Decision chart and evidence walks")
    a0.legend(loc="upper left", fontsize=7.5, frameon=True, facecolor="white", framealpha=0.9)
    a0.grid(False)
    a0.text(0.58 * zoom, 0.50 * zoom, "accept", color="#0f5c33", fontsize=9, rotation=45,
            ha="center", va="center")
    a0.text(0.73 * zoom, 0.15 * zoom, "reject", color="#7a1015", fontsize=9)
    a0.text(0.47 * zoom, 0.27 * zoom, "test", color="#555", fontsize=8.5, rotation=45,
            ha="center", va="center")

    # (b) credible-interval width vs number of high-fidelity runs: informed vs uninformed prior.
    cur = pd.read_csv(cp).sort_values("k")
    a1.plot(cur.k, cur.width_uninformed, color=RED, marker="o", ms=3, lw=1.6,
            label="high-fidelity only")
    a1.plot(cur.k, cur.width_informed, color=BLUE, marker="s", ms=3, lw=1.6,
            label="M&S-informed prior")
    a1.set_xlabel("high-fidelity runs")
    a1.set_ylabel("mean 95\\% CrI width")
    a1.set_ylim(0, None)
    a1.set_title("(b) A cheap prior sharpens costly tests")
    a1.legend(loc="upper right")

    fig.savefig(FIG / "bayes_te.pdf")
    fig.savefig(FIG / "bayes_te.png", dpi=170)
    plt.close(fig)
    print(f"[bayes_te] chart n_max={n_max}; CrI width at k=0 informed "
          f"{cur.iloc[0].width_informed:.2f} vs uninformed {cur.iloc[0].width_uninformed:.2f}")


def fig_drone() -> None:
    """Drone-war increment. (a) The EW-immune command link (M1) keeps direct human control from
    collapsing as the comms/EW ladder worsens. (b) Counter-UAS/SHORAD (M2) turns the sensor-swarm
    response from monotone-in-size into an interior optimum; the cost-exchange (M3, amber, right axis)
    peaks at the same place and collapses for oversized swarms."""
    fp, cp = DATA / "drone_fiber_link.csv", DATA / "drone_cuas_swarm.csv"
    if not (fp.exists() and cp.exists()):
        print("[drone] CSVs not present - skipping (run tools/make_drone_numbers.py)")
        return
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.6, 3.1))

    # (a) EW-immune command link across the comms/EW ladder.
    F = pd.read_csv(fp)
    nf = int(F["n_rep"].iloc[0])
    piv = F.pivot(index="comms_level", columns="link", values="success")
    x = piv.index.values
    for link, col, mk, ls in [("jammable", RED, "o", "-"), ("immune", GREEN, "s", "-")]:
        y = piv[link].values * 100
        ci = _ci(piv[link].values, nf) * 100
        a0.plot(x, y, color=col, marker=mk, ms=4, lw=1.8, ls=ls,
                label=("jammable link" if link == "jammable" else "EW-immune link"))
        a0.fill_between(x, y - ci, y + ci, color=col, alpha=0.14)
    a0.set_xlabel("comms / EW level (C0 clear $\\rightarrow$ C5 severe)")
    a0.set_ylabel("direct-control success (%)")
    a0.set_ylim(0, 100); a0.set_xticks(x)
    a0.legend(loc="lower left")
    a0.set_title("(a) EW-immune link resists jamming")

    # (b) Counter-UAS makes swarm size an interior optimum; cost-exchange on the right axis.
    C = pd.read_csv(cp)
    nc = int(C["n_rep"].iloc[0])
    off = C[C.cuas == "off"].sort_values("n_uas").reset_index(drop=True)
    on = C[C.cuas == "on"].sort_values("n_uas").reset_index(drop=True)
    xs = on["n_uas"].values
    for df, col, mk, ls, lab in [(off, BLUE, "o", "--", "unopposed"), (on, RED, "s", "-", "counter-UAS")]:
        y = df["success"].values * 100
        ci = _ci(df["success"].values, nc) * 100
        a1.plot(df["n_uas"], y, color=col, marker=mk, ms=4, lw=1.8, ls=ls, label=lab)
        a1.fill_between(df["n_uas"], y - ci, y + ci, color=col, alpha=0.13)
    pk = int(on["n_uas"][on["success"].idxmax()])
    a1.axvline(pk, color=RED, ls=":", lw=1.0, alpha=0.6)
    a1.set_xlabel("recon swarm size (UAS)")
    a1.set_ylabel("mission success (%)")
    a1.set_ylim(0, 100); a1.set_xticks(xs)
    a1.legend(loc="upper left")
    a1b = a1.twinx()
    a1b.plot(on["n_uas"], on["cost_exchange"], color=AMBER, marker="^", ms=3.5, lw=1.5)
    a1b.set_ylabel("cost-exchange (C-UAS)", color=AMBER)
    a1b.tick_params(axis="y", colors=AMBER)
    a1b.set_ylim(bottom=0)
    a1b.grid(False)
    a1.set_title("(b) Counter-UAS: interior optimum")

    fig.savefig(FIG / "drone.pdf")
    fig.savefig(FIG / "drone.png", dpi=170)
    plt.close(fig)
    print(f"[drone] fiber: jammable {piv['jammable'].iloc[0]*100:.0f}%->{piv['jammable'].iloc[-1]*100:.0f}%, "
          f"immune {piv['immune'].iloc[0]*100:.0f}%->{piv['immune'].iloc[-1]*100:.0f}% across C0->C5")
    print(f"[drone] swarm optimum (C-UAS) at size {pk}: success "
          f"{on['success'].max()*100:.0f}%, oversized {on['success'].iloc[-1]*100:.0f}%")


def main() -> None:
    fig_centerpiece_phase()
    fig_centerpiece_curves()
    fig_uc3_frontier()
    fig_uc5()
    fig_killweb_sweeps()
    fig_bayes_te()
    fig_drone()
    print("figures ->", FIG)


if __name__ == "__main__":
    main()
