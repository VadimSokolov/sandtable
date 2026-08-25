#!/usr/bin/env python3
"""Score CR-77 against its registered falsifiers, mechanically.

CR-77 asserts that a design set is a fixed vector of latent offsets and an operating point is a
single number sliding all of them along one probit curve. If that holds, the differences between
designs are CONSTANT ON THE PROBIT SCALE across operating points, and a study's replication cost at
an operating point nobody has run is fixed by a fit made at one somebody has.

The registration is in doc/autoresearch-conjectures.md under CR-77 and it fixes everything this
script does: the fitting span, the anchor rule, which cells are excluded as entailed, the two
thresholds, and the branch to take if the measured costs turn out to be noise. This file was
written before any of the numbers were read, for the same reason score_bench.py was.

No simulation. Every quantity comes from the truth tables already on disk; per-mission standard
deviations are recovered exactly as se * sqrt(reps) from the block the answer key was built on,
which is both free and a better estimator than the hundred and twenty fresh draws difficulty() takes.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sandtable.search.problems import get                      # noqa: E402
from sandtable.search.oracle import _path, truth_reps          # noqa: E402

SPANS = (8, 10, 12, 16)
FIT_SPAN = 8
KNOBS = ("qcap", "disc")
PRIMARY = "succ"
EXPLORATORY = "loss"
RMS_MAX = 0.045          # registered
RSQ_MIN = 0.50           # registered
RHO_MIN = 0.50           # registered


# ---------------------------------------------------------------- probit

def _ppf(p: float) -> float:
    """Inverse normal CDF. Acklam's rational approximation, |error| < 1.15e-9."""
    if not 0.0 < p < 1.0:
        return math.copysign(float("inf"), p - 0.5)
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------- data

def cell(knob: str, span: int, metric: str) -> dict:
    """{design-key: (value, se)} plus the problem, read from the answer key on disk."""
    p = get(f"{knob}_s{span}_{metric}")
    raw = json.loads(_path(p).read_text())
    meta = raw.pop("_meta")
    se = meta["_se"]
    return {"p": p, "val": raw, "se": se, "reps": meta["_reps"],
            "designs": sorted(raw)}


def _rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):                       # average ties
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def spearman(xs, ys) -> float:
    rx, ry = _rank(xs), _rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx > 0 and dy > 0 else float("nan")


# ---------------------------------------------------------------- part A

def fit_and_predict(knob: str, metric: str, anchor_rule: str = "mid") -> dict:
    cells = {s: cell(knob, s, metric) for s in SPANS}
    designs = cells[FIT_SPAN]["designs"]
    fitv = cells[FIT_SPAN]["val"]

    # The anchor is chosen from the FITTING span only, never from a held-out one. "mid" takes the
    # design closest to one half because probit is best conditioned there; "first" takes the first
    # design in enumeration order and exists as the robustness check the registration promised.
    if anchor_rule == "mid":
        anchor = min(designs, key=lambda d: abs(fitv[d] - 0.5))
    else:
        anchor = designs[0]

    # Six free offsets. The anchor's is zero by construction, which is why its cells never score.
    delta = {d: _ppf(fitv[d]) - _ppf(fitv[anchor]) for d in designs}

    rows, ent = [], []
    for s in SPANS:
        c = cells[s]
        base = c["val"][anchor]                       # one reading per span, and nothing else
        for d in designs:
            pred = _cdf(_ppf(base) + delta[d])
            held = s != FIT_SPAN
            entailed = (d == anchor) or (s == FIT_SPAN)
            row = {"span": s, "design": d, "actual": c["val"][d], "pred": pred,
                   "se": c["se"][d], "held_out": held, "entailed": entailed}
            (ent if entailed else rows).append(row)

    act = [r["actual"] for r in rows]
    err = [r["pred"] - r["actual"] for r in rows]
    n = len(rows)
    rms = math.sqrt(sum(e * e for e in err) / n)
    mean = sum(act) / n
    sst = sum((a - mean) ** 2 for a in act)
    rsq = 1.0 - sum(e * e for e in err) / sst if sst > 0 else float("nan")
    return {"knob": knob, "metric": metric, "anchor": anchor, "delta": delta,
            "rows": rows, "entailed": ent, "n": n, "rms": rms, "rsq": rsq,
            "cells": cells, "designs": designs}


# ---------------------------------------------------------------- part B

def cost_of(values: dict, ses: dict, reps: int, direction: str) -> dict:
    """Mirror oracle.difficulty(): reps per design for the top two to sit two standard errors
    apart, with the per-mission sd pooled over the top two. sd comes from the answer key's own
    block as se*sqrt(reps), which is exact rather than resampled."""
    ranked = sorted(values, key=lambda k: values[k], reverse=(direction == "max"))
    gap = abs(values[ranked[0]] - values[ranked[1]])
    sds = [ses[k] * math.sqrt(reps) for k in ranked[:2]]
    sd = math.sqrt(sum(x * x for x in sds) / 2.0)
    se_gap = math.hypot(ses[ranked[0]], ses[ranked[1]])
    return {"gap": gap, "sd": sd, "se_gap": se_gap,
            "reps": float("inf") if gap <= 0 else (2.0 * sd / gap) ** 2,
            "top": ranked[0], "second": ranked[1]}


