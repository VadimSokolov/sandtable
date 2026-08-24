"""CR-65: the repair removes all of the named waste and reclaims none of the loss it was named for.

A blind console works requests whose asker already gave up and asked again. `stale_check = "before"`
makes it read `req_seq`, a counter it already keeps, and skip them. The repair is free in
information and free in time and it removes ONE HUNDRED PERCENT of the stale clock. It is also worth
at most 8.4 percent of what refusing the work is worth, and at twenty-four assets it is worth
exactly nothing, because the dead clock is conserved: the console goes on being busy producing no
answer, and merely stops producing no answer on superseded requests.

Two guards govern the prose this file feeds.

The first is that `busy_stale` CANNOT be used to rank the repairs. `stale_check = "before"` is
defined as never working a stale request, so its `busy_stale` is zero by entailment rather than by
measurement, and the bounded and admitting consoles reach the same zero by a second route. The three
arms are byte-identical in every block at every span. Any macro this file emits from `busy_stale` is
therefore a LEVEL of the reference arm or a statement about the collapse itself, never a contrast
used to prefer one repair over another. `GhIdentical` records the collapse so the manuscript can
state it as a measured fact.

The second is that the honest denominator for "what is this repair worth" is what the ALTERNATIVE
repair buys, not what the waste was. Every share macro here divides by the gain of `admits`, so a
reader is never shown a fraction whose denominator is the thing the treatment removed by definition.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ar_survey import survey                                    # noqa: E402

ROOT = HERE.parent
LOG = str(ROOT / "report" / "data" / "queue" / "st-ghost-9459739.out")
OUT = ROOT / "report" / "gen" / "ghost_numbers.tex"

SPANS = ("6", "8", "12", "16", "24")
WORD = {"6": "Six", "8": "Eight", "12": "Twelve", "16": "Sixteen", "24": "TwentyFour"}
HOLD = {"0.25": "Quarter", "0.5": "Half", "1.0": "One", "2.0": "Two",
        "4.0": "Four", "8.0": "Eight", "16.0": "Sixteen"}
V = {"GATE up": "gates up", "GATE down": "gates down",
     "equivalent": "equivalent", "inconclusive": "inconclusive"}


def _levels(sec: str, metric: str) -> dict[tuple[str, str], float]:
    """Per-arm, per-sweep-point means straight from the log, which `survey` does not expose."""
    out: dict[tuple[str, str], float] = {}
    cur = None
    for ln in open(LOG):
        m = re.match(r"### (U\d) .*\((\w+)\)", ln)
        if m:
            cur = (m.group(1), m.group(2))
            continue
        m = re.match(r"AR_ROW arm=(\S+) \w+=(\S+) mean=(\S+)", ln)
        if m and cur == (sec, metric):
            out[(m.group(1), m.group(2))] = float(m.group(3))
    return out


def _identical(sec: str, metric: str, arms: tuple[str, ...], pts: tuple[str, ...]) -> bool:
    """Are these arms byte-identical in every block at every sweep point? Defect 19's evidence."""
    vec: dict[tuple[str, str], list[float]] = {}
    cur = None
    for ln in open(LOG):
        m = re.match(r"### (U\d) .*\((\w+)\)", ln)
        if m:
            cur = (m.group(1), m.group(2))
            continue
        m = re.match(r"AR_ROW arm=(\S+) \w+=(\S+) mean=\S+ vals=(\S+)", ln)
        if m and cur == (sec, metric):
            vec[(m.group(1), m.group(2))] = [float(x) for x in m.group(3).split(",")]
    if not all((a, p) in vec for a in arms for p in pts):
        return False
    return all(vec[(arms[0], p)] == vec[(a, p)] for a in arms[1:] for p in pts)


