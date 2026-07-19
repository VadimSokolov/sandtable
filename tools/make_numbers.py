"""Generate the paper's numbers (LaTeX macros) and result tables from the study CSVs.

Single source of truth for every value the manuscript cites. Reads report/data/*.csv (tidy
per-design KPI means from the Hopper studies) and writes:
  report/gen/numbers.tex      -- \\newcommand macros, \\input by main.tex
  report/gen/tab_centerpiece.tex, tab_uc3.tex, tab_uc5.tex, tab_lanchester.tex
  report/results/numbers.txt  -- human-readable audit trail (every macro + provenance)

    PYTHONPATH=src python tools/make_numbers.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("report/data")
GEN = Path("report/gen"); GEN.mkdir(parents=True, exist_ok=True)
RES = Path("report/results"); RES.mkdir(parents=True, exist_ok=True)
NREP = 300

_macros: dict[str, str] = {}
_audit: list[str] = []


def put(name: str, value, note: str) -> None:
    """Register a macro (LaTeX-safe name -> string value) and an audit line."""
    _macros[name] = str(value)
    _audit.append(f"\\{name} = {value}    # {note}")


def _fmt(x, nd=0):
    return f"{x:.{nd}f}"


# --------------------------------------------------------------------------- centerpiece
def centerpiece() -> None:
    d = pd.read_csv(DATA / "centerpiece_direct.csv")
    s = pd.read_csv(DATA / "centerpiece_supervisory.csv")
    m = d.merge(s, on=["comms_level", "n_blue"], suffixes=("_d", "_s"))
    m["delta"] = (m["success_rate_s"] - m["success_rate_d"]) * 100

    def dsucc(mode_df, span, c):
        v = mode_df[(mode_df.n_blue == span) & (mode_df.comms_level == c)]["success_rate"].iloc[0]
        return round(v * 100)

    put("cpDirClearLoSpan", dsucc(d, 2, 0), "direct success%% span1:2 C0")
    put("cpDirSevereLoSpan", dsucc(d, 2, 5), "direct success%% span1:2 C5")
    put("cpDirClearHiSpan", dsucc(d, 8, 0), "direct success%% span1:8 C0")
    put("cpSupClearHiSpan", dsucc(s, 8, 0), "supervisory success%% span1:8 C0")

    # supervisory comms-invariance: spread across comms for span 1:2
    row = s[s.n_blue == 2].sort_values("comms_level")["success_rate"].values * 100
    put("cpSupLoSpanMin", _fmt(row.min()), "supervisory span1:2 min success%% over comms")
    put("cpSupLoSpanMax", _fmt(row.max()), "supervisory span1:2 max success%% over comms")
    put("cpSupLoSpanSpread", _fmt(row.max() - row.min(), 1), "supervisory span1:2 comms spread (pp)")

    # crossover C* per span (first comms where delta >= 0)
    stars = {}
    for n in sorted(m.n_blue.unique()):
        sub = m[m.n_blue == n].sort_values("comms_level")
        star = sub[sub.delta >= 0]["comms_level"].min()
        stars[n] = None if pd.isna(star) else int(star)
    put("cpStarLoSpan", stars[2], "crossover C* at span 1:2")
    put("cpStarHiSpan", stars[8], "crossover C* at span 1:8")

    # max supervisory advantage (largest positive delta)
    put("cpDeltaMax", _fmt(m.delta.max()), "max supervisory-minus-direct advantage (pp)")
    put("cpDeltaHiSpanClear",
        _fmt(m[(m.n_blue == 8) & (m.comms_level == 0)]["delta"].iloc[0]),
        "supervisory advantage at span 1:8, C0 (pp)")

    # table: delta grid
    piv = m.pivot(index="n_blue", columns="comms_level", values="delta").sort_index()
    lines = [r"\begin{tabular}{r" + "r" * len(piv.columns) + "}", r"\toprule",
             "span & " + " & ".join(f"C{c}" for c in piv.columns) + r" \\", r"\midrule"]
    for n, r in piv.iterrows():
        cells = " & ".join(f"{v:+.0f}" for v in r.values)
        lines.append(f"1:{n} & {cells}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_centerpiece.tex").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- UC-3
def uc3() -> None:
    f = pd.read_csv(DATA / "uc3_frontier.csv").sort_values("route_bias")
    g = f.groupby("route_bias", as_index=False).mean(numeric_only=True)
    lo, hi = g.iloc[0], g.iloc[-1]
    put("ucThreeSuccFast", round(lo.success_rate * 100), "UC3 success%% route_bias 0 (fast corridor)")
    put("ucThreeSuccCover", round(hi.success_rate * 100), "UC3 success%% route_bias 1 (defilade)")
    put("ucThreeLossFast", _fmt(lo.blue_losses, 1), "UC3 blue losses route_bias 0 (of 8)")
    put("ucThreeLossCover", _fmt(hi.blue_losses, 1), "UC3 blue losses route_bias 1 (of 8)")
    put("ucThreeTimeFast", round(lo.t_obj_success), "UC3 time-to-obj (s) route_bias 0")
    put("ucThreeTimeCover", round(hi.t_obj_success), "UC3 time-to-obj (s) route_bias 1")
    put("ucThreeTempoRatio", _fmt(hi.t_obj_success / lo.t_obj_success, 1), "UC3 tempo ratio cover/fast")

    # table: a subset of route_bias rows
    keep = [0.0, 0.25, 0.5, 0.75, 1.0]
    sub = g[g.route_bias.isin(keep)]
    lines = [r"\begin{tabular}{rrrrr}", r"\toprule",
             r"route bias & success (\%) & blue losses & red losses & $t_{\text{obj}}$ (s) \\", r"\midrule"]
    for _, r in sub.iterrows():
        lines.append(f"{r.route_bias:.2f} & {r.success_rate*100:.0f} & {r.blue_losses:.1f} & "
                     f"{r.red_losses:.1f} & {r.t_obj_success:.0f}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_uc3.tex").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- UC-5
def uc5() -> None:
    path = DATA / "uc5_swarm_jam.csv"
    if not path.exists():
        _audit.append("# UC-5 CSV absent - macros skipped (regen after Hopper)")
        return
    u = pd.read_csv(path)

    def cell(n, c, col):
        r = u[(u.n_uas == n) & (u.comms_level == c)]
        return None if r.empty else r[col].iloc[0]

    nmax = int(u.n_uas.max())
    put("ucFiveSwarmMax", nmax, "UC5 largest swarm size")
    put("ucFiveSuccBlind", round(cell(0, 0, "success_rate") * 100), "UC5 success%% no recon (n=0)")
    put("ucFiveSuccBestClear", round(cell(nmax, 0, "success_rate") * 100), "UC5 success%% max swarm, C0")
    put("ucFiveSuccBestSevere", round(cell(nmax, 5, "success_rate") * 100), "UC5 success%% max swarm, C5")
    put("ucFiveCovBlind", _fmt(cell(0, 0, "detection_coverage"), 2), "UC5 coverage no recon")
    put("ucFiveCovBestClear", _fmt(cell(nmax, 0, "detection_coverage"), 2), "UC5 coverage max swarm C0")
    put("ucFiveCovBestSevere", _fmt(cell(nmax, 5, "detection_coverage"), 2), "UC5 coverage max swarm C5")
    # a mid swarm size (3) to show the operating point + jam collapse
    put("ucFiveSuccMidClear", round(cell(3, 0, "success_rate") * 100), "UC5 success%% n=3 C0")
    put("ucFiveSuccMidSevere", round(cell(3, 5, "success_rate") * 100), "UC5 success%% n=3 C5")

    # table: coverage & success at C0/C3/C5 across swarm size
    show_c = [0, 3, 5]
    ns = sorted(u.n_uas.unique())
    lines = [r"\begin{tabular}{r" + "r" * (2 * len(show_c)) + "}", r"\toprule",
             " & " + " & ".join([r"\multicolumn{2}{c}{" + f"C{c}" + "}" for c in show_c]) + r" \\"]
    cmid = " ".join([f"\\cmidrule(lr){{{2*i+2}-{2*i+3}}}" for i in range(len(show_c))])
    lines.append(cmid)
    lines.append("swarm & " + " & ".join(["cov & succ"] * len(show_c)) + r" \\")
    lines.append(r"\midrule")
    for n in ns:
        cells = []
        for c in show_c:
            cov = cell(n, c, "detection_coverage"); su = cell(n, c, "success_rate")
            cells.append(f"{cov:.2f} & {su*100:.0f}")
        lines.append(f"{n} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_uc5.tex").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- Lanchester cross-check
def lanchester() -> None:
    """Analytic aimed-fire (square-law) attrition vs the sim, on a controlled duel.

    Reads report/data/lanchester.csv if present (produced by tools/lanchester_check.py);
    otherwise skips. Kept here so the table lives with the other generated tables.
    """
    path = DATA / "lanchester.csv"
    if not path.exists():
        _audit.append("# Lanchester CSV absent - table skipped (run tools/lanchester_check.py)")
        return
    L = pd.read_csv(path)
    lines = [r"\begin{tabular}{rrrrr}", r"\toprule",
             r"$B_0$ & $R_0$ & sim $B$ surv. & Lanchester $B$ & rel. err. \\", r"\midrule"]
    for _, r in L.iterrows():
        lines.append(f"{int(r.B0)} & {int(r.R0)} & {r.sim_surv:.2f} & {r.lanch_surv:.2f} & "
                     f"{r.rel_err*100:.1f}\\%" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_lanchester.tex").write_text("\n".join(lines) + "\n")
    put("lanchMaxErr", _fmt(L.rel_err.abs().max() * 100, 1), "max Lanchester relative error (%)")


def main() -> None:
    centerpiece()
    uc3()
    uc5()
    lanchester()
    put("nRep", NREP, "Monte-Carlo replications per design")
    tex = "% AUTO-GENERATED by tools/make_numbers.py -- do not edit.\n"
    tex += "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in _macros.items()) + "\n"
    (GEN / "numbers.tex").write_text(tex)
    (RES / "numbers.txt").write_text(
        "SandTable paper -- generated numbers (source: tools/make_numbers.py over report/data/*.csv)\n"
        + "=" * 78 + "\n" + "\n".join(_audit) + "\n")
    print(f"wrote {GEN/'numbers.tex'} ({len(_macros)} macros)")
    print(f"wrote tables -> {GEN}")
    print(f"wrote audit  -> {RES/'numbers.txt'}")


if __name__ == "__main__":
    main()
