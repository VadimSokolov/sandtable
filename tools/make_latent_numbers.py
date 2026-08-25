"""Numbers for the latent-shift account: CR-74's fit and CR-75's registered test of it.

Separate from tools/make_ceiling_numbers.py, which generates the CR-69 censoring
measurements under the Ce prefix. These carry the Cl prefix and go to their own file, so
neither generator can overwrite the other's macros. That is not hypothetical: this file
began life by clobbering that one.

The account is that a capability adds a CONSTANT to a latent margin, and that everything a test
program reads as the capability mattering less at scale is the success metric compressing that
constant as the baseline approaches its bound. The model has one parameter per capability and no
freedom in its shape:

    effect(b) = Phi(Phi^-1(b) + delta) - b

Two things are generated here and they are kept apart on purpose. CR-74 is a FIT, made after the
batteries ran, and its honest support is a leave-one-section-out check rather than a falsifier.
CR-75 is the registered test, and it refits nothing: delta is taken from CR-74 and the prediction at
a new cell is conditional on the baseline that cell's own control arm reads. Macros from the second
are only emitted when the second battery's log is present, so a manuscript cannot quote a verdict
that has not been produced.
"""
from __future__ import annotations

import math
import pathlib
import re
import statistics as st
import sys
from statistics import NormalDist

N = NormalDist()
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

LOSS_LOG = ROOT / "report" / "data" / "queue" / "st-loss-9460876.out"
OUT = ROOT / "report" / "gen" / "latent_numbers.tex"
REF = "blindUnbound"
ARMS = {"boundOne": "Bound", "admits": "Admit"}
WORD = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
        8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 14: "fourteen",
        16: "sixteen", 20: "twenty", 24: "twenty-four", 32: "thirty-two"}


def _read(log: pathlib.Path, metric_wanted: str = "success") -> dict:
    """{(section, arm, dose): [block means]} for one metric."""
    sec = met = None
    rows: dict[tuple[str, str, str], list[float]] = {}
    if not log.exists():
        return rows
    for ln in log.read_text().splitlines():
        ln = ln.strip()
        if ln.startswith("### "):
            m = re.match(r"### ([WX]\d)\b.*\((\w+)\)$", ln)
            if m:
                sec, met = m.group(1), m.group(2)
            continue
        if ln.startswith("AR_ROW") and met == metric_wanted:
            arm = re.search(r"arm=(\S+)", ln).group(1)
            d = re.search(r"(?:n_red|n_blue|span)=(\S+)", ln)
            vals = [float(x) for x in re.search(r"vals=(\S+)", ln).group(1).split(",")]
            rows[(sec, arm, d.group(1) if d else "?")] = vals
    return rows


def _cells(rows: dict, arm: str) -> list[tuple[str, str, float, float]]:
    """(section, dose, baseline mean, treated mean) for every cell the reference also covers."""
    out = []
    for (s, a, d), vals in sorted(rows.items()):
        if a != arm:
            continue
        base = rows.get((s, REF, d))
        if base:
            out.append((s, d, st.mean(base), st.mean(vals)))
    return out


def _pred(b: float, delta: float) -> float:
    b = min(max(b, 1e-6), 1 - 1e-6)
    return N.cdf(N.inv_cdf(b) + delta) - b


def _fit(cells) -> float:
    best, x = (1e9, 0.0), 0.02
    while x < 2.5:
        ss = sum((_pred(b, x) - (tr - b)) ** 2 for _, _, b, tr in cells)
        if ss < best[0]:
            best = (ss, x)
        x += 0.002
    return best[1]


def _r2(cells, resid) -> float:
    obs = [tr - b for _, _, b, tr in cells]
    sse = sum(r * r for r in resid)
    sst = sum((o - st.mean(obs)) ** 2 for o in obs)
    return 1 - sse / sst if sst > 0 else float("nan")


def main() -> None:
    out: list[tuple[str, str]] = []
    rows = _read(LOSS_LOG)
    if not rows:
        raise SystemExit(f"{LOSS_LOG} not found or carries no success rows")

    # W4, the dose-response that was registered as the guard against a single hand-picked operating
    # point and then left unscored until now.
    for arm, tag in ARMS.items():
        for dose in ("4", "6", "8", "10", "12"):
            b = rows.get(("W4", REF, dose))
            tr = rows.get(("W4", arm, dose))
            if b and tr:
                out.append((f"Cl{tag}Dose{WORD[int(dose)].replace('-', '')}",
                            f"{st.mean(tr) - st.mean(b):+.4f}"))
    base4 = {d: st.mean(rows[("W4", REF, d)]) for d in ("4", "6", "8", "10", "12")
             if ("W4", REF, d) in rows}
    if base4:
        out += [("ClBaseCeil", f"{base4['4']:.4f}"), ("ClBaseFloor", f"{base4['12']:.4f}")]

    # The fit, and then the check that makes a post-hoc fit worth reporting at all.
    for arm, tag in ARMS.items():
        cells = _cells(rows, arm)
        if not cells:
            continue
        delta = _fit(cells)
        resid = [(tr - b) - _pred(b, delta) for _, _, b, tr in cells]
        out += [(f"Cl{tag}Delta", f"{delta:.3f}"),
                (f"Cl{tag}Cells", str(len(cells))),
                (f"Cl{tag}RSq", f"{_r2(cells, resid):.3f}"),
                (f"Cl{tag}Rms", f"{math.sqrt(sum(r * r for r in resid) / len(resid)):.4f}"),
                (f"Cl{tag}MaxEff", f"{max(tr - b for _, _, b, tr in cells):+.4f}")]

        folds, deltas = [], []
        for s in sorted({c[0] for c in cells}):
            tr_, te = [c for c in cells if c[0] != s], [c for c in cells if c[0] == s]
            d = _fit(tr_)
            deltas.append(d)
            folds += [(t - b) - _pred(b, d) for _, _, b, t in te]
        out += [(f"Cl{tag}OosRSq", f"{_r2(cells, folds):.3f}"),
                (f"Cl{tag}OosRms", f"{math.sqrt(sum(r * r for r in folds) / len(folds)):.4f}"),
                (f"Cl{tag}DeltaLo", f"{min(deltas):.3f}"),
                (f"Cl{tag}DeltaHi", f"{max(deltas):.3f}"),
                (f"Cl{tag}Folds", WORD[len(deltas)])]
        # Where the curve says the maximum must sit, against where the sweep put it. Taken from W4
        # ALONE, and not from the pooled cells: W4 is the one section that sweeps the baseline
        # monotonically across the whole range, so a maximum is well defined in it. Pooling sections
        # whose baselines are sampled at whatever points their own sweeps happened to visit would
        # report the largest observed effect rather than the location of a maximum.
        w4 = [c for c in cells if c[0] == "W4"]
        if w4:
            peak = max(w4, key=lambda c: c[3] - c[2])
            out += [(f"Cl{tag}PeakBase", f"{peak[2]:.3f}"),
                    (f"Cl{tag}PeakEff", f"{peak[3] - peak[2]:+.4f}")]

    out += [("ClSections", WORD[len({c[0] for c in _cells(rows, 'boundOne')})]),
            ("ClPeakTheory", "0.500")]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("% generated by tools/make_ceiling_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {OUT} with {len(out)} macros")


if __name__ == "__main__":
    main()
