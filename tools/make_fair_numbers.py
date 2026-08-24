"""CR-62: who gets served, not how many get served.

Every console result in this paper before this battery scored a rule by an average: answers per
step, mission success, utilization. An average cannot see exclusion, and the fleets these consoles
serve are not uniform. The metrics added for this conjecture split the same answers by the
requester's own deadline (`answer_step_ratio`), count the vehicles that got nothing at all
(`starved_frac`), and read the spread of per-vehicle service (`answer_rate_iqr`).

The finding is that queue discipline, a knob with no capability cost and no information cost, moves
all three by more than any capability lever in the paper, and that the field a console reads does
not determine the sign of what it does: a mean-budget console and a deadline-ordered console read
the identical deadline number and gate in opposite directions.

    st-regress2-9455454.out   P5 the discipline ladder; P6 the effort decomposition
    st-regress3-9456257.out   Q1 the quantile budget at matched information (the corrective run:
                              P6's quantile arms were bit-identical to FCFS because the budget is
                              only consulted when the console cannot see the job)
                              Q2 the effort decomposition where work can be wasted
                              Q3 whether ordering and capping compose
    st-maps-9449946.out       N1 the same starvation on three maps
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
P5LOG, Q_LOG, MLOG = "st-regress2-9455454.out", "st-regress3-9456257.out", "st-maps-9449946.out"
P5 = "P5 the discipline ladder, deadlines against sorting"
Q1 = "Q1 the quantile budget spends the deadline field regressively"
Q2 = "Q2 the effort decomposition where work can be wasted"
Q3 = "Q3 do the two levers compose"
MAPS = (("Band", "N1 the five levers on the band map"),
        ("Choke", "N1 the five levers on the chokepoint map"),
        ("Open", "N1 the five levers on the open map"))

# Short LaTeX-safe stems for the arms that get their own macros.
DISC = (("Edf", "edf"), ("Rand", "random"), ("Easy", "easyFirst"), ("Hard", "hardFirst"),
        ("Pat", "patientFirst"), ("Cap", "cap7"))
# The three inequality readings and the two aggregates, kept apart on purpose: the finding is that
# a discipline can move the first three hard while leaving the last two alone.
INEQ = (("Ratio", "answer_step_ratio"), ("Starv", "starved_frac"), ("Iqr", "answer_rate_iqr"))
AGG = (("Rate", "answer_rate_v"), ("Srv", "served_per_step"))


def _t(c, arm, pt):
    """(effect, t, verdict) for one contrast, or None when the pair is absent."""
    v = c.get((arm, pt))
    return None if v is None else (v[0], v[1], v[4])


# The rule table. Every row reads the SAME message and sees the same job; only the order of service
# differs. That is what makes it a different table from the knowledge ladder rather than another rung
# of it: the knowledge ladder prices what a console must be told, and this prices what it does with
# what it was already told.
ROWS = (("First come, first served", "fcfs"), ("Random order", "random"),
        ("Shortest job first", "easyFirst"), ("Longest job first", "hardFirst"),
        ("Most patient first", "patientFirst"), ("Earliest deadline first", "edf"),
        ("Service cap alone", "cap7"))
COLS = (("served_per_step", 3), ("answer_rate_v", 3), ("starved_frac", 3),
        ("answer_step_ratio", 2), ("answer_rate_iqr", 3), ("abandoned_per_step", 3))


def _table() -> None:
    lv = {m: survey(P5LOG, P5, m, quiet=True) for m, _ in COLS}
    c = survey(P5LOG, P5, "answer_step_ratio", ref="fcfs", quiet=True)
    lines = ["\\begin{tabular}{lrrrrrrl}", "\\toprule",
             "rule & served & answer & starved & patient: & service & abandoned & vs.\\ FCFS \\\\",
             " & /step & rate & frac. & impatient & IQR & /step & on ratio \\\\", "\\midrule"]
    for label, arm in ROWS:
        cells = [f"{lv[m][arm][1]:.{d}f}" for m, d in COLS]
        v = c.get((arm, "16"))
        verd = "reference" if arm == "fcfs" else (
            v[4].replace("GATE up", "worse").replace("GATE down", "better") if v else "")
        lines.append(" & ".join([label] + cells + [verd]) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (ROOT / "report" / "gen" / "tab_fair.tex").write_text("\n".join(lines) + "\n")
    print(f"wrote tab_fair.tex with {len(ROWS)} rows")


def main() -> None:
    out: list[tuple[str, str]] = []

    # --- P5: the ladder itself, every arm against FCFS at the saturated span. --------------------
    for mtag, metric in INEQ + AGG:
        c = survey(P5LOG, P5, metric, ref="fcfs", quiet=True)
        lv = survey(P5LOG, P5, metric, quiet=True)
        for atag, arm in DISC:
            r = _t(c, arm, "16")
            if r is None:
                continue
            e, t, verd = r
            out += [(f"Fr{atag}{mtag}", f"{e:+.4f}"), (f"Fr{atag}{mtag}T", f"{t:+.1f}"),
                    (f"Fr{atag}{mtag}V", verd.replace("GATE ", "gates ").replace("_", " "))]
        # Levels for the two arms the prose names in the open, so the reader sees the magnitude and
        # not only the difference. `quant80`/`quant95` are deliberately absent: in THIS battery every
        # arm could see the job, the budget is only consulted when it cannot, and the two quantile
        # arms came back bit-identical to FCFS. Section Q1 is the corrective run.
        for atag, arm in (("Fcfs", "fcfs"), ("Edf", "edf")):
            if arm in lv:
                out.append((f"FrLv{atag}{mtag}", f"{lv[arm][1]:.4f}"))

    # --- P5: the abandonment side of the same ladder, which is the price EDF does not pay. -------
    for mtag, metric in (("Aband", "abandoned_per_step"), ("Succ", "success")):
        c = survey(P5LOG, P5, metric, ref="fcfs", quiet=True)
        for atag, arm in (("Edf", "edf"), ("Cap", "cap7")):
            r = _t(c, arm, "16")
            if r:
                out += [(f"Fr{atag}{mtag}", f"{r[0]:+.4f}"), (f"Fr{atag}{mtag}V",
                        r[2].replace("GATE ", "gates "))]

    # --- Q1: identical information, opposite rule. ----------------------------------------------
    for mtag, metric in INEQ + AGG:
        c = survey(Q_LOG, Q1, metric, ref="meanBudget", quiet=True)
        lv = survey(Q_LOG, Q1, metric, quiet=True)
        for atag, arm in (("QEighty", "q80"), ("QNinetyfive", "q95"), ("EdfB", "edfBudget")):
            r = _t(c, arm, "16")
            if r is None:
                continue
            out += [(f"Fq{atag}{mtag}", f"{r[0]:+.4f}"), (f"Fq{atag}{mtag}T", f"{r[1]:+.1f}"),
                    (f"Fq{atag}{mtag}V", r[2].replace("GATE ", "gates "))]
        for atag, arm in (("Mean", "meanBudget"), ("QNinetyfive", "q95"), ("EdfB", "edfBudget")):
            if arm in lv:
                out.append((f"FqLv{atag}{mtag}", f"{lv[arm][2]:.4f}"))

    # --- Q2: where the extra work goes. The late bin is the mechanism claim: deadline order does
    # not merely reshuffle, it spends the console on jobs that were about to die.
    for mtag, metric in (("Late", "worked_late_per_step"), ("Lost", "worked_lost_per_step"),
                         ("Stale", "stale_per_step"), ("Work", "worked_per_step")):
        c = survey(Q_LOG, Q2, metric, ref="admitFcfs", quiet=True)
        r = _t(c, "admitEdf", "16")
        if r:
            out += [(f"Fe{mtag}", f"{r[0]:+.4f}"), (f"Fe{mtag}T", f"{r[1]:+.1f}"),
                    (f"Fe{mtag}V", r[2].replace("GATE ", "gates "))]

    # --- Q3: do the two levers compose? Each direction of the 2x2, at both spans. ----------------
    for mtag, metric in (("Ratio", "answer_step_ratio"), ("Rate", "answer_rate_v"),
                         ("Srv", "served_per_step"), ("Aband", "abandoned_per_step")):
        add_edf = survey(Q_LOG, Q3, metric, ref="cap7", quiet=True)     # EDF on top of a cap
        add_cap = survey(Q_LOG, Q3, metric, ref="edf", quiet=True)      # a cap on top of EDF
        for stag, pt in (("Coll", "8"), ("Full", "16")):
            for dtag, c in (("AddEdf", add_edf), ("AddCap", add_cap)):
                r = _t(c, "edfCap7", pt)
                if r:
                    out += [(f"Fc{dtag}{mtag}{stag}", f"{r[0]:+.4f}"),
                            (f"Fc{dtag}{mtag}{stag}V", r[2].replace("GATE ", "gates "))]

    # --- maps: the null that made the exclusion metric look inert was a configuration, not a fact
    # about fleets. On a UNIFORM fleet a plain FIFO console with an unbounded backlog excludes most
    # of it, and the number replicates to three decimals on three maps.
    starv, back = {}, {}
    for tag, sec in MAPS:
        s = survey(MLOG, sec, "starved_frac", quiet=True)
        b = survey(MLOG, sec, "backlog_mean", quiet=True)
        starv[tag], back[tag] = s, b
        out.append((f"Fm{tag}Fifo", f"{s['fifo'][4]:.4f}"))
    out += [("FmSpread", f"{max(v['fifo'][4] for v in starv.values()) - min(v['fifo'][4] for v in starv.values()):.4f}")]
    for atag, arm in (("Fifo", "fifo"), ("Lifo", "lifo"), ("Rand", "rand"), ("Admit", "admit")):
        out += [(f"Fm{atag}Starv", f"{starv['Band'][arm][4]:.4f}"),
                (f"Fm{atag}Back", f"{back['Band'][arm][4]:.1f}")]

    # How much of the deadline order's repair is available WITHOUT the semantic field. This is the
    # question the knowledge ladder above asks, applied to the rule axis, and the answer is most of
    # it: the expensive rung buys the last increment and the aggregate improvement, not the bulk of
    # the fairness gain. Reported as a fraction of the deadline order's own movement so the three
    # readings, which have different units, can be put on one line.
    for mtag, metric in INEQ:
        lv = survey(P5LOG, P5, metric, quiet=True)
        base, best = lv["fcfs"][1], lv["edf"][1]
        span = base - best
        for atag, arm in (("Rand", "random"), ("Easy", "easyFirst"), ("Cap", "cap7")):
            frac = (base - lv[arm][1]) / span if abs(span) > 1e-12 else float("nan")
            out.append((f"Fx{atag}{mtag}", f"{100 * frac:.0f}"))

    _table()

    dst = ROOT / "report" / "gen" / "fair_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:22s} {v}")


if __name__ == "__main__":
    main()
