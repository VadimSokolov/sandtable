#!/usr/bin/env python3
"""Score CR-75 against its two registered falsifiers.

Nothing is estimated from the new data. `delta` is fixed at CR-74's fitted values and the predicted
effect at a cell whose control arm reads baseline `b` is Phi(Phi^-1(b) + delta) - b.

  Falsifier one, the level: RMS deviation of observed from predicted effects over every gradeable
  cell, above 0.045, which is twice CR-74's out-of-sample RMS.
  Falsifier two, the shape: the success gain's maximum falling outside the baseline band 0.35-0.65.

    python3 tools/score_ceiling.py experiments/results/ar_logs/*.out
"""
from __future__ import annotations

import math
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score_latent_grid import _ppf, _cdf                       # noqa: E402

DELTA = {"boundOne": 0.454, "admits": 0.394}     # CR-74, not refitted
CONTROL = "blindUnbound"
RMS_MAX = 0.045                                   # registered
BAND = (0.35, 0.65)                               # registered
ROW = re.compile(r"^AR_ROW arm=(?P<arm>\S+)\s+(?P<key>\w+)=(?P<lvl>\S+)\s+mean=(?P<mean>[-\d.]+)")
SEC = re.compile(r"^### (?P<tag>X\d)\s+(?P<title>.*?)\s*\((?P<metric>\w+)\)\s*$")


def parse(paths):
    out = {}
    for p in paths:
        sec = None
        for ln in pathlib.Path(p).read_text().split("\n"):
            m = SEC.match(ln)
            if m:
                sec = (m.group("tag"), m.group("metric"))
                out.setdefault(sec, {})
                continue
            m = ROW.match(ln)
            if m and sec:
                out[sec].setdefault(m.group("lvl"), {})[m.group("arm")] = float(m.group("mean"))
    return out


def main() -> int:
    paths = sys.argv[1:] or sorted(
        (pathlib.Path(__file__).resolve().parents[1]
         / "experiments" / "results" / "ar_logs").glob("*.out"))
    data = parse(paths)
    if not data:
        raise SystemExit("no AR_ROW sections found")

    print("CR-75 scored against its two registered falsifiers")
    print(f"  delta fixed at {DELTA}, nothing refitted")
    print(f"  F1 fails if RMS > {RMS_MAX}; F2 fails if the success maximum leaves {BAND}\n")

    devs, curve, bysec = [], [], {}
    for (tag, metric), lvls in sorted(data.items()):
        if metric != "success":
            continue
        print(f"  {tag} {metric}")
        for lvl, arms in sorted(lvls.items(), key=lambda z: float(z[0])):
            b = arms.get(CONTROL)
            if b is None or not 0.0 < b < 1.0:
                continue
            for arm, d in DELTA.items():
                if arm not in arms:
                    continue
                pred = _cdf(_ppf(b) + d) - b
                obs = arms[arm] - b
                devs.append(obs - pred)
                bysec.setdefault(tag, []).append(obs - pred)
                curve.append((b, obs))
                print(f"    lvl={lvl:>4s} base={b:.4f}  {arm:10s} "
                      f"pred{pred:+.4f} obs{obs:+.4f} dev{obs - pred:+.4f}")
    if not devs:
        raise SystemExit("no gradeable success cells")

    rms = math.sqrt(sum(d * d for d in devs) / len(devs))
    # X1 and X2 move the baseline by opposing strength; X3 moves it by span. The registration
    # named X3 as the section that decides whether the model is about the metric or merely about
    # opposing strength, so the split is reported whatever the pooled number says.
    print()
    for tag in sorted(bysec):
        d = bysec[tag]
        how = "span" if tag == "X3" else "opposing strength"
        print(f"  {tag} ({how:17s}): RMS {math.sqrt(sum(x * x for x in d) / len(d)):.4f} "
              f"over {len(d):2d} cells, worst {max(d, key=abs):+.4f}")
    peak_b = max(curve, key=lambda z: z[1])[0]
    f1 = rms <= RMS_MAX
    f2 = BAND[0] <= peak_b <= BAND[1]
    print(f"\n  F1 level: RMS {rms:.4f} over {len(devs)} cells   {'PASS' if f1 else 'FAIL'}")
    print(f"  F2 shape: success gain peaks at baseline {peak_b:.4f}   {'PASS' if f2 else 'FAIL'}")
    print(f"\nVERDICT CR-75: {'HOLDS' if f1 and f2 else 'RETRACTED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