def cost_predicted(fit: dict, span: int) -> dict:
    """Same formula, but every value and every sd comes from the model. For a counted success the
    threshold story fixes the per-mission sd at sqrt(p(1-p)) with nothing left to fit."""
    p = fit["cells"][span]["p"]
    pred = {r["design"]: r["pred"] for r in fit["rows"] + fit["entailed"] if r["span"] == span}
    ranked = sorted(pred, key=lambda k: pred[k], reverse=(p.direction == "max"))
    gap = abs(pred[ranked[0]] - pred[ranked[1]])
    sds = [math.sqrt(max(pred[k] * (1 - pred[k]), 0.0)) for k in ranked[:2]]
    sd = math.sqrt(sum(x * x for x in sds) / 2.0)
    return {"gap": gap, "sd": sd,
            "reps": float("inf") if gap <= 0 else (2.0 * sd / gap) ** 2}


def score_cost(fit: dict) -> dict:
    meas, pred, noisy = [], [], 0
    detail = []
    for s in SPANS:
        c = fit["cells"][s]
        m = cost_of(c["val"], c["se"], c["reps"], c["p"].direction)
        q = cost_predicted(fit, s)
        if m["gap"] < m["se_gap"]:
            noisy += 1
        meas.append(m["reps"]); pred.append(q["reps"])
        detail.append({"span": s, "meas": m, "pred": q})
    finite = [(a, b) for a, b in zip(meas, pred) if math.isfinite(a) and math.isfinite(b)]
    rho = spearman([a for a, _ in finite], [b for _, b in finite]) if len(finite) > 2 else float("nan")
    return {"rho": rho, "noisy": noisy, "n": len(SPANS), "detail": detail}


# ---------------------------------------------------------------- report

def main() -> int:
    print("CR-77 scored against its registered falsifiers")
    print(f"  fit span n_blue={FIT_SPAN}; held out {[s for s in SPANS if s != FIT_SPAN]}")
    print(f"  A fails if RMS > {RMS_MAX} or R2 < {RSQ_MIN} at EITHER knob")
    print(f"  B fails if Spearman < {RHO_MIN} at BOTH knobs\n")

    verdicts = {}
    for metric, tag in ((PRIMARY, "PRIMARY"), (EXPLORATORY, "exploratory")):
        print(f"=== {metric}  ({tag}) ===")
        fits = {}
        for knob in KNOBS:
            f = fit_and_predict(knob, metric)
            g = fit_and_predict(knob, metric, anchor_rule="first")
            fits[knob] = f
            ok = f["rms"] <= RMS_MAX and f["rsq"] >= RSQ_MIN
            print(f"  {knob:5s} anchor={f['anchor'][:38]:38s} n_scored={f['n']:3d}")
            print(f"        out-of-sample RMS {f['rms']:.4f}   R2 {f['rsq']:+.3f}   "
                  f"{'PASS' if ok else 'FAIL'}")
            print(f"        robustness (first-design anchor): RMS {g['rms']:.4f}  R2 {g['rsq']:+.3f}")
            worst = max(f["rows"], key=lambda r: abs(r["pred"] - r["actual"]))
            print(f"        worst cell  span {worst['span']:2d}  actual {worst['actual']:.4f}  "
                  f"pred {worst['pred']:.4f}  se {worst['se']:.4f}")
            verdicts[(metric, knob, "A")] = ok
        for knob in KNOBS:
            b = score_cost(fits[knob])
            print(f"  {knob:5s} cost rank across spans: Spearman {b['rho']:+.3f}   "
                  f"gaps inside their own se: {b['noisy']}/{b['n']}")
            for d in b["detail"]:
                mm, pp = d["meas"]["reps"], d["pred"]["reps"]
                print(f"          n_blue={d['span']:2d}  measured {mm:12.1f}  predicted {pp:12.1f}  "
                      f"gap {d['meas']['gap']:.5f} +- {d['meas']['se_gap']:.5f}")
            verdicts[(metric, knob, "B")] = b
        print()

    a_pass = all(verdicts[(PRIMARY, k, "A")] for k in KNOBS)
    bs = [verdicts[(PRIMARY, k, "B")] for k in KNOBS]
    noisy_total = sum(b["noisy"] for b in bs)
    n_total = sum(b["n"] for b in bs)
    print("VERDICTS (primary metric only; the exploratory one cannot decide anything)")
    print(f"  A: {'HOLDS' if a_pass else 'RETRACTED'}")
    if noisy_total > n_total / 2:
        print(f"  B: NO VALID TEST  ({noisy_total}/{n_total} measured gaps sit inside their own "
              f"standard error, the branch registered in advance)")
    else:
        ok = any(math.isfinite(b["rho"]) and b["rho"] >= RHO_MIN for b in bs)
        print(f"  B: {'HOLDS' if ok else 'RETRACTED'}  "
              f"(rho {', '.join(f'{b['rho']:+.3f}' for b in bs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
