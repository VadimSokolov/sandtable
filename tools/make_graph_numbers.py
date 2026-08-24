"""CR-68: does the topology carry anything the geometry does not?

CR-60 scored four GEOMETRIC readings of one set of positions and recommended the one that never
looks at the commanded formation. This tool scores two GRAPH readings of the same positions against
mission success, and answers the objection that a graph reading costs an assumed peer-link range
where a geometric one costs nothing.

The claim here is an ORDERING claim, so it is scored by rank correlation over the design grid and
NOT by the paired gate. That is stated in the macros' own names and has to stay stated: the project's
gate answers "did this arm move the metric", and no amount of it answers "does this reading rank the
design space the way the mission does".
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
from scipy.stats import spearmanr

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ar_survey import survey                                    # noqa: E402

ROOT = HERE.parent
LOG = str(ROOT / "report" / "data" / "queue" / "st-graph-9459832.out")
OUT = ROOT / "report" / "gen" / "graph_numbers.tex"

X1 = "X1 the geometric and graph readings on one grid"
X2 = "X2 the band of assumed link range in which a graph reading discriminates"
ARMS = ("chainTight", "chainWide", "starTight", "starVeryWide", "starWide")
RANGES = (150, 250, 400, 600, 1000)

# Sign each reading is predicted to carry against mission success, declared here rather than read
# off the result. Readings referenced to the COMMANDED station are marked, because CR-60 already
# refuted them for a reason this grid would hide: the treatment sets the commanded geometry, so a
# station-referenced reading looks good here by construction.
READINGS = {
    "fleet_spread_mean":       (-1, "geometric", False),
    "fleet_cross_mean":        (-1, "geometric", False),
    "station_err_mean":        (-1, "geometric", True),
    "station_cross_mean":      (-1, "geometric", True),
    "fleet_fiedler_mean":      (+1, "graph", False),
    "fleet_kappa_mean":        (+1, "graph", False),
    "fleet_faults_mean":       (+1, "graph", False),
    "fleet_disconnected_frac": (-1, "graph", False),
}
NAME = {"fleet_spread_mean": "Spread", "fleet_cross_mean": "Cross", "station_err_mean": "StatErr",
        "station_cross_mean": "StatCross", "fleet_fiedler_mean": "Fiedler",
        "fleet_kappa_mean": "Kappa", "fleet_faults_mean": "Faults",
        "fleet_disconnected_frac": "Disc"}
IDX = ("One", "Two", "Three", "Four", "Five")


def _flat(sec, metric):
    lv = survey(LOG, sec, metric, quiet=True)
    if not lv or any(a not in lv for a in ARMS):
        return None
    return np.array([v for a in ARMS for v in lv[a]])


def main() -> None:
    out: list[tuple[str, str]] = []
    succ = _flat(X1, "success")
    if succ is None:
        raise SystemExit(f"{LOG}: no X1 grid")

    # Cells where mission success is against a bound cannot order anything, per the Round 36 axis
    # rule. Diagnosed from the outcome axis itself here because there is no single reference arm on
    # a design grid, and reported so the reader can see how many cells the rule removed.
    ok = (succ > 0.02) & (succ < 0.98)
    out += [("GrCells", str(succ.size)), ("GrCellsUsed", str(int(ok.sum())))]

    ranked = []
    for m, (sgn, kind, ref_by_treat) in READINGS.items():
        x = _flat(X1, m)
        if x is None:
            continue
        rho = spearmanr(x[ok], succ[ok]).statistic
        tag = NAME[m]
        out += [(f"GrRho{tag}", f"{rho:+.3f}"),
                (f"GrSign{tag}", "as predicted" if np.sign(rho) == sgn else "BACKWARD")]
        if not ref_by_treat:
            ranked.append((abs(rho), tag, kind))
    ranked.sort(reverse=True)
    if ranked:
        out += [("GrBest", ranked[0][1]), ("GrBestRho", f"{ranked[0][0]:.3f}"),
                ("GrBestKind", ranked[0][2]),
                ("GrWorst", ranked[-1][1]), ("GrWorstRho", f"{ranked[-1][0]:.3f}")]
        best_geo = next((r for r in ranked if r[2] == "geometric"), None)
        best_gph = next((r for r in ranked if r[2] == "graph"), None)
        if best_geo and best_gph:
            out += [("GrGeoBest", best_geo[1]), ("GrGeoBestRho", f"{best_geo[0]:.3f}"),
                    ("GrGraphBest", best_gph[1]), ("GrGraphBestRho", f"{best_gph[0]:.3f}"),
                    ("GrGraphOverGeo", f"{best_gph[0] / best_geo[0]:.1f}")]

    # `faults` is NOT a monotone transform of mean connectivity, which is the objection a reader
    # will raise first, since (kappa-1)//2 is monotone in kappa. The transform is applied PER
    # SAMPLED STEP and then averaged, so the mean of the floor is not the floor of the mean, and
    # the two rank the grid differently. Measured rather than argued.
    k, f = _flat(X1, "fleet_kappa_mean"), _flat(X1, "fleet_faults_mean")
    if k is not None and f is not None:
        out.append(("GrFaultsKappaRho", f"{spearmanr(k, f).statistic:.3f}"))

    # X2: the price of the graph reading is one assumed number, so the question is whether the
    # ordering depends on it. The control that makes the section readable is that mission success
    # is IDENTICAL across the sweep: the assumed range is an observer's parameter and touches
    # nothing in the simulation.
    s2 = survey(LOG, X2, "success", quiet=True)
    if s2:
        spans = [max(s2[a]) - min(s2[a]) for a in ARMS]
        out.append(("GrRangeInert", f"{max(spans):.4f}"))
        base = np.array([s2[a][0] for a in ARMS])
        rhos = []
        for j in range(len(RANGES)):
            d = survey(LOG, X2, "fleet_faults_mean", quiet=True)
            if not d:
                break
            x = np.array([d[a][j] for a in ARMS])
            r = spearmanr(x, base).statistic
            rhos.append(r)
            out.append((f"GrRangeRho{IDX[j]}", f"{r:+.3f}"))
        if rhos:
            out += [("GrRangeLo", str(RANGES[0])), ("GrRangeHi", str(RANGES[-1])),
                    ("GrRangeWorst", f"{min(rhos):+.3f}"), ("GrRangeBest", f"{max(rhos):+.3f}")]

    OUT.write_text("% generated by tools/make_graph_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    for k, v in out:
        print(f"  {k:22s} {v}")
    print(f"\n{len(out)} macros -> {OUT}")


if __name__ == "__main__":
    main()
