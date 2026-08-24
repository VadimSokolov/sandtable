"""Score a ProjectGL confirmation run against the tier-1 predictions registered before it.

Usage:  python3 tools/score_bridge.py tier2.csv [--log report/data/queue/st-crosstier-<job>.out]

The protocol is `doc/cross-tier-protocol.md`. The registration is on SIGN and ORDER OF MAGNITUDE,
never on value: two tiers agreeing to four decimals would be evidence of a bug rather than of
validity. This script exists so that the comparison cannot be re-specified after the tier-2 numbers
are seen, which is the only failure mode a cross-tier confirmation really has.

It refuses to score a file whose arms do not match the registration, and it refuses to score fewer
than five missions per arm, because a protocol that quietly accepts three is not a protocol.
"""
from __future__ import annotations

import argparse
import csv
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ar_survey import survey                                    # noqa: E402

ROOT = HERE.parent
SEC = "X1 the bridge operating point, blind vs refund vs admit"
ARMS = ("blind", "refund", "admit")
CELL = "0"                          # C0, the registered link state
MIN_MISSIONS = 5
FRACTION_OF_TIER_ONE = 0.10         # the registered magnitude floor

# The registered direction of each shared observable, as declared in the protocol before any
# tier-2 data existed. +1 means a working discard rule should RAISE it.
DIRECTION = {"success": +1, "arrived_frac": +1, "blue_losses": -1, "mission_time": 0}


def _tier_one(log: str) -> dict:
    """Point estimates at the registered cell, read from the crosstier battery's own log."""
    pred = {}
    for metric in DIRECTION:
        lv = survey(log, SEC, metric, quiet=True)
        if not lv:
            continue
        # `survey` returns {arm: [levels]}; the sweep is comms_level = 0, 2 and C0 is index 0.
        if all(a in lv for a in ARMS):
            pred[metric] = {a: lv[a][0] for a in ARMS}
    return pred


def _tier_two(path: str) -> dict:
    rows = list(csv.DictReader(open(path, newline="")))
    if not rows:
        raise SystemExit(f"{path}: no rows")
    got = {r["arm"].strip() for r in rows}
    missing = set(ARMS[:2]) - got                # blind and refund are the registered pair
    if missing:
        raise SystemExit(f"{path}: the registration names arms {ARMS[:2]}, missing {sorted(missing)}")
    if got - set(ARMS):
        raise SystemExit(f"{path}: unregistered arms present: {sorted(got - set(ARMS))}. "
                         "Scoring an arm that was not registered is re-specifying the protocol.")
    out: dict = {}
    for arm in sorted(got):
        mine = [r for r in rows if r["arm"].strip() == arm]
        if len(mine) < MIN_MISSIONS:
            raise SystemExit(f"{path}: arm {arm!r} has {len(mine)} missions, protocol requires "
                             f"at least {MIN_MISSIONS}")
        out[arm] = {}
        for metric in DIRECTION:
            vals = [float(r[metric]) for r in mine if r.get(metric) not in (None, "")]
            out[arm][metric] = (sum(vals) / len(vals)) if vals else float("nan")
        out[arm]["_n"] = len(mine)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tier2")
    ap.add_argument("--log", default=None,
                    help="crosstier battery log; defaults to the newest in report/data/queue")
    a = ap.parse_args()

    log = a.log
    if log is None:
        cand = sorted((ROOT / "report" / "data" / "queue").glob("st-crosstier-*.out"))
        if not cand:
            raise SystemExit("no crosstier log found; the tier-1 side must be registered first")
        log = str(cand[-1])

    t1, t2 = _tier_one(log), _tier_two(a.tier2)
    if not t1:
        raise SystemExit(f"{log}: no registered predictions at the bridge operating point")

    print(f"tier 1: {log}")
    print(f"tier 2: {a.tier2}  ({', '.join(f'{k} n={v[chr(95)+chr(110)]}' for k, v in t2.items())})\n")
    print(f"{'observable':<14} {'tier-1 gap':>12} {'tier-2 gap':>12} {'ratio':>8}  verdict")
    print("-" * 66)

    verdicts = []
    for metric, want in DIRECTION.items():
        if metric not in t1 or "refund" not in t2:
            continue
        g1 = t1[metric]["refund"] - t1[metric]["blind"]
        g2 = t2["refund"][metric] - t2["blind"][metric]
        if want == 0:
            print(f"{metric:<14} {g1:>12.4f} {g2:>12.4f} {'':>8}  (reported, not registered)")
            continue
        ratio = (g2 / g1) if g1 else float("nan")
        if math.isnan(g2):
            v = "MISSING"
        elif (g2 > 0) != (g1 > 0):
            v = "FAILS: sign flipped"
        elif abs(g2) < FRACTION_OF_TIER_ONE * abs(g1):
            v = f"FAILS: under {FRACTION_OF_TIER_ONE:.0%} of tier 1"
        else:
            v = "CONFIRMS"
        verdicts.append(v)
        print(f"{metric:<14} {g1:>12.4f} {g2:>12.4f} {ratio:>8.2f}  {v}")

    print("-" * 66)
    if not verdicts:
        print("no registered observable could be scored")
        raise SystemExit(2)
    bad = [v for v in verdicts if v != "CONFIRMS"]
    if bad:
        print(f"BRIDGE FAILS on {len(bad)} of {len(verdicts)} registered observables.")
        print("Per the protocol this is a publishable result. Do NOT re-run at a different")
        print("operating point in search of a better one; name the abstraction boundary instead.")
        raise SystemExit(1)
    print(f"BRIDGE CONFIRMS on all {len(verdicts)} registered observables.")


if __name__ == "__main__":
    main()
