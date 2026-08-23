"""Generate the CR-59 macros: the admission-rule requirements ladder, priced.

Reads:
    st-bias-9449800.out     H1 (offset x load), H2 (offset x spread), H3 (the information-free
                            null), H4 (pessimism with no per-job estimate), H5 (offset x cv),
                            H6 (the mission end)
    st-capped-9449936.out   M1 (the honest capped console, which retracted F6)

Every number here is a console quantity except the H6 block, which is the mission end and is the
only place the recommendation is asymmetric: the knob's downside reaches the mission and its upside
does not, so both are generated and the prose says which is which.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_survey import survey  # noqa: E402
from make_queue_numbers import ROOT  # noqa: E402

BIA = "st-bias-9449800.out"
H1 = "H1 the offset ladder against the load ladder"
H2 = "H2 spread against offset, at sixteen assets"
H3 = "H3 tightness without selectivity, at sixteen assets"
H4 = "H4 pessimism without a per-job estimate"
H5 = "H5 the offset ladder against service spread, at sixteen assets"
H6 = "H6 does the offset reach the mission"
NB = ["4", "6", "8", "12", "16"]
SG = ["1.0", "1.25", "1.6", "2.0", "2.5", "3.2", "4.0"]


def main() -> None:
    out: list[tuple[str, str]] = []
    srv = survey(BIA, H1, "served_per_step", quiet=True)
    con = survey(BIA, H1, "served_per_step", ref="b100", quiet=True)
    svc = survey(BIA, H1, "svc_serviced_mean", quiet=True)
    i16, i4 = NB.index("16"), NB.index("4")

    # The ladder itself, and the argmax row that carries F9.
    for arm, tag in (("b060", "Opt"), ("b100", "One"), ("b160", "Mid"),
                     ("b250", "Best"), ("b400", "Over")):
        out.append((f"Bi{tag}Sixteen", f"{srv[arm][i16]:.4f}"))
        out.append((f"Bi{tag}Four", f"{srv[arm][i4]:.4f}"))
    out += [("BiArgFour", "1.00"), ("BiArgSix", "1.00"), ("BiArgEight", "1.60"),
            ("BiArgTwelve", "2.00"), ("BiArgSixteen", "2.50"),
            ("BiGainSixteen", f"{con[('b250', '16')][0]:+.4f}"),
            ("BiGainTwelve", f"{con[('b160', '12')][0]:+.4f}"),
            # Optimism is free at an idle server and ruinous at a busy one: the shadow price of a
            # slot showing up on the cheap side of the ladder.
            ("BiOptGapFour", f"{con[('b060', '4')][0]:+.4f}"),
            ("BiOptGapSixteen", f"{con[('b060', '16')][0]:+.4f}"),
            ("BiSvcOne", f"{svc['b100'][i16]:.2f}"),
            ("BiSvcBest", f"{svc['b250'][i16]:.2f}")]

    # The requirements ladder, priced. Each rung against the console with no admission rule at all.
    q = survey(BIA, H4, "served_per_step", quiet=True)
    qc = survey(BIA, H4, "served_per_step", ref="q000", quiet=True)
    r = survey(BIA, H3, "served_per_step", quiet=True)
    rc = survey(BIA, H3, "served_per_step", ref="base", quiet=True)
    rab = survey(BIA, H3, "abandon_queue_frac", quiet=True)
    NB3 = ["8", "12", "16"]
    j = NB3.index("16")
    out += [("BiRungNone", f"{q['q000'][j]:.4f}"),
            # The random-refusal rung is quoted at its OWN best fraction, which is the weakest
            # fraction in the sweep; the matched-refusal-rate pair below uses r40 instead, because
            # that is the arm that turns away as much work as the selective console does.
            ("BiRungRandom", f"{max(r[a2][j] for a2 in ('r20', 'r40', 'r60', 'r80')):.4f}"),
            ("BiRungRandomGap", f"{rc[('r20', '16')][0]:+.4f}"),
            ("BiRungQuantile", f"{q['q90'][j]:.4f}"),
            ("BiRungQuantileGap", f"{qc[('q90', '16')][0]:+.4f}"),
            ("BiRungSeeing", f"{r['base'][j]:.4f}"),
            ("BiRungPriced", f"{r['bias'][j]:.4f}"),
            # The matched-refusal-rate comparison, which is what makes F8 about SELECTIVITY rather
            # than about how much work gets turned away.
            ("BiRefuseSel", f"{rab['bias'][j]:.4f}"),
            ("BiRefuseRand", f"{rab['r40'][j]:.4f}"),
            ("BiMatchedSel", f"{r['bias'][j]:.4f}"),
            ("BiMatchedRand", f"{r['r40'][j]:.4f}")]

    # Spread against offset: the peak VALUE collapses while the peak LOCATION barely moves, and the
    # instrument says why.
    sp = survey(BIA, H2, "served_per_step", quiet=True)
    ss = survey(BIA, H2, "svc_serviced_mean", quiet=True)
    out += [("BiPeakClean", f"{max(sp['s000']):.4f}"), ("BiPeakMid", f"{max(sp['s070']):.4f}"),
            ("BiPeakNoisy", f"{max(sp['s140']):.4f}"),
            ("BiSelClean", f"{ss['s000'][0]:.2f}"), ("BiSelCleanTop", f"{ss['s000'][-1]:.2f}"),
            ("BiSelNoisy", f"{ss['s140'][0]:.2f}"), ("BiSelNoisyTop", f"{ss['s140'][-1]:.2f}")]

    # The degenerate case, which is a step and not a curve.
    cv = survey(BIA, H5, "served_per_step", quiet=True)
    cs = survey(BIA, H5, "svc_serviced_mean", quiet=True)
    out += [("BiFlatOne", f"{cv['cv00'][0]:.4f}"), ("BiFlatBest", f"{cv['cv00'][2]:.4f}"),
            ("BiFlatOff", f"{cv['cv00'][3]:.4f}"), ("BiFlatSvc", f"{cs['cv00'][0]:.4f}"),
            # And the value of the knob scaling with spread while its location does not.
            ("BiCvLow", f"{cv['cv25'][2] - cv['cv25'][0]:+.4f}"),
            ("BiCvMid", f"{cv['cv50'][2] - cv['cv50'][0]:+.4f}"),
            ("BiCvHigh", f"{cv['cv100'][2] - cv['cv100'][0]:+.4f}")]

    # The mission end, where the recommendation turns asymmetric.
    ms = survey(BIA, H6, "success", ref="b100", quiet=True)
    out += [("BiMissBest", f"{ms[('b160', '8')][0]:+.4f}"),
            ("BiMissBestVerdict", ms[('b160', '8')][4]),
            ("BiMissHarm", f"{ms[('b400', '4')][0]:+.4f}")]

    gen = ROOT / "report" / "gen" / "bias_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {gen} with {len(out)} macros")


if __name__ == "__main__":
    main()
