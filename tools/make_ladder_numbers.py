"""CR-66: the requirements ladder, priced one rung at a time.

Four rungs, each costing strictly more than the one below it:

    blindUnbound   knows nothing, refuses nothing
    boundOne       knows nothing, refuses by overflow (drop the oldest at capacity one)
    boundTwo       the same at capacity two
    admits         reads a deadline field, refuses what it cannot finish
    admitsEdf      reads the same field twice, to refuse AND to order

Every increment is reported ADJACENT-RUNG, because a program office buys the next rung and not the
whole ladder, and a table of everything-against-blind makes the second rung look like it delivers
what the first one already delivered. The one place the whole-ladder gap is quoted is the collapse
cell, once, where it is the point.

Degrades gracefully: a section absent from a partial log emits nothing rather than failing, so the
tool can be run against a battery that is still going.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ar_survey import survey                                    # noqa: E402

ROOT = HERE.parent
LOG = str(ROOT / "report" / "data" / "queue" / "st-ladder-9459669.out")
OUT = ROOT / "report" / "gen" / "ladder_numbers.tex"

V1 = "V1 the four rungs on a uniform fleet"
V2 = "V2 the four rungs on a two-point fleet"
V3 = "V3 where the deadline field starts earning, against fleet heterogeneity"

RUNGS = ("blindUnbound", "boundOne", "boundTwo", "admits", "admitsEdf")
STEP = {("blindUnbound", "boundOne"): "Bound", ("boundOne", "boundTwo"): "Two",
        ("boundTwo", "admits"): "Field", ("admits", "admitsEdf"): "Order"}
WORD = {"8": "Eight", "12": "Twelve", "16": "Sixteen", "24": "TwentyFour"}
V = {"GATE up": "gates up", "GATE down": "gates down",
     "equivalent": "equivalent", "inconclusive": "inconclusive"}


def _adjacent(sec, metric, tag, spans=("8", "16", "24")):
    """Each rung against the one immediately below it, at the spans the prose quotes."""
    if not survey(LOG, sec, metric, quiet=True):
        return []                     # section absent from a partial log; emit nothing, not an error
    rows = []
    for lo, hi in STEP:
        con = survey(LOG, sec, metric, ref=lo, quiet=True)
        if not con:
            return []
        for s in spans:
            key = (hi, s)
            if key not in con:
                continue
            eff, t, agree, n, verdict = con[key]
            stem = f"{tag}{STEP[(lo, hi)]}{WORD.get(s, s)}"
            rows.append((stem, f"{eff:+.4f}"))
            rows.append((stem + "V", V.get(verdict, verdict)))
    return rows


def _levels(sec, metric, tag, spans=("8", "16", "24")):
    lv = survey(LOG, sec, metric, quiet=True)
    if not lv:
        return []
    order = survey(LOG, sec, metric, quiet=True)
    axis = None
    rows = []
    # `survey` without a reference returns {arm: [levels]}; the sweep order is the battery's.
    axis = ["8", "12", "16", "24"]
    for arm in RUNGS:
        if arm not in order:
            continue
        for s in spans:
            if s not in axis:
                continue
            rows.append((f"{tag}{arm[0].upper()}{arm[1:]}{WORD.get(s, s)}",
                         f"{order[arm][axis.index(s)]:.4f}"))
    return rows


def main() -> None:
    out: list[tuple[str, str]] = []

    # The whole-ladder gap, quoted ONCE, at the span where the blind console has collapsed. This is
    # the number that makes the section worth reading and it is also the number that, repeated in
    # every row of a table, would make each later rung look like it delivered what the first did.
    srv = survey(LOG, V1, "served_per_step", quiet=True)
    if srv:
        i24 = 3
        blind, best = srv["blindUnbound"][i24], srv["admits"][i24]
        out += [("LdCollapseBlind", f"{blind:.4f}"), ("LdCollapseBest", f"{best:.4f}"),
                ("LdCollapseRatio", f"{best / blind:.0f}")]

    # V1: the uniform fleet. The registered prediction is that the free bound is equivalent to the
    # deadline field, and that the order adds nothing because there is nothing to order.
    out += _adjacent(V1, "success", "LdU")
    out += _adjacent(V1, "served_per_step", "LdUSrv")
    out += _levels(V1, "success", "LdUSucc")
    out += _levels(V1, "busy_dead", "LdUDead")

    # Is the third rung byte-identical to the second on a uniform fleet? Structural if so: all
    # deadlines are equal, so earliest-deadline-first degenerates to first-come-first-served. Stated
    # as a measured fact rather than asserted, because it is the reason V2 exists.
    same = 0
    tot = 0
    for m in ("success", "served_per_step", "starved_frac", "abandoned_per_step", "busy_dead",
              "answer_rate_v"):
        lv = survey(LOG, V1, m, quiet=True)
        if not lv or "admits" not in lv or "admitsEdf" not in lv:
            continue
        for a, b in zip(lv["admits"], lv["admitsEdf"]):
            tot += 1
            same += int(a == b)
    if tot:
        out += [("LdUEdfSame", str(same)), ("LdUEdfCells", str(tot))]

    # V2: the two-point fleet, where the pilot says the rungs come apart.
    out += _adjacent(V2, "success", "LdM")
    out += _adjacent(V2, "served_per_step", "LdMSrv")
    out += _adjacent(V2, "starved_frac", "LdMStarve")
    out += _adjacent(V2, "answer_rate_v", "LdMRate")
    out += _levels(V2, "starved_frac", "LdMStarveL")

    # The section's own result, in the two numbers that carry it. On a heterogeneous fleet the
    # deadline field read ONCE is a throughput instrument that makes exclusion worse, and the same
    # field read a SECOND time, to order rather than to refuse, is an exclusion instrument that adds
    # no throughput. Same field, same cost to field, opposite in what they fix. The ratio is quoted
    # because the absolute numbers understate it: a requirement that says "use request deadlines"
    # buys whichever of the two the vendor implements.
    st = survey(LOG, V2, "starved_frac", quiet=True)
    if st and "admits" in st and "admitsEdf" in st:
        i24 = 3
        a, e = st["admits"][i24], st["admitsEdf"][i24]
        out += [("LdMExclField", f"{a:.4f}"), ("LdMExclOrder", f"{e:.4f}"),
                ("LdMExclRatio", f"{a / e:.0f}" if e else "n/a"),
                ("LdMExclBound", f"{st['boundOne'][i24]:.4f}")]

    # V3: heterogeneity as the sweep, which is where the threshold lives.
    het = survey(LOG, V3, "served_per_step", quiet=True)
    if het:
        axis = ["0", "3", "6", "9", "12", "18"]
        for arm in ("blindUnbound", "boundTwo", "admits"):
            if arm not in het:
                continue
            for j, lvl in enumerate(axis):
                if j < len(het[arm]):
                    out.append((f"LdH{arm[0].upper()}{arm[1:]}S{lvl}", f"{het[arm][j]:.4f}"))

    seen, rows = set(), []
    for k, v in out:
        if k not in seen:
            seen.add(k)
            rows.append((k, v))
    OUT.write_text("% generated by tools/make_ladder_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in rows))
    for k, v in rows:
        print(f"  {k:24s} {v}")
    print(f"\n{len(rows)} macros -> {OUT}")


if __name__ == "__main__":
    main()
