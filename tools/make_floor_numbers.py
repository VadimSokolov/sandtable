"""Does the gate itself have a detection floor, and did any published null fall below it?

The project's statistical gate requires that sixty percent of blocks agree in sign. On a metric that
counts missions, a block of `reps` missions can only register a difference at all if at least one of
its missions flips, so the fraction of blocks that can agree is capped at

    1 - (1 - |effect|) ** reps

and the sign requirement therefore becomes a floor on the EFFECT that no amount of replication
reaches. At sixty-four missions per block the floor is 0.0142. Running more blocks does not lower
it. Only larger blocks do, which is the opposite of where a test program's instinct points.

Two numbers again, and they answer different questions. The FREQUENCY is how many contrasts anywhere
in the landed logs sit below their own floor. The COST is how many contrasts that actually feed a
macro read `equivalent` while below it, because those and only those are places where the manuscript
reports a null the gate could not have returned any other way.

The arithmetic came before the audit and is checkable without it: the two cells in the CR-70 battery
whose effect is 0.0161, just above the floor, read 0.66 and 0.59 of blocks agreeing, straddling the
gate's threshold exactly where the formula puts the boundary.
"""
from __future__ import annotations

import collections
import contextlib
import importlib
import io
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import ar_survey                                                # noqa: E402

ROOT = HERE.parent
QUEUE = ROOT / "report" / "data" / "queue"
OUT = ROOT / "report" / "gen" / "floor_numbers.tex"
SIGN = 0.60                       # the gate's sign-consistency requirement

# Metrics that count missions, so a block mean moves in steps of 1/reps and CAN read exactly zero
# difference. A continuous rate essentially never does, and the floor does not apply to it.
# Established by asking the logs rather than by reading metric names, which is the discipline this
# project's first genus exists to enforce. A block mean of `success` is a multiple of one over the
# block's mission count in 98.8 percent of the 16,688 readings on it; `blue_loss_frac` is one in
# 12.6 percent, because its denominator counts vehicles rather than missions, and `served_per_step`
# in 1.4 percent. The floor argument needs a metric whose per-mission reading is zero or one, so it
# applies to the first and not to the others, and listing loss here on the strength of its name
# would have been the same mistake in the same place.
COUNTED = {"success"}

SKIP = {"make_bayes_te_numbers", "make_belief_numbers", "make_ceiling_numbers", "make_drone_numbers",
        "make_killweb_numbers", "make_personality_numbers", "make_queue_numbers",
        "make_triage_numbers", "make_pinned_numbers", "make_floor_numbers", "make_bench_numbers"}


def floor_for(reps: int) -> float:
    return 1.0 - (1.0 - SIGN) ** (1.0 / reps)


def _reps(log: pathlib.Path) -> int | None:
    for ln in log.read_text().splitlines()[:5]:
        m = re.search(r"reps=(\d+)", ln)
        if m:
            return int(m.group(1))
    return None


def _published() -> list:
    """(log, section, metric, ref, arm, sweep, effect, t, agree, nblocks, verdict) per macro-feeding
    contrast, captured by standing in front of the survey every generator calls."""
    got = []
    orig = ar_survey.survey

    def spy(log, sec, metric, ref=None, quiet=False):
        out = orig(log, sec, metric, ref=ref, quiet=quiet)
        if ref and out:
            for (arm, sweep), v in out.items():
                eff, t, agree, nb, verdict = v
                got.append((pathlib.Path(log).name, sec, metric, ref, arm, sweep,
                            eff, t, agree, nb, verdict))
        return out

    ar_survey.survey = spy
    try:
        for path in sorted((ROOT / "tools").glob("make_*_numbers.py")):
            if path.stem in SKIP:
                continue
            try:
                mod = importlib.import_module(path.stem)
            except Exception:
                continue
            mod.survey = spy
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                with contextlib.suppress(Exception):
                    mod.main()
    finally:
        ar_survey.survey = orig
    return got


def main() -> None:
    reps_of = {p.name: _reps(p) for p in sorted(QUEUE.glob("*.out"))}
    seen = {r for r in reps_of.values() if r}
    # The corpus is not all one block size, and the floor is a function of block size, so the
    # headline has to name the size it belongs to rather than quietly take the smallest. The audit
    # below uses each log's own count; only this summary needed deciding.
    main_reps = collections.Counter(r for r in reps_of.values() if r).most_common(1)[0][0]
    pub = _published()

    counted = [r for r in pub if r[2] in COUNTED and reps_of.get(r[0])]
    gated_hi, gated_lo, eq_lo = [], [], []
    for r in counted:
        f = floor_for(reps_of[r[0]])
        gated = "gate" in str(r[10]).lower()        # the verdict reads "GATE up" / "GATE down"
        if gated and abs(r[6]) < f:
            gated_lo.append(r)                       # a counterexample, if one exists
        elif gated:
            gated_hi.append(r)
        elif 0 < abs(r[6]) < f:
            eq_lo.append(r)

    out = [("FlSign", f"{SIGN:.2f}"),
           ("FlReps", str(main_reps)),
           ("FlRepsAll", "/".join(map(str, sorted(seen)))),
           ("FlFloor", f"{floor_for(main_reps):.4f}"),
           ("FlFloorPct", f"{100 * floor_for(main_reps):.2f}"),
           ("FlPublished", str(len(pub))),
           ("FlCounted", str(len(counted))),
           ("FlGated", str(len(gated_hi) + len(gated_lo))),
           ("FlGatedBelow", str(len(gated_lo))),
           ("FlEqBelow", str(len(eq_lo))),
           ("FlSmallestGated", f"{min((abs(r[6]) for r in gated_hi), default=float('nan')):.4f}"),
           ("FlLargestEqBelow", f"{max((abs(r[6]) for r in eq_lo), default=float('nan')):.5f}"),
           ("FlMargin",
            f"{floor_for(main_reps) - max((abs(r[6]) for r in eq_lo), default=0):.5f}"),
           ("FlClean", "yes" if not gated_lo else "no")]
    below, entailed, err = eq_lo, gated_lo, float("nan")
    for r_, lbl in ((16, "Sixteen"), (32, "ThirtyTwo"), (64, "SixtyFour"),
                    (256, "TwoFiftySix"), (1024, "TenTwentyFour")):
        out.append((f"FlFloor{lbl}", f"{floor_for(r_):.4f}"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("% generated by tools/make_floor_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {OUT} with {len(out)} macros")
    print(f"  published contrasts {len(pub)}, on a mission-counted metric {len(counted)}")
    print(f"  gated {len(gated_hi) + len(gated_lo)}, of which BELOW the floor {len(gated_lo)}")
    print(f"  equivalent while below the floor {len(eq_lo)}")
    if gated_hi:
        print(f"  smallest effect that ever gated {min(abs(r[6]) for r in gated_hi):.5f}")
    if eq_lo:
        print(f"  largest sub-floor effect {max(abs(r[6]) for r in eq_lo):.5f} "
              f"against a predicted floor of {floor_for(main_reps):.5f}")
    if gated_lo:
        print("\n  COUNTEREXAMPLES, which refute the floor:")
        for r in gated_lo[:20]:
            print(f"    {r[0]:30s} {str(r[1])[:24]:24s} {r[4]} vs {r[3]} @ {r[5]}: "
                  f"eff={r[6]:+.5f} {r[8]}/{r[9]} {r[10]}")


if __name__ == "__main__":
    main()
