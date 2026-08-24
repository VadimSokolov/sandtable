"""Read one battery section as a table of arms against sweep points, with the gate applied.

Every battery in this project ends up being read the same way and the reading has been hand-written
each time, which is how two of the instrument defects in the ledger got in. This is that reading,
once: pick a section and a metric, choose a reference arm, and get every other arm's paired contrast
against it at every sweep point, gated by `ar_gate` with the metric's own floor, plus the
equivalence verdict for the contrasts that do not gate.

    python3 tools/ar_survey.py st-maps-9448824.out "M1 the lever" success --ref band_blind

Without `--ref` it prints levels only, which is the right reading for an argmax over a ladder.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_FRAC, FULL_T, gate, margin, tost  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import paired  # noqa: E402


_THIN = 0.01          # a reference below one percent of its own unit cannot carry a relative margin
_RATE = {"served_per_step", "requests_per_step", "abandoned_per_step"}


def survey(log: str, sec: str, metric: str, ref: str | None = None, quiet: bool = False) -> dict:
    d = load(find(log), sec, metric)
    arms = sorted({a for a, _ in d})
    pts = sorted({k for _, k in d}, key=lambda x: (float(x) if _isnum(x) else 0.0, x))
    if ref and ref not in arms:
        raise SystemExit(f"reference arm {ref!r} not in {arms}")
    rows = {}
    if not quiet:
        print(f"# {log} :: {sec} :: {metric}" + (f"   reference {ref}" if ref else ""))
        print("arm".ljust(16) + "".join(p.rjust(11) for p in pts))
    for a in arms:
        lv = [_mean(d[(a, p)]) if (a, p) in d else float("nan") for p in pts]
        rows[a] = lv
        if not quiet:
            print(a.ljust(16) + "".join(f"{v:11.4f}" for v in lv))
    _censored_cells(log, sec, metric, d, quiet)
    _flat_reference(log, sec, metric, ref, d, pts, quiet)
    _zero_base(log, sec, metric, ref, d, pts, quiet)
    _pinned_arm(log, sec, metric, d, arms, pts, quiet)
    _duplicate_dose(log, sec, metric, d, arms, pts, quiet)
    _thin_base(log, sec, metric, ref, d, pts, quiet)
    if not ref:
        if not quiet:
            best = {p: max(arms, key=lambda a: rows[a][i]) for i, p in enumerate(pts)}
            print("argmax".ljust(16) + "".join(best[p].rjust(11) for p in pts))
        return rows
    if not quiet:
        print(f"\ncontrasts against {ref}: effect, t, blocks agreeing, verdict")
    out = {}
    for a in arms:
        if a == ref:
            continue
        for i, p in enumerate(pts):
            if (a, p) not in d or (ref, p) not in d:
                continue
            e, t, w, n = paired({"vals": d[(a, p)]}, {"vals": d[(ref, p)]})
            base = _mean(d[(ref, p)])
            ok = gate(metric, e, t, w, n, base, t_min=FULL_T, frac=FULL_FRAC)
            eq, st = (False, 0.0) if ok else tost(e, t, n, margin(metric, base))
            verdict = ("GATE " + ("up" if e > 0 else "down")) if ok else \
                      ("equivalent" if eq else "inconclusive")
            out[(a, p)] = (e, t, w, n, verdict)
            if not quiet:
                print(f"  {a:<14} {p:>6}  {e:+9.4f}  t={t:8.2f}  {w:2d}/{n:2d}  {verdict}"
                      + (f"  (tost {st:.2f})" if not ok else ""))
    return out


def _pinned_arm(log, sec, metric, d, arms, pts, quiet) -> int:
    """Announce an arm that is byte-identical in every block at every sweep point.

    This is the backstop for a defect the other three guards cannot see, because all three audit the
    REFERENCE arm and this one lives in the treatments. CR-65 measured `busy_stale` on three
    consoles that differ by two orders of magnitude in what they buy, and got a byte-identical
    reading from all three: `stale_check = "before"` is DEFINED as never working a stale request and
    the metric counts exactly that, so its zero is entailed rather than measured, and the other two
    arms reach the same zero because nothing survives their buffers long enough to go stale. The
    contrast against the reference was fine and correctly gated. What was unreadable was the RANKING
    among the treatments, and no guard was pointed at it because that contrast was never formed.

    In a stochastic simulator at thirty-two blocks, exact repetition across every block and every
    sweep point is the signature of a structural value, not of a quiet effect. This guard does not
    decide whether the value is entailed by a definition or merely degenerate in a regime. It
    demands that somebody say which, in the same spirit as `_flat_reference`: what is never
    acceptable is not knowing.
    """
    bad = []
    for a in arms:
        vecs = [d[(a, p)] for p in pts if (a, p) in d]
        if len(vecs) < 2:
            continue
        if all(v == vecs[0] for v in vecs) and len(set(vecs[0])) == 1:
            bad.append((a, vecs[0][0]))
    if not bad:
        return 0
    msg = (f"!! PINNED ARM: {', '.join(f'{a} at {v:g}' for a, v in bad)} on {metric!r} is "
           f"byte-identical in every block at every sweep point. A value that repeats exactly is "
           f"structural. Classify it (entailed by the arm's definition, or degenerate in this "
           f"regime) before ranking anything against it on this axis")
    if not quiet:
        print(msg)
    else:
        sys.stderr.write(f"{log}::{sec}: {msg}\n")
    return len(bad)


def _duplicate_dose(log, sec, metric, d, arms, pts, quiet) -> int:
    """Announce adjacent sweep points that are the same dose wearing two labels.

    CR-65's cadence control swept `reask_hold` over seven values and was reported as flat across
    sixty-four-fold. Two of the seven quantize to the same integer number of steps, so they are one
    dose: every arm is byte-identical between them, the sweep has six levels rather than seven, and
    the range over which flatness was demonstrated is half what the section claimed. A control that
    flatters its own flatness with a duplicated dose has not been run at the range it reports.

    `_flat_reference` cannot see this because it requires the WHOLE row to be constant.
    """
    bad = []
    for i in range(len(pts) - 1):
        a1, a2 = pts[i], pts[i + 1]
        cells = [(a, a1, a2) for a in arms if (a, a1) in d and (a, a2) in d]
        if cells and all(d[(a, x)] == d[(a, y)] for a, x, y in cells):
            bad.append((a1, a2, len(cells)))
    if not bad:
        return 0
    msg = ("!! DUPLICATE DOSE: " + "; ".join(
        f"{x} and {y} are byte-identical in all {n} arms" for x, y, n in bad)
        + f" on {metric!r}. The sweep has fewer distinct levels than it reports, so any range "
          f"claimed across them is narrower than stated")
    if not quiet:
        print(msg)
    else:
        sys.stderr.write(f"{log}::{sec}: {msg}\n")
    return len(bad)


def _thin_base(log, sec, metric, ref, d, pts, quiet) -> int:
    """Announce a reference so near zero that the RELATIVE margin has collapsed toward nothing.

    Outside `RATE_METRICS` the gate's materiality margin is a fraction of the reference level, so a
    reference of exactly zero makes it zero. `_zero_base` catches that. It does not catch a
    reference of 0.000541, which is what `worksGhost` reads at six assets: the margin there is
    0.0000325 of the console's clock, and a repair worth half a thousandth of a percent of operator
    time gates as material with a large t.

    This announces rather than re-margins, because the scoring surface is frozen and a margin
    changed after the fact would move landed verdicts silently. The honest handling is to read such
    a cell as a level, not as a gated effect.
    """
    if not ref or metric in _RATE:
        return 0
    thin = [p for p in pts if (ref, p) in d and 0.0 < abs(_mean(d[(ref, p)])) < _THIN]
    if not thin:
        return 0
    lv = ", ".join(f"{p}={_mean(d[(ref, p)]):.6f}" for p in thin)
    msg = (f"!! THIN BASE: {ref!r} on {metric!r} is nonzero but below {_THIN:g} at {lv}. The "
           f"relative margin there is a fraction of almost nothing, so a difference of no "
           f"operational size can still gate. Read these cells as levels, not as gated effects")
    if not quiet:
        print(msg)
    else:
        sys.stderr.write(f"{log}::{sec}: {msg}\n")
    return len(thin)


def _censored_cells(log, sec, metric, d, quiet) -> int:
    """Announce cells containing an undefined value, because a NaN that reaches a gate is a verdict.

    `answer_step_ratio` is undefined when the impatient half of the fleet receives nothing at all. It
    used to stand in the fleet size, which averages and gates and reads as a very large but finite
    stratification; it is now NaN. NaN compares false against every threshold, so a censored cell
    would quietly come back "inconclusive", which is a verdict rather than a refusal. This makes it a
    refusal.
    """
    bad = [(a, p) for (a, p), v in d.items() if any(x != x for x in v)]
    if not bad:
        return 0
    msg = (f"!! CENSORED: {len(bad)} of {len(d)} cells of {sec!r} on {metric!r} contain an undefined "
           f"value and cannot be scored: " + ", ".join(f"{a}@{p}" for a, p in sorted(bad)[:6]))
    if not quiet:
        print(msg)
    else:
        sys.stderr.write(f"{log}: {msg}\n")
    return len(bad)


def _zero_base(log, sec, metric, ref, d, pts, quiet) -> int:
    """Announce a reference sitting at exactly zero, because the relative margin then vanishes.

    For every metric outside `RATE_METRICS` the gate's materiality margin is a FRACTION of the
    reference level. A reference of exactly zero makes that margin zero, so any difference at all
    gates as material and no equivalence can ever be declared. That is the mirror image of the flat
    reference above: there the contrast could not move, here it cannot fail to. Both look like
    ordinary contrasts in the output.
    """
    from ar_gate import RATE_METRICS
    if not ref or metric in RATE_METRICS:
        return 0
    bad = [p for p in pts if (ref, p) in d and _mean(d[(ref, p)]) == 0.0]
    if not bad:
        return 0
    msg = (f"!! ZERO-BASE REFERENCE: {ref!r} is exactly 0 at {', '.join(bad)} on {metric!r}, so the "
           f"relative margin is 0 and every difference there gates by construction")
    if not quiet:
        print(msg)
    else:
        sys.stderr.write(f"{log}::{sec}: {msg}\n")
    return len(bad)


def _flat_reference(log, sec, metric, ref, d, pts, quiet) -> bool:
    """Warn when the reference arm is byte-identical across the sweep, because then it is a constant.

    A contrast against an arm the treatment cannot move is a level wearing a difference. The paper
    came within one round of publishing three of them: an operator that checks every answer catches
    every wrong one by construction, so its automation error rate and its harm channel are both inert
    and its cells came back byte-identical. Nothing in the numbers said so, because a contrast
    against a constant looks exactly like a contrast against anything else. This says so.

    The check is deliberately a warning and not an error. A reference that does not move is sometimes
    the whole point of a control arm; what is never acceptable is not KNOWING.
    """
    if not ref or len(pts) < 2:
        return False
    vecs = [tuple(d[(ref, p)]) for p in pts if (ref, p) in d]
    if len(vecs) < 2 or len(set(vecs)) > 1:
        return False
    if not quiet:
        print(f"!! FLAT REFERENCE: {ref!r} is byte-identical at all {len(vecs)} sweep points of "
              f"{sec!r} on {metric!r}. Every contrast below is a level, not a difference.")
    else:
        sys.stderr.write(f"!! FLAT REFERENCE {log}::{sec}::{metric}: {ref} is byte-identical "
                         f"across all {len(vecs)} sweep points\n")
    return True


def _mean(v):
    return sum(v) / len(v)


def _isnum(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("section", help="a substring of the section header, without the metric")
    ap.add_argument("metric")
    ap.add_argument("--ref", default=None)
    a = ap.parse_args()
    survey(a.log, a.section, a.metric, a.ref)


if __name__ == "__main__":
    main()
