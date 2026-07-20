"""Generate the paper's schematic diagrams and config tables from the code and scenarios.

Unlike tools/make_figures.py (which plots study RESULTS), this script draws the model's STRUCTURE:

  report/figures/architecture.pdf   layered modules + the fixed-step run_mission pipeline
  report/figures/command_model.pdf  direct vs supervisory operator model (the moving-optimum mechanism)
  report/figures/scenarios.pdf      data-driven schematic of the three scenarios (terrain, forces, routes, ranges)
  report/gen/tab_ladder.tex         the C0-C5 comms/EW ladder (from sandtable.comms_ew)
  report/gen/tab_platforms.tex      platform parameters per scenario (from scenarios/*.json)

Everything is derived from the source (module constants, scenario JSONs, the real overwatch_stations
laydown), so the diagrams cannot drift from the simulator.

    PYTHONPATH=src python tools/make_diagrams.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

from sandtable.comms_ew import _LADDER
from sandtable.planning import overwatch_stations
from sandtable.scenario import load_scenario
from sandtable.world import build_world

FIG = Path("report/figures"); FIG.mkdir(parents=True, exist_ok=True)
GEN = Path("report/gen"); GEN.mkdir(parents=True, exist_ok=True)

# Palette shared with make_figures.py, plus soft fills for boxes.
BLUE, RED, AMBER, GREEN, AIR = "#2f6fed", "#e5484d", "#e8912a", "#1f9d57", "#12a89a"
INK, EDGE = "#1c2530", "#8a97a4"
FILL_CORE, FILL_IO, FILL_WRAP = "#eef3fc", "#f4f6f8", "#fbf3e6"
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})


# --------------------------------------------------------------------------- helpers
def _box(ax, x, y, w, h, text, fc=FILL_CORE, ec=EDGE, fs=8.5, bold=False, tc=INK, lw=1.1):
    """Rounded box centered at (x, y) with wrapped text; coordinates are axis units (0..100)."""
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                       boxstyle="round,pad=0.4,rounding_size=1.6",
                       fc=fc, ec=ec, lw=lw, mutation_aspect=0.55)
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold" if bold else "normal", zorder=5, linespacing=1.25)
    return p


def _arrow(ax, x0, y0, x1, y1, color=INK, lw=1.3, rad=0.0, style="-|>", ls="-"):
    a = FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=11,
                        lw=lw, color=color, connectionstyle=f"arc3,rad={rad}",
                        linestyle=ls, zorder=4, shrinkA=2, shrinkB=2)
    ax.add_patch(a)
    return a


def _clean(ax, xlim=(0, 100), ylim=(0, 100)):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")


# --------------------------------------------------------------------------- architecture + loop
def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    _clean(ax)

    # inputs (top)
    _box(ax, 20, 92, 34, 11,
         "Scenario\n(forces, terrain, objective)", fc=FILL_IO, fs=8)
    _box(ax, 55, 92, 20, 11, "seed", fc=FILL_IO, fs=8)
    _box(ax, 82, 92, 30, 11, "design params\n(sweep knobs)", fc=FILL_IO, fs=8)

    # pure-function wrapper container
    wrap = FancyBboxPatch((6, 20), 88, 58, boxstyle="round,pad=0.4,rounding_size=2",
                          fc="none", ec=BLUE, lw=1.4, linestyle=(0, (5, 3)))
    ax.add_patch(wrap)
    ax.text(9, 74, r"run_mission(scenario, seed, params) $\rightarrow$ metrics   "
                   r"$\cdot$   pure function, no global state",
            fontsize=8, style="italic", color=BLUE, ha="left", va="center")

    for x0 in (20, 55, 82):
        _arrow(ax, x0, 86.5, x0 if x0 != 82 else 70, 78, color=EDGE)

    # build state
    _box(ax, 50, 68, 74, 8,
         "build world (terrain rasters: speed, cover, conceal)   +   entities (SoA arrays)",
         fc="#f0f7f2", ec=GREEN, fs=8)
    _arrow(ax, 50, 64, 50, 58.5, color=EDGE)

    # the fixed-step pipeline (5 stages)
    stages = [
        ("C2\ntasking", "#eaf0fc"),
        ("planning\n(routes,\nformation)", "#eaf0fc"),
        ("motion\n(unicycle,\nterrain)", "#eaf0fc"),
        ("sensing\n(shared SA,\nrelay)", "#eaf0fc"),
        ("engagement\n(aimed fire,\nPk)", "#eaf0fc"),
    ]
    xs = np.linspace(17, 83, 5)
    for i, ((label, fc), x) in enumerate(zip(stages, xs)):
        _box(ax, x, 50, 13.5, 12, label, fc=fc, ec=BLUE, fs=7.6, bold=(i == 0))
        if i < 4:
            _arrow(ax, x + 6.9, 50, xs[i + 1] - 6.9, 50, color=INK)
    ax.text(50, 41.5, "each step advances the state in this fixed order   (dt = 1 s)",
            ha="center", va="center", fontsize=7.6, color=INK, style="italic")

    # loop-back arrow (flat arc just above the pipeline row, clears the build-world box)
    _arrow(ax, 82, 56.5, 18, 56.5, color=AMBER, lw=1.4, rad=0.11)
    ax.text(50, 58.7, "for k in steps", ha="center", va="center", fontsize=7.2,
            color="#9a6a12", style="italic")

    # state row read/written by the pipeline
    _box(ax, 50, 30, 80, 8,
         "state: SoA entity arrays  (x, y, heading, hp, seen, control\\_quality, ...)  +  terrain rasters",
         fc="#f7f7f4", ec=EDGE, fs=7.6)
    _arrow(ax, 30, 44, 30, 34, color=EDGE, ls=(0, (2, 2)))
    _arrow(ax, 70, 34, 70, 44, color=EDGE, ls=(0, (2, 2)))
    ax.text(31.5, 39, "read", fontsize=6.6, color=EDGE, ha="left", style="italic")
    ax.text(71.5, 39, "write", fontsize=6.6, color=EDGE, ha="left", style="italic")

    # output
    _arrow(ax, 50, 20, 50, 13.5, color=EDGE)
    _box(ax, 50, 8, 82, 9,
         "mission KPIs: success, blue/red losses, time-to-objective, detection coverage",
         fc=FILL_WRAP, ec=AMBER, fs=8, bold=True)

    # side wrappers
    ax.text(2.5, 49, "evaluate(): average over N seeded replications", rotation=90,
            fontsize=7.2, color="#556", ha="center", va="center", style="italic")
    ax.text(97.5, 49, "polarisopt DOE / BO  $\\rightarrow$  SLURM (Hopper)", rotation=90,
            fontsize=7.2, color="#556", ha="center", va="center", style="italic")

    fig.savefig(FIG / "architecture.pdf")
    fig.savefig(FIG / "architecture.png", dpi=170)
    plt.close(fig)
    print("wrote architecture.pdf")


# --------------------------------------------------------------------------- command model
def fig_command_model() -> None:
    fig, (axd, axs) = plt.subplots(1, 2, figsize=(6.6, 3.1))
    for ax in (axd, axs):
        _clean(ax)

    # ---- direct (human in the loop) ----
    axd.text(50, 96, "Direct control (human in the loop)", ha="center", fontsize=9,
             fontweight="bold", color=BLUE)
    # agents
    for j, y in enumerate(np.linspace(78, 30, 4)):
        _box(axd, 15, y, 16, 8, f"agent {j+1}", fc="#eaf0fc", ec=BLUE, fs=7.2)
    # link
    _box(axd, 50, 54, 20, 15, "comms link\nlatency $\\ell$\ndrop $p$", fc=FILL_WRAP, ec=AMBER, fs=7.4)
    axd.text(50, 43.5, "EW degrades the link", ha="center", fontsize=6.8, color=RED, style="italic")
    # operator server
    _box(axd, 85, 54, 20, 16, "operator\n(single server,\nrate $\\mu$)", fc="#fdeef0", ec=RED, fs=7.4, bold=True)
    # request / reply arrows
    for y in np.linspace(78, 30, 4):
        _arrow(axd, 23, y, 40, 54, color=EDGE, lw=0.9, rad=0.12)
    _arrow(axd, 60, 58, 75, 58, color=INK, lw=1.1)     # to operator
    _arrow(axd, 75, 50, 60, 50, color=INK, lw=1.1)     # reply back
    axd.text(67, 61, "request", fontsize=6.6, color="#556", ha="center")
    axd.text(67, 46.5, "reply", fontsize=6.6, color="#556", ha="center")
    # quality outcomes
    axd.text(50, 20, "resulting control quality", ha="center", fontsize=7.4, style="italic", color=INK)
    axd.text(50, 13.5, "serviced in time: $q_{op}$  ·  waiting: $q_{stall}$", ha="center", fontsize=7.2, color=INK)
    axd.text(50, 7.5, "dropped / timeout: $q_{fallback}$", ha="center", fontsize=7.2, color=INK)

    # ---- supervisory (human on the loop) ----
    axs.text(50, 96, "Supervisory autonomy (on the loop)", ha="center", fontsize=9,
             fontweight="bold", color=GREEN)
    for j, y in enumerate(np.linspace(78, 30, 4)):
        _box(axs, 30, y, 20, 8, f"agent {j+1}", fc="#eef7f1", ec=GREEN, fs=7.2)
        _box(axs, 62, y, 14, 8, "$q_{auto}$", fc="#f0f7f2", ec=GREEN, fs=7.6)
        _arrow(axs, 40.5, y, 54.5, y, color=EDGE, lw=0.9)
    axs.text(50, 20, "decides locally, every step", ha="center", fontsize=7.4, style="italic", color=INK)
    axs.text(50, 13.5, "no queue, no link: steady $q_{auto}$", ha="center", fontsize=7.2, color=INK)
    axs.text(50, 7.5, "comms-invariant", ha="center", fontsize=7.2, color=GREEN, fontweight="bold")

    # attention-dilution formula spanning the bottom
    fig.text(0.5, -0.03,
             r"attention dilution: $q_{op}^{\mathrm{eff}} = q_{auto} + (q_{operator}-q_{auto})\,"
             r"\min(1,\ \kappa/n)$.   More agents $n$ dilute the per-decision quality and lengthen the queue.",
             ha="center", fontsize=7.8, color=INK)
    fig.savefig(FIG / "command_model.pdf")
    fig.savefig(FIG / "command_model.png", dpi=170)
    plt.close(fig)
    print("wrote command_model.pdf")


# --------------------------------------------------------------------------- scenario schematics
def _lane_y(x, bias, gx, gy, size_h, converge=900.0):
    """The route lane y(x) the planner steers along (mirrors planning.step)."""
    corridor_y, covered_y = size_h * 0.5, size_h * 0.78
    lane = (1 - bias) * corridor_y + bias * covered_y
    x_conv = gx - converge
    c = np.clip((x - x_conv) / max(gx - x_conv, 1.0), 0.0, 1.0)
    return lane + (gy - lane) * c


def _draw_world(ax, scn):
    world = build_world(scn, np.random.default_rng(0))
    w, h = scn.size
    ax.imshow(world.cover, origin="lower", extent=[0, w, 0, h], cmap="Greens",
              vmin=0, vmax=1.2, alpha=0.55, aspect="auto", zorder=0)
    return world


def _force_positions(f, scn):
    """Approximate laydown centroids for a force (column/line along the formation direction)."""
    n = scn.params.get(f.count_param, f.count) if f.count_param else f.count
    n = int(n)
    cx, cy = f.spawn
    gap = f.spacing if f.spacing is not None else scn.params.get("formation_spread", 30.0)
    fdir = {"column": (-1.0, 0.0), "line": (0.0, 1.0), "wedge": (-1.0, 1.0)}.get(f.formation, (-1.0, 0.0))
    xs = cx + fdir[0] * gap * np.arange(n)
    ys = cy + fdir[1] * gap * np.arange(n)
    return xs, ys


def fig_scenarios() -> None:
    specs = [
        ("(a) UC-3  route vs defilade", "scenarios/uc3_route_defilade.json", "uc3"),
        ("(b) Centerpiece  span of control $\\times$ comms/EW", "scenarios/sc_span_control.json", "cp"),
        ("(c) UC-5  sensor swarm under EW", "scenarios/uc5_sensor_swarm.json", "uc5"),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(6.6, 6.4))
    for ax, (title, path, kind) in zip(axes, specs):
        scn = load_scenario(path)
        w, h = scn.size
        _draw_world(ax, scn)
        gx, gy = scn.objective.goal

        # objective
        ax.scatter([gx], [gy], marker="*", s=180, color=AMBER, edgecolor="k", lw=0.5, zorder=6)
        ax.text(gx, gy + 190, "objective", ha="center", fontsize=6.8, color="#7a5a12")

        # forces
        for f in scn.forces:
            xs, ys = _force_positions(f, scn)
            pt = scn.platform_types[f.ptype]
            if f.side == 1:  # red
                ax.scatter(xs, ys, marker="s", s=34, color=RED, edgecolor="k", lw=0.4, zorder=5)
                # weapon-range rings show the kill zone
                for x, y in zip(xs, ys):
                    ax.add_patch(Circle((x, y), pt.weapon_range, fill=False, ec=RED,
                                        lw=0.5, alpha=0.28, ls=(0, (3, 3)), zorder=1))
            elif pt.domain == 1:  # UAS (air)
                st = overwatch_stations(len(xs), scn.params.get("overwatch_x", gx * 0.6),
                                        scn.params.get("overwatch_y", h * 0.5),
                                        pt.sensor_range, scn.size,
                                        aspect=scn.params.get("overwatch_aspect", 1.0))
                ax.scatter(st[:, 0], st[:, 1], marker="^", s=42, color=AIR, edgecolor="k", lw=0.4, zorder=6)
                for x, y in st:
                    ax.add_patch(Circle((x, y), pt.sensor_range, fill=True, fc=AIR, ec=AIR,
                                        lw=0.6, alpha=0.10, zorder=1))
            else:  # blue ground
                ax.scatter(xs, ys, marker="o", s=34, color=BLUE, edgecolor="k", lw=0.4, zorder=5)
                if kind == "uc5":  # near-blind: tiny sensor ring vs long weapon ring
                    ax.add_patch(Circle((xs[0], ys[0]), pt.sensor_range, fill=False, ec=BLUE,
                                        lw=0.8, alpha=0.6, zorder=2))
                    ax.add_patch(Circle((xs[0], ys[0]), pt.weapon_range, fill=False, ec=BLUE,
                                        lw=0.7, alpha=0.22, ls=(0, (3, 3)), zorder=2))
                    ax.text(xs[0], ys[0] - 560, "near-blind UGVs\nsensor 350 m $\\ll$ weapon 1400 m",
                            fontsize=6.0, color=BLUE, ha="center", va="top")

        # routes
        if kind == "uc3":
            xr = np.linspace(scn.forces[0].spawn[0], gx, 120)
            for bias, col, lab in [(0.0, RED, "fast corridor (exposed)"),
                                   (0.5, AMBER, "balanced"),
                                   (1.0, GREEN, "defilade (covered)")]:
                yr = _lane_y(xr, bias, gx, gy, h)
                ax.plot(xr, yr, color=col, lw=1.8, zorder=3, label=lab)
            ax.legend(loc="lower left", fontsize=6.2, frameon=True, framealpha=0.85,
                      handlelength=1.6, borderpad=0.4)
            ax.text(300, h * 0.78, "cover band", fontsize=6.2, color="#1a6b3a", va="center")
            ax.text(2900, 1150, "AT-team defenders", fontsize=6.2, color=RED, ha="center")
        elif kind == "cp":
            xr = np.linspace(scn.forces[0].spawn[0], gx, 120)
            ax.plot(xr, _lane_y(xr, scn.params.get("route_bias", 0.65), gx, gy, h),
                    color=BLUE, lw=1.6, zorder=3)
            ax.text(w * 0.5, 2580,
                    "1 operator supervises $n$ ground assets over the comms/EW link",
                    fontsize=6.6, color=BLUE, ha="center", va="top",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
        else:  # uc5
            xr = np.linspace(scn.forces[0].spawn[0], gx, 120)
            ax.plot(xr, _lane_y(xr, scn.params.get("route_bias", 0.5), gx, gy, h),
                    color=BLUE, lw=1.4, zorder=3, alpha=0.7)
            ax.annotate("UAS overwatch cues\nnear-blind shooters", xy=(scn.params["overwatch_x"], gy + 300),
                        fontsize=6.4, color=AIR, ha="center")

        ax.set_title(title, fontsize=9, loc="left", color=INK)
        ax.set_xlim(0, w); ax.set_ylim(300, 2700)
        ax.set_xticks([0, 2000, 4000, 6000]); ax.set_yticks([1000, 2000])
        ax.tick_params(labelsize=6.5)
        ax.set_xlabel("x (m)", fontsize=7); ax.set_ylabel("y (m)", fontsize=7)

    fig.tight_layout(h_pad=1.1)
    fig.savefig(FIG / "scenarios.pdf")
    fig.savefig(FIG / "scenarios.png", dpi=170)
    plt.close(fig)
    print("wrote scenarios.pdf")


# --------------------------------------------------------------------------- config tables
def tab_ladder() -> None:
    lines = [r"\begin{tabular}{clcl}", r"\toprule",
             r"level & one-way latency (steps) & drop prob. & regime \\", r"\midrule"]
    for lvl, (lat, drop, label) in sorted(_LADDER.items()):
        lines.append(f"C{lvl} & {lat} & {drop:.2f} & {label} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_ladder.tex").write_text("\n".join(lines) + "\n")
    print("wrote tab_ladder.tex")


def tab_platforms() -> None:
    rows = []
    seen = set()
    specs = [("UC-3", "scenarios/uc3_route_defilade.json"),
             ("centerpiece", "scenarios/sc_span_control.json"),
             ("UC-5", "scenarios/uc5_sensor_swarm.json")]
    for tag, path in specs:
        scn = load_scenario(path)
        for name, pt in scn.platform_types.items():
            key = (tag, name)
            if key in seen:
                continue
            seen.add(key)
            dom = "air" if pt.domain == 1 else "ground"
            rows.append((tag, name, dom, pt.max_speed, pt.sensor_range, pt.weapon_range, pt.pk_base))
    lines = [r"\begin{tabular}{lllrrrr}", r"\toprule",
             r"scenario & platform & domain & $v_{\max}$ (m/s) & sensor (m) & weapon (m) & $p_k$ \\",
             r"\midrule"]
    last = None
    for tag, name, dom, v, sr, wr, pk in rows:
        show = tag if tag != last else ""
        last = tag
        safe = name.replace("_", r"\_")
        lines.append(f"{show} & {safe} & {dom} & {v:.0f} & {sr:.0f} & {wr:.0f} & {pk:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_platforms.tex").write_text("\n".join(lines) + "\n")
    print("wrote tab_platforms.tex")


def main() -> None:
    fig_architecture()
    fig_command_model()
    fig_scenarios()
    tab_ladder()
    tab_platforms()
    print("diagrams ->", FIG)


if __name__ == "__main__":
    main()
