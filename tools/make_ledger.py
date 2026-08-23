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
     "\\textsc{repaired}: guard checked width, not the realized mean"),
    ("contribution pointers all resolve",
     "(instrument, not a claim)",
     "\\textsc{repaired}: the checker truncated long lists"),
    ("a scattered arrival stream reads one",
     "(instrument, not a claim)",
     "\\textsc{repaired}: a gated stream does not, and the null moves with dwell and rate"),
    ("the stop-dead cliff has a closed form in route, speed and clock",
     "a separating hold more than 0.05 from the prediction, or one that moves with span",
     "\\textsc{refuted} on both, in three registrations declared final in advance; "
     "the threshold tracks span, so the console decides it"),
    ("the burstiness window belongs to the channel",
     "(instrument, not a claim)",
     "\\textsc{repaired}: benched against an injected cohort, it belongs to the mechanism"),
]


def main() -> None:
    lines = ["\\begin{tabular}{@{}p{0.26\\textwidth}p{0.34\\textwidth}p{0.34\\textwidth}@{}}",
             "\\toprule",
             "registered claim & falsifier declared before the run & outcome \\\\",
             "\\midrule"]
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
