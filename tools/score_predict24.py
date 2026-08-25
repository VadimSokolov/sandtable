#!/usr/bin/env python3
"""Score CR-78 against its registered falsifiers.

CR-78 froze a vector of latent offsets, fitted at n_blue=8 alone, and used them to predict an
operating point nobody had simulated. This file is written before the n_blue=24 tables exist, so
that scoring is transcription. The registration in doc/autoresearch-conjectures.md fixes all four
parts, and part D is the one that matters most for reading the rest: mission success at this span
is predicted to sit at ceiling within six hundredths of a standard error, so it is NOT scored as a
test of the shape and a ceiling reading is not a confirmation of anything.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from score_latent_grid import cell, fit_and_predict, _ppf, _cdf, SPANS   # noqa: E402

SPAN = 24
PREV = 16
B_TOL = 0.010            # registered: anchor prediction error in loss units
C_DIRECTION = {"loss": "fall", "succ": "fall", "srv": "rise"}   # registered


def offsets(knob: str, metric: str, shape: str = "probit") -> dict:
    f = fit_and_predict(knob, metric, shape=shape)
    return f["anchor"], f["delta"], f


def extrapolated_base(f) -> float:
    xs = list(SPANS)
    ys = [_ppf(f["cells"][s]["val"][f["anchor"]]) for s in xs]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b1 = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return _cdf(b1 * SPAN + (my - b1 * mx))


def spread_over_se(knob: str, metric: str, span: int) -> float:
    c = cell(knob, span, metric)
    v = list(c["val"].values()); e = list(c["se"].values())
    return (max(v) - min(v)) / (sum(e) / len(e))


def score_a(knob: str) -> dict:
    """Measure only the anchor at the new span; predict the other six. Scored against both
    controls, because CR-77 showed a threshold with no control under it can be met by a predictor
    with no shape in it."""
    c24 = cell(knob, SPAN, "loss")
    out = {}
    for shape in ("probit", "linear", "null"):
        anchor, delta, _ = offsets(knob, "loss", shape=shape)
        base = c24["val"][anchor]
        err = []
        for d in c24["designs"]:
            if d == anchor:
                continue                       # entailed by construction, excluded at registration
            pred = _cdf(_ppf(base) + delta[d]) if shape == "probit" else \
                min(max(base + delta[d], 0.0), 1.0)
            err.append(pred - c24["val"][d])
        out[shape] = math.sqrt(sum(e * e for e in err) / len(err))
    v = list(c24["val"].values())
    out["spread"] = max(v) - min(v)
    out["pass"] = out["probit"] < min(out["linear"], out["null"]) and out["probit"] < 0.5 * out["spread"]
    return out


def score_b(knob: str) -> dict:
    _, _, f = offsets(knob, "loss")
    pred = extrapolated_base(f)
    got = cell(knob, SPAN, "loss")["val"][f["anchor"]]
    return {"anchor": f["anchor"], "pred": pred, "got": got,
            "err": pred - got, "pass": abs(pred - got) <= B_TOL}


def main() -> int:
    print(f"CR-78 scored at n_blue={SPAN}, predictions frozen at n_blue=8\n")

    print("D  (declared untestable in advance, reported so it is not misread)")
    for knob in ("qcap", "disc"):
        c = cell(knob, SPAN, "succ")
        v = list(c["val"].values()); e = list(c["se"].values())
        sp, se = max(v) - min(v), sum(e) / len(e)
        print(f"   {knob:5s} success spans {sp:.5f} over se {se:.5f} = {sp / se:.2f} se   "
              f"best {max(v):.4f}   {'at ceiling as predicted' if sp / se < 2 else 'NOT AT CEILING'}")
    print()

    print("A  (anchor measured, six predicted; must beat BOTH controls and half the spread)")
    a_ok = True
    for knob in ("qcap", "disc"):
        r = score_a(knob)
        a_ok &= r["pass"]
        print(f"   {knob:5s} probit {r['probit']:.4f}   linear {r['linear']:.4f}   "
              f"null {r['null']:.4f}   spread/2 {r['spread'] / 2:.4f}   "
              f"{'PASS' if r['pass'] else 'FAIL'}")
    print()

    print(f"B  (no data at the new span at all; anchor error must be within {B_TOL})")
    b_ok = True
    for knob in ("qcap", "disc"):
        r = score_b(knob)
        b_ok &= r["pass"]
        print(f"   {knob:5s} predicted {r['pred']:.4f}   measured {r['got']:.4f}   "
              f"error {r['err']:+.4f}   {'PASS' if r['pass'] else 'FAIL'}")
    print()

    print(f"C  (six registered directions, n_blue={SPAN} against n_blue={PREV})")
    c_ok = True
    for knob in ("qcap", "disc"):
        for metric, want in C_DIRECTION.items():
            a, b = spread_over_se(knob, metric, PREV), spread_over_se(knob, metric, SPAN)
            got = "rise" if b > a else "fall"
            ok = got == want
            c_ok &= ok
            print(f"   {knob:5s} {metric:5s} {a:8.1f} -> {b:8.1f}  want {want:4s} got {got:4s}  "
                  f"{'ok' if ok else 'FAILS'}")
    print()

    print("VERDICTS")
    print(f"  A: {'HOLDS' if a_ok else 'RETRACTED'}")
    print(f"  B: {'HOLDS' if b_ok else 'RETRACTED'}")
    print(f"  C: {'HOLDS' if c_ok else 'RETRACTED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
