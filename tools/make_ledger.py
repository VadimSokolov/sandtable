"""Build the registered-claim ledger table.

A reader who sees only surviving results cannot tell a pre-registered loop from a post-hoc one.
The only thing that separates them is the denominator: what was registered, what its falsifier
was, and what happened when it fired. This table is that denominator. It is written by hand from
`doc/autoresearch-conjectures.md` rather than parsed out of it, because the outcomes are
judgements and a parser would launder them into something that looks automatic.

    python3 tools/make_ledger.py

Writes `report/gen/tab_ledger.tex`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT  # noqa: E402

# claim, what its registered falsifier was, what happened
ROWS = [
    ("collapse span $n^\\star$",
     "goodput transition brackets a different span",
     "\\textsc{held}, at one, two and three consoles"),
    ("latency ceiling $\\ell^\\star$",
     "C4 and C5 separate at the default patience",
     "\\textsc{held}, and they separate when patience is raised"),
    ("bistable band",
     "no initial-condition gap at any span",
     "\\textsc{held} at the one span the band covers"),
    ("multiplicative interaction",
     "the predicted product form does not appear",
     "\\textsc{retracted} on its own falsifier; the shape it predicted survives"),
    ("a load rule with a knee",
     "smooth decline at every backoff span",
     "\\textsc{refuted} on both metrics; buried, and its revival clause closed"),
    ("adaptive backoff dominates",
     "no gain over the best fixed hold",
     "\\textsc{partial}: dominance died, the insurance claim ships"),
    ("span effect is a teaming effect",
     "supervisory falls as far as direct, or the mediator is flat",
     "\\textsc{held}: console \\atConsoleShare\\%, and the mediator is monotone"),
    ("notification becomes the majority share",
     "the share does not exceed one half once consumed",
     "\\textsc{refuted}; the unconsumed signal is negative, so the share was the wrong instrument"),
    ("a consumed refusal beats an ignored one",
     "no gain past collapse, or a cost below it",
     "\\textsc{held}: +0.268 goodput at twelve, and free at four"),
    ("the software lever is worth a fraction of a second console, and the fraction "
     "is the same on the clean metrics",
     "the one-console admit arm at or below one blind console on the absolute rate",
     "\\textsc{held}: 62\\% of a console on service, 77\\% on success, at eight assets"),
    ("the rate rule serves less and wins more, so staffing has two answers",
     "the rule winning or losing on both metrics at once",
     "\\textsc{held} at every span: below plain admit on service, above it on success"),
    ("the service the rate rule gives up was going to be wasted",
     "abandonment falling no faster than service, or the wasted share not falling",
     "\\textsc{held} on the first limb, 63 abandonments removed per unit of service at sixteen "
     "assets; the second limb is unreadable, its denominator moved 41\\%"),
    ("admission control is worth more, not less, as the link gets worse",
     "null or reversed on the absolute service rate",
     "\\textsc{held} on the clean metric at two spans where the ratio found one; "
     "the contaminated metric was hiding it"),
    ("burstiness helps an open reliance loop and harms a closed one",
     "the difference in differences loses its sign on the absolute rate",
     "\\textsc{held}: the LEVELS themselves flip sign, +0.004 open against -0.018 closed"),
    ("the crowding is vehicles colliding with each other, not with themselves",
     "the cross-vehicle contrast is null while the self-collision one carries it",
     "\\textsc{held}: self-collision is exactly zero, the round trip forbids it, "
     "and the cross-vehicle contrast gates in every cell"),
    ("a residual cohort survives jitter and grows with the dwell",
     "the no-retry control shows the same crowding as the jittered arm",
     "\\textsc{refuted}: it shows more, so nothing survives jitter and the residual "
     "was a gap between two calculated floors"),
    ("jitter helps by desynchronizing from the channel",
     "no Fano reduction in any mean-matched pair",
     "\\textsc{refuted} at the channel's dwell, \\textsc{confirmed} at the benched window: "
     "\\frGeRed{} of \\frGePairs{} pairs, and the refutation was the instrument"),
    ("wait priced by a self-authored knob",
     "(none: the design was the problem)",
     "\\textsc{cut} before running, on adversarial review"),
    ("jitter arms hold their mean",
     "(instrument, not a claim)",
     "\\textsc{repaired}: guard checked width, not the realized mean; guarded by a fixture that asserts the realized fleet mean, not the spread that was asked for"),
    ("contribution pointers all resolve",
     "(instrument, not a claim)",
     "\\textsc{repaired}: the checker truncated long lists; guarded by the pre-flight audit, which now resolves every pointer rather than the first few"),
    ("a scattered arrival stream reads one",
     "(instrument, not a claim)",
     "\\textsc{repaired}: a gated stream does not, and the null moves with dwell and rate; guarded by a null computed from the run's own dwell and rate rather than assumed to be one"),
    ("the stop-dead cliff has a closed form in route, speed and clock",
     "a separating hold more than 0.05 from the prediction, or one that moves with span",
     "\\textsc{refuted} on both, in three registrations declared final in advance; "
     "the threshold tracks span, so the console decides it"),
    ("the burstiness window belongs to the channel",
     "(instrument, not a claim)",
     "\\textsc{repaired}: benched against an injected cohort, it belongs to the mechanism; guarded by that bench, which any change to the statistic must still pass"),
    ("queue discipline moves nothing at the console",
     "(instrument: there is no queue to order)",
     "\\textsc{void-unreachable}: service is committed at ARRIVAL, so a discipline can only "
     "permute same-step arrivals, and where those are common the console is already saturated; guarded by a fixture pinning the reservation path bit-identical, so a real queue cannot be added without the difference showing"),
    ("the console's backlog has a closed-form size",
     "an argmax outside $\\{1,2\\}$ at the published point, or one that ignores patience",
     "\\textsc{held}: $k^{\\star}=2$ is the argmax at three spans, and the unbounded buffer it "
     "replaces delivers a factor of \\QcapUnboundedGainMed{} less"),
    ("the sizing rule is a point, and one may err on the safe side",
     "(retracted before publication, by generating the number over the whole grid)",
     "\\textsc{refuted}: the response is a plateau, not a peak, and which way to err reverses "
     "with load, because a cap in requests is a different delay at each arrival rate"),
    ("capping the request's age beats bounding the backlog",
     "a fixed counter matching the age cap under a moving link",
     "\\textsc{refuted}: it does, at every switching period, so the recommendation stays the "
     "cheapest rung and the message format does not change"),
    ("a queue rule derived for exponential service transfers to this console",
     "(instrument: the server does not draw its service times)",
     "\\textsc{repaired}: the console is $M/D/1$, so the correction term is the residual of a "
     "deterministic service and not the skew of an Erlang; guarded by a service-variability sweep that now runs the whole family from a metronome to an exponential server"),
    ("every closed form here was derived on a metronome",
     "an answer that leaves the plateau, or a lever that changes sign, at exponential service",
     "\\textsc{held}: the deterministic answer stays inside the variable server\'s plateau in "
     "\\QcapCvCells{} of \\QcapCvCells{} cells, and the lever loses value without approaching "
     "a sign change"),
]


def main() -> None:
    lines = ["\\begin{tabular}{@{}p{0.26\\textwidth}p{0.34\\textwidth}p{0.34\\textwidth}@{}}",
             "\\toprule",
             "registered claim & falsifier declared before the run & outcome \\\\",
             "\\midrule"]
    # Adversarial review's criterion, enforced here rather than remembered: a defect earns
    # its place in the table only if it can name the guard that makes its recurrence
    # impossible. A row that cannot is a war story, and war stories get cut.
    for r in ROWS:
        if "instrument" in r[1] and "guarded by" not in r[2]:
            raise SystemExit(f"instrument row names no guard, so it does not ship: {r[0]!r}")
    lines += [" & ".join(r) + " \\\\" for r in ROWS]
    lines += ["\\bottomrule", "\\end{tabular}"]
    out = ROOT / "report" / "gen" / "tab_ledger.tex"
    out.write_text("\n".join(lines) + "\n")
    # The prose says how many entries there are and how many failed. Counting them here keeps
    # those two sentences from drifting the next time a row is added.
    claims = [r for r in ROWS if "instrument" not in r[1]]
    failed = [r for r in claims if "refuted" in r[2] or "cut" in r[2] or "partial" in r[2]]
    counts = {"ldRows": len(ROWS), "ldClaims": len(claims), "ldInstr": len(ROWS) - len(claims),
              "ldFailed": len(failed), "ldHeld": len(claims) - len(failed)}
    (ROOT / "report" / "gen" / "ledger_counts.tex").write_text(
        "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in counts.items()))
    print(f"wrote {out} with {len(ROWS)} rows "
          f"({counts['ldClaims']} claims, {counts['ldFailed']} failed, {counts['ldInstr']} instruments)")


if __name__ == "__main__":
    main()
