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
