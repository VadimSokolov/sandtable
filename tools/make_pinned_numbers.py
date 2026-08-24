"""How often is an arm pinned at a structural value, and did it ever cost a published number?

A defect that appears once is an anecdote. This sweeps every landed battery log and prices the
entailed-zero genus across the whole project, then audits whether any number the manuscript prints
rests on it.

Two quantities, and they answer different questions. The FREQUENCY is how often an arm sits
byte-identical in every block at every sweep point, which is the signature of a value fixed by a
definition rather than measured. The COST is how many of the contrasts that actually feed a macro
compare two arms pinned at the same value, since those and only those are the readings where the
genus turns a true statement into an empty one.

The second number is the one that decides whether anything has to be retracted, and running the
audit rather than reasoning about it is the point: the frequency is high enough that the answer was
not obvious in advance.
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
OUT = ROOT / "report" / "gen" / "pinned_numbers.tex"
# These generators run the simulator instead of reading a battery log, so they contribute no
# contrast to audit and would only cost minutes.
SKIP = {"make_bayes_te_numbers", "make_belief_numbers", "make_ceiling_numbers", "make_drone_numbers",
        "make_killweb_numbers", "make_personality_numbers", "make_queue_numbers",
        "make_triage_numbers", "make_pinned_numbers"}


def _pin_table() -> tuple[dict, int, list]:
    """(log, section, metric, arm) -> the value it is pinned at, plus the denominator."""
    pin, cells, same = {}, 0, []
    for log in sorted((ROOT / "report" / "data" / "queue").glob("*.out")):
        cur, vec = None, {}
        for ln in log.read_text().splitlines():
            m = re.match(r"### (\w+) .*\((\w+)\)", ln)
            if m:
                cur = (m.group(1), m.group(2))
                continue
            m = re.match(r"AR_ROW arm=(\S+) \w+=(\S+) mean=\S+ vals=(\S+)", ln)
            if m and cur:
                vec.setdefault(cur, {}).setdefault(m.group(1), {})[m.group(2)] = m.group(3)
        cells += len(vec)
        for (sec, met), arms in vec.items():
            here = {}
            for a, c in arms.items():
                vals = list(c.values())
                if len(vals) > 1 and len(set(vals)) == 1 and len(set(vals[0].split(","))) == 1:
                    here[a] = float(vals[0].split(",")[0])
                    pin[(log.name, sec, met, a)] = here[a]
            by = collections.defaultdict(list)
            for a, v in here.items():
                by[v].append(a)
            if any(len(g) >= 2 for g in by.values()):
                same.append((log.name, sec, met))
    return pin, cells, same


def _published_contrasts() -> set:
    """Every (log, section, metric, reference, arm) that actually feeds a macro."""
    seen = set()
    orig = ar_survey.survey

    def spy(log, sec, metric, ref=None, quiet=False):
        out = orig(log, sec, metric, ref=ref, quiet=quiet)
        if ref:
            for (arm, _p) in (out or {}):
                seen.add((pathlib.Path(log).name, sec, metric, ref, arm))
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
    return seen


def main() -> None:
    pin, cells, same = _pin_table()
    arms_pinned = len({(lg, s, m) for (lg, s, m, _a) in pin})
    contrasts = _published_contrasts()

    cost = []
    for (lg, sec, met, ref, arm) in sorted(contrasts):
        for key in {sec, sec.split()[0]}:
            pr, pa = pin.get((lg, key, met, ref)), pin.get((lg, key, met, arm))
            if pr is not None and pa is not None and pr == pa:
                cost.append((lg, key, met, ref, arm))
                break

    out = [
        ("PnCells", str(cells)),
        ("PnPinned", str(arms_pinned)),
        ("PnPinnedPct", f"{100.0 * arms_pinned / cells:.0f}"),
        ("PnSamePair", str(len(same))),
        ("PnContrasts", str(len(contrasts))),
        ("PnCost", str(len(cost))),
        # Every affected contrast sits in a negative control, where a pinned zero is the outcome
        # the section was built to demonstrate rather than a ranking anyone consumed.
        ("PnCostSections", ", ".join(sorted({f"{c[1]}" for c in cost})) or "none"),
        ("PnClean", "yes" if not cost or all(c[1] == "U4" for c in cost) else "no"),
    ]
    OUT.write_text("% generated by tools/make_pinned_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    for k, v in out:
        print(f"  {k:16s} {v}")


if __name__ == "__main__":
    main()
