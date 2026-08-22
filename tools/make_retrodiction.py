"""Build the external-check table: what the closed forms say against what other people published.

The retrodictions were scattered across the validation and attribution sections, which made a
reader count them by hand and made it easy to read a sign agreement as if it were a numerical one.
This puts them in one place with the STATUS column doing the work, so the two kinds cannot be
confused. Values come from `make_provenance.py`'s macros rather than being retyped.

    python3 tools/make_retrodiction.py

Writes `report/gen/tab_retrodiction.tex`.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT  # noqa: E402


def macros() -> dict[str, str]:
    """Read the already-generated macro files, so a number can only appear here if some other
    script has already traced it to a run or a scenario file."""
    out = {}
    for f in (ROOT / "report" / "gen").glob("*.tex"):
        for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", f.read_text()):
            out[m.group(1)] = m.group(2)
    return out


ROWS = [
    ("MAGIC 2010 field competition \\citep{olson2012magic}",
     "<<n>> robots on one task operator, reported unsaturated",
     "$n^\\star = <<nstar>>$ at their cadence",
     "\\textbf{numerical}: predicted operator sits at <<util>>\\% utilization, unsaturated as reported"),
    ("Giachetti et al.\\ 2012 \\citep{giachetti2012agent}",
     "capacity one robot; team size hurts under centralized authority, no effect decentralized",
     "the same interaction, with a threshold",
     "\\textbf{sign only}: a two-level design cannot separate serialization from congestion"),
    ("fan-out \\citep{olsen2004fanout,crandall2005validating}",
     "$\\mathrm{FO} = \\mathrm{NT}/\\mathrm{IT} + 1 = <<fanout>>$ here",
     "$n^\\star = <<nsc>>$ here",
     "\\textbf{compatible}: a duty-cycle bound and a stability bound, same order, not the same quantity"),
    ("wait time \\citep{cummings2008predicting}",
     "up to 67\\% of operator capacity lost to waiting",
     "waiting is the binding term above $n^\\star$",
     "\\textbf{qualitative}: agrees on which term binds, no value compared"),
]


def main() -> None:
    m = macros()
    sub = {"n": m["provMagicN"], "nstar": m["provMagicNstar"], "util": m["provMagicUtil"],
           "fanout": m["provFanout"], "nsc": m["provNstarClear"]}
    lines = ["\\begin{tabular}{@{}p{0.20\\textwidth}p{0.24\\textwidth}p{0.18\\textwidth}p{0.30\\textwidth}@{}}",
             "\\toprule",
             "external source & what it reports & what the closed forms say & status \\\\",
             "\\midrule"]
    for src, rep, says, status in ROWS:
        cells = []
        for c in (src, rep, says, status):
            cells.append(re.sub(r"<<(\w+)>>", lambda mm: sub[mm.group(1)], c))
        lines.append(" & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    out = ROOT / "report" / "gen" / "tab_retrodiction.tex"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
