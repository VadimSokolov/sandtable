"""Generate the attribution macros for the span-of-control result.

The centerpiece measures a span effect at a fixed defending force. Sweeping span that way changes
the force ratio as well as the console load, so the measured effect is not automatically a teaming
effect. This script reads the attribution battery, which holds the ratio fixed and sweeps the same
span under three control regimes, and produces the difference in differences and the decomposition
of it. It reads both `success` and `arrived_frac`, because the first is a threshold on the second
and a step in a threshold can be a step in the underlying fraction or a step across the cut.

    python3 tools/make_attrib_numbers.py

Writes `report/gen/attrib_numbers.tex` and appends a traceable block to `report/results/numbers.txt`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT, paired, row, rows  # noqa: E402

LOG = "st-attrib-9445987.out"
SPANS = (3, 6, 9, 12, 15)


def _series(rs, sec, prefix, held):
    """The five span rungs of one control regime. The two experiments name their arms
    differently: the held-ratio sweep encodes the span in the arm name, the fixed-defender
    sweep sweeps it, so the lookup differs by experiment and not by regime."""
    if held:
        return [row(rs, sec, f"{prefix}{n:02d}") for n in SPANS]
    return [row(rs, sec, prefix, str(n)) for n in SPANS]


def _did(fix_lo, fix_hi, held_lo, held_hi):
    """Difference in differences, paired blockwise. Both experiments share a seed schedule, so
    the four arms of a cell are the same missions under four treatments and the difference of
    differences is itself a paired quantity."""
    d = [(a - b) - (c - e) for a, b, c, e in
         zip(fix_hi["vals"], fix_lo["vals"], held_hi["vals"], held_lo["vals"], strict=True)]
    n = len(d)
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1)
    t = mean / ((var / n) ** 0.5) if var > 0 else float("inf")
    return mean, t, sum(1 for x in d if x * mean > 0), n


def _check_pairing(rs, held_sec, fix_sec) -> None:
    """The difference in differences is paired blockwise, which is only legitimate if the two
    experiments ran the same seed schedule. They must therefore COINCIDE at the pivot span, where
    holding the force ratio and fixing the defenders describe the same design, and differ away from
    it. Checked by value rather than assumed, because a paired t on unpaired blocks is not
    conservative: it would understate the variance and inflate every t in this file."""
    pivot = str(SPANS[1])
    for pre in ("dir", "ref", "sup"):
        a = row(rs, held_sec, f"{pre}{int(pivot):02d}")["vals"]
        b = row(rs, fix_sec, pre, pivot)["vals"]
        if a != b:
            sys.exit(f"pairing broken: {pre} at n={pivot} differs between the two designs, so the "
                     f"blockwise difference in differences is not paired")
    lo = str(SPANS[0])
    if row(rs, held_sec, f"{'dir'}{int(lo):02d}")["vals"] == row(rs, fix_sec, "dir", lo)["vals"]:
        sys.exit(f"the two designs are identical at n={lo}; the contrast is empty")


def main() -> None:
    rs = rows(LOG)
    m: dict[str, str] = {}
    for metric, tag in (("success", ""), ("arrived_frac", "Arr")):
        held_sec = f"T1 held force ratio, three control regimes ({metric})"
        fix_sec = f"T2 defenders fixed at four, the same three regimes ({metric})"
        _check_pairing(rs, held_sec, fix_sec)
        steps = {}
        for reg, pre in (("Dir", "dir"), ("Ref", "ref"), ("Sup", "sup")):
            held = _series(rs, held_sec, pre, True)
            fix = _series(rs, fix_sec, pre, False)
            hm, ht, _, hn = paired(held[-1], held[0])
            fm, ft, _, _ = paired(fix[-1], fix[0])
            steps[reg] = hm
            m[f"at{tag}Held{reg}"] = f"{hm:+.3f}"
            m[f"at{tag}Held{reg}T"] = f"{ht:.1f}"
            m[f"at{tag}Fix{reg}"] = f"{fm:+.3f}"
            m[f"at{tag}Fix{reg}T"] = f"{ft:.1f}"
            if reg == "Dir":
                dm, dt, dw, dn = _did(fix[0], fix[-1], held[0], held[-1])
                m[f"at{tag}Did"] = f"{dm:+.3f}"
                m[f"at{tag}DidT"] = f"{dt:.1f}"
                m[f"at{tag}DidBlocks"] = str(dw)
                m[f"at{tag}DidN"] = str(dn)
                m[f"at{tag}Blocks"] = str(hn)
                m[f"at{tag}Mono"] = ("yes" if all(a["mean"] > b["mean"]
                                                  for a, b in zip(held, held[1:])) else "no")
        # Supervisory removes the console entirely, so the share of the collapse it does NOT
        # recover is the share the console cannot be responsible for.
        m[f"at{tag}ConsoleShare"] = f"{100 * (1 - steps['Sup'] / steps['Dir']):.0f}"
        m[f"at{tag}ScenarioShare"] = f"{100 * steps['Sup'] / steps['Dir']:.0f}"
        m[f"at{tag}RefundShare"] = f"{100 * (1 - steps['Ref'] / steps['Dir']):.0f}"
        for reg, pre in (("Dir", "dir"), ("Ref", "ref"), ("Sup", "sup")):
            held = _series(rs, held_sec, pre, True)
            m[f"at{tag}{reg}Lo"] = f"{held[0]['mean']:.3f}"
            m[f"at{tag}{reg}Hi"] = f"{held[-1]['mean']:.3f}"
    m["atSpanLo"], m["atSpanHi"] = str(SPANS[0]), str(SPANS[-1])

    gen = ROOT / "report" / "gen" / "attrib_numbers.tex"
    gen.write_text("% AUTO-GENERATED by tools/make_attrib_numbers.py -- do not edit.\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in m.items()))
    res = ROOT / "report" / "results" / "numbers.txt"
    body = res.read_text()
    tag = ("\n\nSpan attribution numbers "
           f"(source: tools/make_attrib_numbers.py over report/data/queue/{LOG})\n")
    body = body.split(tag)[0] + tag + "=" * 78 + "\n"
    body += "".join(f"\\{k} = {v}\n" for k, v in m.items())
    res.write_text(body)
    print(f"wrote {gen} and appended {len(m)} numbers to {res}")


if __name__ == "__main__":
    main()