def main() -> None:
    out: list[tuple[str, str]] = []

    # U1. The share table. The denominator is what the ADMITTING console buys, never what the waste
    # was, because a fraction of the removed waste is a fraction of a definition.
    srv = _levels("U1", "served_per_step")
    dead = _levels("U1", "busy_dead")
    shares: dict[str, float] = {}
    for s in SPANS:
        w, d, a = srv[("worksGhost", s)], srv[("dropsGhost", s)], srv[("admits", s)]
        dg, rg = d - w, a - w
        shares[s] = 100.0 * dg / rg if rg > 1e-9 else 0.0
        out += [(f"GhWorks{WORD[s]}", f"{w:.4f}"),
                (f"GhDrops{WORD[s]}", f"{d:.4f}"),
                (f"GhAdmits{WORD[s]}", f"{a:.4f}"),
                (f"GhDropGain{WORD[s]}", f"{dg:+.4f}"),
                (f"GhRefuseGain{WORD[s]}", f"{rg:+.4f}"),
                (f"GhShare{WORD[s]}", f"{shares[s]:.1f}"),
                (f"GhDead{WORD[s]}", f"{dead[('worksGhost', s)]:.4f}"),
                (f"GhDeadDrops{WORD[s]}", f"{dead[('dropsGhost', s)]:.4f}")]

    # The window. The free repair is worth nothing where there are no ghosts, peaks in the middle,
    # and decays to zero under saturation. An interior optimum is the whole operational point.
    peak = max(SPANS, key=lambda s: shares[s])
    out += [("GhPeakSpan", WORD[peak].lower()), ("GhPeakSpanNum", peak),
            ("GhPeakShare", f"{shares[peak]:.1f}"),
            ("GhLastShare", f"{shares['24']:.1f}")]

    # The conservation, which is the registered prediction and the reason the repair buys nothing.
    st = survey(LOG, "U1", "busy_stale", ref="worksGhost", quiet=True)
    la = survey(LOG, "U1", "busy_late", ref="worksGhost", quiet=True)
    for s in ("16", "24"):
        if st.get(("dropsGhost", s)) and la.get(("dropsGhost", s)):
            out += [(f"GhStale{WORD[s]}", f"{st[('dropsGhost', s)][0]:+.4f}"),
                    (f"GhLate{WORD[s]}", f"{la[('dropsGhost', s)][0]:+.4f}")]
    dd = survey(LOG, "U1", "busy_dead", ref="worksGhost", quiet=True)
    if dd.get(("dropsGhost", "24")):
        eff, t, _a, _n, verdict = dd[("dropsGhost", "24")]
        out += [("GhDeadReclaimed", f"{eff:+.4f}"), ("GhDeadReclaimedV", V.get(verdict, verdict))]

    # DEFECT 19. The three repairs read identically on the axis named after the waste, and separate
    # completely on the axis named after the loss. Both facts are emitted so the manuscript can put
    # them side by side rather than assert the collapse.
    out.append(("GhIdentical",
                "yes" if _identical("U1", "busy_stale",
                                    ("dropsGhost", "boundTwo", "admits"), SPANS) else "no"))
    if st.get(("dropsGhost", "24")) and st.get(("admits", "24")):
        out += [("GhStaleT", f"{abs(st[('dropsGhost', '24')][1]):.0f}"),
                ("GhStaleDrops", f"{st[('dropsGhost', '24')][0]:+.4f}"),
                ("GhStaleAdmits", f"{st[('admits', '24')][0]:+.4f}")]
    if dd.get(("dropsGhost", "24")) and dd.get(("admits", "24")):
        out += [("GhDeadDropsEff", f"{dd[('dropsGhost', '24')][0]:+.4f}"),
                ("GhDeadDropsV", V.get(dd[('dropsGhost', '24')][4], "")),
                ("GhDeadAdmitsEff", f"{dd[('admits', '24')][0]:+.4f}"),
                ("GhDeadAdmitsV", V.get(dd[('admits', '24')][4], ""))]
    out.append(("GhIdenticalOrder",
                "yes" if _identical("U2", "busy_stale",
                                    ("fcfsDrops", "rrDrops", "edfDrops"),
                                    ("8", "12", "16", "24")) else "no"))

    # U2. Dropping the ghost inverts the discipline ordering rather than shifting it, which decides
    # the question CR-64 left open: the inversion belongs to what a blind buffer CONTAINS.
    ar = survey(LOG, "U2", "answer_rate_v", ref="fcfsWorks", quiet=True)
    for arm, tag in (("rrWorks", "RrWorks"), ("edfWorks", "EdfWorks"),
                     ("fcfsDrops", "FcfsDrops"), ("rrDrops", "RrDrops"), ("edfDrops", "EdfDrops")):
        if ar.get((arm, "8")):
            out.append((f"Gh{tag}", f"{ar[(arm, '8')][0]:+.4f}"))
    if all(ar.get((a, "8")) for a in ("rrWorks", "edfWorks", "fcfsDrops", "rrDrops", "edfDrops")):
        works_best = max(("rrWorks", "edfWorks"), key=lambda a: ar[(a, "8")][0])
        drops_best = max(("fcfsDrops", "rrDrops", "edfDrops"), key=lambda a: ar[(a, "8")][0])
        out += [("GhWorksBest", {"rrWorks": "round robin", "edfWorks": "deadline order"}[works_best]),
                ("GhDropsBest", {"fcfsDrops": "arrival order", "rrDrops": "round robin",
                                 "edfDrops": "deadline order"}[drops_best]),
                ("GhInverts", "yes" if drops_best == "fcfsDrops" else "no")]

    # U3, both registered halves. At sixteen the ghost clock is flat across a sixty-four-fold
    # cadence range; at eight it is not, and delivered throughput has an interior maximum, so the
    # fleet-side repair has a size rather than a direction.
    c16 = _levels("U3", "busy_stale")
    holds = ("0.25", "0.5", "1.0", "2.0", "4.0", "8.0", "16.0")
    lv16 = [c16[("worksSixteen", h)] for h in holds]
    out += [("GhCadSixteenLo", f"{min(lv16):.4f}"), ("GhCadSixteenHi", f"{max(lv16):.4f}"),
            ("GhCadSixteenSpan", f"{max(lv16) - min(lv16):.4f}"),
            ("GhCadSixteenRel", f"{100.0 * (max(lv16) - min(lv16)) / max(lv16):.1f}")]
    p8 = _levels("U3", "served_per_step")
    lv8 = [p8[("worksEight", h)] for h in holds]
    s8 = [c16[("worksEight", h)] for h in holds]
    best = holds[lv8.index(max(lv8))]
    out += [("GhCadEightLo", f"{min(s8):.4f}"), ("GhCadEightHi", f"{max(s8):.4f}"),
            ("GhCadBestHold", best), ("GhCadBestHoldWord", HOLD[best].lower()),
            ("GhCadBestSrv", f"{max(lv8):.4f}"), ("GhCadFastSrv", f"{lv8[0]:.4f}"),
            ("GhCadSlowSrv", f"{lv8[-1]:.4f}"),
            ("GhCadInterior", "yes" if best not in (holds[0], holds[-1]) else "no")]

    # U4, the defect-14 guard. Where there is no ghost, no arm may separate on any reading.
    worst = 0.0
    for m in ("busy_dead", "served_per_step", "success"):
        c = survey(LOG, "U4", m, ref="worksGhost", quiet=True)
        for (arm, _p), v in (c or {}).items():
            if v[4] not in ("equivalent", "inconclusive"):
                worst = max(worst, abs(v[0]))
    out.append(("GhControlGates", "none" if worst == 0.0 else f"{worst:.4f}"))

    OUT.write_text("% generated by tools/make_ghost_numbers.py -- do not edit\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {OUT} with {len(out)} macros")


if __name__ == "__main__":
    main()
