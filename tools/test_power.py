"""What a mission test can and cannot detect, before it is run.

This is the ceiling account turned around. CR-74 fits one constant per capability on a latent
margin, so the effect a test REPORTS at a given baseline is determined rather than free:

    effect(b) = Phi(Phi^-1(b) + delta) - b

and the block-to-block noise of the paired difference is close to the binomial value at the block's
mission count, measured at 1.30 times it across the uncensored cells of the CR-70 battery, with a
spread of 0.27 between cells. Put those together and three questions a test program asks before
committing to a trial have arithmetic answers:

  * At this operating point, what effect will the test report for a capability worth this much?
  * How many blocks does it take before that effect clears the gate?
  * Which operating points can answer the question at all inside the blocks I can afford?

The third is the one worth the trouble. A test planned where the baseline sits near a bound will
report a small number and clear nothing, no matter how long it runs, and the report will read as
evidence the capability does not help. This says so in advance.

    python3 tools/test_power.py --delta 0.454
    python3 tools/test_power.py --delta 0.454 --blocks 32 --reps 64
    python3 tools/test_power.py --invert --delta 0.2 --blocks 32

Everything here is conditional on the model, which is fitted rather than derived, and on one
simulator's scenario family. It is a planning aid, not a guarantee, and the registered test of the
model it rests on is CR-75.
"""
from __future__ import annotations

import argparse
import math
from statistics import NormalDist

N = NormalDist()
T_GATE = 1.70                 # the project's full tier
NOISE_K = 1.30                # measured paired sd over binomial sd, CR-70 battery, uncensored cells
NOISE_K_LO, NOISE_K_HI = 0.83, 1.86      # the range across those cells


def effect(b: float, delta: float) -> float:
    b = min(max(b, 1e-9), 1 - 1e-9)
    return N.cdf(N.inv_cdf(b) + delta) - b


def paired_sd(b: float, reps: int, k: float = NOISE_K) -> float:
    return k * math.sqrt(max(b * (1 - b), 0.0) / reps)


def blocks_needed(b: float, delta: float, reps: int, k: float = NOISE_K) -> float:
    e, s = effect(b, delta), paired_sd(b, reps, k)
    if e <= 0:
        return float("inf")
    if s <= 0:
        return 1.0                     # a pinned baseline has no noise and no signal either
    return (T_GATE * s / e) ** 2


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delta", type=float, default=0.454,
                    help="the capability's latent worth. 0.454 is the backlog bound and 0.394 the "
                         "admission rule, both fitted in CR-74")
    ap.add_argument("--reps", type=int, default=64, help="missions per block")
    ap.add_argument("--blocks", type=int, default=0,
                    help="blocks available; when given, each baseline is marked gate or not")
    ap.add_argument("--invert", action="store_true",
                    help="report the baseline window a fixed budget can detect in")
    ap.add_argument("--k", type=float, default=NOISE_K, help="paired sd over binomial sd")
    a = ap.parse_args()

    grid = [0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90,
            0.95, 0.98, 0.99, 0.995, 0.999]

    if a.invert and a.blocks:
        ok = [b for b in grid if blocks_needed(b, a.delta, a.reps, a.k) <= a.blocks]
        print(f"capability worth delta={a.delta}, {a.blocks} blocks of {a.reps} missions\n")
        if not ok:
            print("  NO baseline on the grid can gate this capability at this budget.")
        else:
            print(f"  detectable where baseline success lies between {min(ok):.3f} and {max(ok):.3f}")
            print(f"  best placed at baseline 0.500, where the reported effect is largest "
                  f"({effect(0.5, a.delta):+.4f})")
        print("\n  A test placed outside that window reports a small number and clears nothing,")
        print("  and the report reads as evidence the capability did not help.")
        return

    print(f"capability worth delta={a.delta} on the latent scale, "
          f"blocks of {a.reps} missions, gate at |t| >= {T_GATE}")
    print(f"paired noise taken at {a.k:.2f} times binomial "
          f"(measured range {NOISE_K_LO:.2f} to {NOISE_K_HI:.2f})\n")
    head = f"{'baseline':>9s} {'reported':>9s} {'block sd':>9s} {'blocks to gate':>15s}"
    if a.blocks:
        head += f" {'at ' + str(a.blocks) + ' blocks':>16s}"
    print(head)
    for b in grid:
        e, s = effect(b, a.delta), paired_sd(b, a.reps, a.k)
        n = blocks_needed(b, a.delta, a.reps, a.k)
        row = (f"{b:9.3f} {e:+9.4f} {s:9.4f} "
               f"{('infinite' if n == float('inf') else f'{n:,.0f}'):>15s}")
        if a.blocks:
            t = e / (s / math.sqrt(a.blocks)) if s > 0 else float("inf")
            row += f" {('GATE t=' + f'{t:.1f}') if n <= a.blocks else 'no':>16s}"
        print(row)
    print("\nThe reported effect is largest at baseline 0.500 and falls to nothing at either bound.")
    print("A capability's worth is a constant; what varies is how much of it the metric can show.")


if __name__ == "__main__":
    main()
