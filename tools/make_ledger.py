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
    ("wait priced by a self-authored knob",
     "(none: the design was the problem)",
     "\\textsc{cut} before running, on adversarial review"),
    ("jitter arms hold their mean",
     "(instrument, not a claim)",
     "\\textsc{repaired}: guard checked width, not the realized mean"),
    ("contribution pointers all resolve",
     "(instrument, not a claim)",
     "\\textsc{repaired}: the checker truncated long lists"),
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
    print(f"wrote {out} with {len(ROWS)} rows")


if __name__ == "__main__":
    main()
