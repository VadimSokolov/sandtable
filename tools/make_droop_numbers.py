"""CR-30: does a saturating operator's answer quality change any conclusion in this paper?

The model's operator answers at a fixed quality regardless of load, which is an oracle assumption
and the strongest one here. `q_droop` takes the quality of a serviced decision down toward the
autonomous baseline in proportion to the console's running utilization, which is the descending
limb of the utilization-performance relation. Zero is exactly the shipped model, so the sweep nests
it at its own baseline.

The registered claim is about ORDERINGS and not magnitudes, because a magnitude read off an
invented droop rate would be the self-authored-knob error that killed CR-28. Five shipped orderings
are checked at every droop level; any sign reversal makes the result it supports conditional on an
oracle operator, and the manuscript would have to say so next to that result.

Source: hopper/batteries/droop.sh, job 9446590.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-droop-9446590.out"
CHECKS = [("O1", "success", "admit", "blind", "AdmitSucc"),
          ("O1", "success", "refund", "blind", "RefundSucc"),
          ("O1", "operator_goodput", "admit", "blind", "AdmitGood"),
          ("O2", "success", "noretry", "rho04", "NoRetry"),
          ("O3", "success", "sup06", "dir06", "SupOverDir")]


def load(sec: str, metric: str) -> dict:
    out, cur = {}, False
    for line in (ROOT / "report" / "data" / "queue" / LOG).read_text().splitlines():
        if line.startswith("### "):
            cur = line.startswith(f"### {sec} ") and f"({metric})" in line
        elif cur and line.startswith("AR_ROW"):
            f = dict(p.split("=", 1) for p in line.split()[1:])
            key = next(v for k, v in f.items() if k not in ("arm", "mean", "vals"))
            out[(f["arm"], key)] = [float(v) for v in f["vals"].split(",")]
    return out


def main() -> None:
    m: dict[str, str] = {}
    reversals, checked = 0, 0
    for sec, metric, a, b, tag in CHECKS:
        d = load(sec, metric)
        if not d:
            continue
        levels = sorted({k[1] for k in d}, key=float)
        eff = []
        for L in levels:
            e, t, w, N = paired({"vals": d[(a, L)]}, {"vals": d[(b, L)]})
            eff.append(e)
            m[f"dr{tag}Blocks"] = str(min(int(m.get(f"dr{tag}Blocks", N)), w))
            m["drBlocks"] = str(N)
        checked += 1
        if len({e > 0 for e in eff}) > 1:
            reversals += 1
        # The two endpoints of the sweep, which is what the prose needs: shipped model and
        # the most degraded operator the knob can produce.
        m[f"dr{tag}Zero"] = f"{eff[0]:+.3f}"
        m[f"dr{tag}Full"] = f"{eff[-1]:+.3f}"
        # Shrinkage of the ordering from oracle to fully drooped, as a share of the oracle value.
        m[f"dr{tag}Shrink"] = f"{100 * (1 - eff[-1] / eff[0]):.0f}"
    m["drLevels"] = str(len(levels))
    m["drChecked"] = str(checked)
    m["drReversals"] = str(reversals)
    m["drVerdict"] = "none" if reversals == 0 else str(reversals)

    gen = ROOT / "report" / "gen" / "droop_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nOperator quality droop (source: tools/make_droop_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}: {checked} orderings, {len(levels)} droop levels, {reversals} reversals")


if __name__ == "__main__":
    main()
