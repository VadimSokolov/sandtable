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
