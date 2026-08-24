"""Generate the CR-59 macros: the admission-rule requirements ladder, priced.

Reads:
    st-bias-9449800.out     H1 (offset x load), H2 (offset x spread), H3 (the information-free
                            null), H4 (pessimism with no per-job estimate), H5 (offset x cv),
                            H6 (the mission end)
    st-capped-9449936.out   M1 (the honest capped console, which retracted F6), M2 (the finer
                            offset grid, which retracted F9 as worded), M3 (the degenerate case),
                            M4 (who pays for the throughput)

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
CAP = "st-capped-9449936.out"
M1 = "M1 the capped console against the inflated one"
M2 = "M2 where the price turns, against the collapse span"
M3 = "M3 the degenerate case, no spread to price"
M4 = "M4 who pays for the throughput"
NB = ["4", "6", "8", "12", "16"]
SG = ["1.0", "1.25", "1.6", "2.0", "2.5", "3.2", "4.0"]


def _did(log: str, section: str, metric: str):
    """Paired difference-in-differences on a ladder's corners, gated like any other contrast.

    A tilt is what "the optimum moves with load" actually asserts, and it is testable directly:
    the high-minus-low offset gap at a high span, minus the same gap at a low span, computed
    within each block so the pairing survives. Reading a moving argmax instead infers the tilt
    from a peak location the data cannot resolve.
    """
    import numpy as np
    import re as _re
    rows, sec = {}, None
    for ln in (ROOT / "report" / "data" / "queue" / log).read_text().splitlines():
        if ln.startswith("### "):
            sec = ln[4:]
            continue
        m = _re.match(r"AR_ROW arm=(\S+) n_blue=(\S+) mean=\S+ vals=(\S+)", ln)
        if m and sec and sec.startswith(section) and metric in sec:
            rows[(m.group(1), m.group(2))] = np.array([float(x) for x in m.group(3).split(",")])

    def contrast(a_hi, a_lo, n_hi, n_lo):
        d = ((rows[(a_hi, n_hi)] - rows[(a_lo, n_hi)])
             - (rows[(a_hi, n_lo)] - rows[(a_lo, n_lo)]))
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
        return d.mean(), t, int((np.sign(d) == np.sign(d.mean())).sum()), len(d)

    return contrast


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

    # ------------------------------------------------------------------ the capped control.
    # M1. The honest console recovers the inflated one, which is what killed F6. Reported as an
    # equivalence, so the one-sided statistic is the number that carries it, not the effect.
    from ar_gate import margin, tost  # noqa: E402
    cp = survey(CAP, M1, "served_per_step", quiet=True)
    cc = survey(CAP, M1, "served_per_step", ref="bias250", quiet=True)
    cs = survey(CAP, M1, "svc_serviced_mean", quiet=True)
    ca = survey(CAP, M1, "abandon_queue_frac", quiet=True)
    spans = ["8", "12", "16"]
    tst = []
    for n in spans:
        eff, t, k, nb, _ = cc[("cap7", n)]
        tst.append(tost(eff, t, nb, margin("served_per_step", cp["bias250"][spans.index(n)]))[1])
    out += [("CapEffOne", f"{cc[('cap7', '8')][0]:+.4f}"),
            ("CapEffTwo", f"{cc[('cap7', '12')][0]:+.4f}"),
            ("CapEffThree", f"{cc[('cap7', '16')][0]:+.4f}"),
            ("CapTostWeak", f"{min(tst):.2f}"),
            # The rider: matched throughput, different refusal and different job length.
            ("CapRefuseBias", f"{ca['bias250'][2]:.4f}"),
            ("CapRefuseHonest", f"{ca['cap7'][2]:.4f}"),
            ("CapSvcBias", f"{cs['bias250'][2]:.4f}"),
            ("CapSvcHonest", f"{cs['cap7'][2]:.4f}")]

    # M2. The finer grid that retracted F9 as worded: the argmax leaves unity at five assets, and
    # the gate does not separate any offset from unity below twelve.
    fs = survey(CAP, M2, "served_per_step", quiet=True)
    fc = survey(CAP, M2, "served_per_step", ref="b100", quiet=True)
    fn = ["4", "5", "6", "7", "8", "10", "12", "16"]
    arms = ["b080", "b090", "b100", "b110", "b125", "b160"]
    # NOT the argmax. On a ladder this flat near its peak the argmax is ill-conditioned: under a
    # truly flat response a monotone sequence across these spans arises by chance often enough
    # that "the optimum moves with load" is not a claim the data supports. Two conditioned
    # readings replace it: the TOLERANCE BAND (every offset within one rate floor of the best,
    # which is what a program office needs anyway) and a gated DIFFERENCE-IN-DIFFERENCES on the
    # ladder's corners, which tests the tilt directly instead of inferring it from a moving peak.
    from ar_gate import rate_floor  # noqa: E402
    fl = rate_floor()
    lab = {a: f"{float(a[1:]) / 100:.2f}" for a in arms}
    band = {}
    for i, n in enumerate(fn):
        best = max(fs[a][i] for a in arms)
        band[n] = [lab[a] for a in arms if fs[a][i] >= best - fl]
    did = _did(CAP, M2, "served_per_step")
    e_wide, t_wide, k_wide, nb = did("b160", "b080", "16", "4")
    e_ref, t_ref, _, _ = did("b160", "b100", "16", "4")
    out += [("CapBandLow", "{" + ", ".join(band["4"]) + "}"),
            ("CapBandLowWidth", str(len(band["4"]))),
            ("CapBandHigh", "{" + ", ".join(band["16"]) + "}"),
            ("CapBandHighWidth", str(len(band["16"]))),
            ("CapBandNarrows", next(n for n in fn if len(band[n]) <= 2)),
            ("CapTiltWide", f"{e_wide:+.4f}"), ("CapTiltWideT", f"{t_wide:.1f}"),
            ("CapTiltBlocks", f"{k_wide} of {nb}"),
            ("CapTiltRef", f"{e_ref:+.4f}"), ("CapTiltRefT", f"{t_ref:.1f}"),
            ("CapGateFirst", next(n for n in fn if fc[("b160", n)][4] == "GATE up")),
            ("CapFineTwelve", f"{fc[('b160', '12')][0]:+.4f}"),
            ("CapFineSixteen", f"{fc[('b160', '16')][0]:+.4f}")]

    # M3. The degenerate case. F11 held, and the step sits at unity exactly.
    dg = survey(CAP, M3, "served_per_step", quiet=True)
    db = ["0.8", "1.0", "1.1", "1.25", "1.6", "2.0", "2.5"]
    out += [("CapFlatBelow", f"{dg['cv000'][0]:.4f}"),
            ("CapFlatAt", f"{dg['cv000'][1]:.4f}"),
            ("CapFlatTop", f"{dg['cv000'][len(db) - 1]:.4f}"),
            ("CapFlatSpan", f"{max(dg['cv000'][1:]) - min(dg['cv000'][1:]):.4f}"),
            ("CapNearFlatSpan", f"{max(dg['cv010'][1:]) - min(dg['cv010'][1:]):.4f}")]

    # M4. Who pays. The throughput is bought with abandonment, and the exchange rate is the number
    # a sponsor should be shown. `starved_frac` is saturated at zero here (instrument defect 13),
    # so it is generated only to be reported as the metric that could not see this.
    ms4 = survey(CAP, M4, "served_per_step", quiet=True)
    ab4 = survey(CAP, M4, "abandoned_per_step", quiet=True)
    ar4 = survey(CAP, M4, "answer_rate_v", quiet=True)
    sv4 = survey(CAP, M4, "starved_frac", quiet=True)
    mc = survey(CAP, M4, "served_per_step", ref="plain", quiet=True)
    ac = survey(CAP, M4, "abandoned_per_step", ref="plain", quiet=True)
    rc = survey(CAP, M4, "answer_rate_v", ref="plain", quiet=True)
    j = spans.index("16")
    rate = lambda a, i: (ab4[a][i] - ab4["plain"][i]) / (ms4[a][i] - ms4["plain"][i])  # noqa: E731
    out += [("CapStarvedAll", f"{max(max(v) for v in sv4.values()):.4f}"),
            ("CapPayServed", f"{mc[('b160', '16')][0]:+.4f}"),
            ("CapPayServedT", f"{mc[('b160', '16')][1]:.1f}"),
            ("CapPayAband", f"{ac[('b160', '16')][0]:+.4f}"),
            ("CapPayAbandT", f"{ac[('b160', '16')][1]:.1f}"),
            ("CapPayRate", f"{rate('b160', j):.1f}"),
            ("CapPayRateBig", f"{rate('bias250'.replace('bias', 'b'), j):.1f}"),
            ("CapPayRateMid", f"{rate('b160', spans.index('12')):.1f}"),
            ("CapPayAnswer", f"{rc[('b160', '16')][0]:+.4f}"),
            ("CapPayAnswerVerdict", rc[("b160", "16")][4]),
            ("CapPayAnswerBig", f"{rc[('b250', '16')][0]:+.4f}"),
            ("CapDomServed", f"{mc[('cap5', '16')][0]:+.4f}"),
            ("CapDomAband", f"{ac[('cap5', '16')][0]:+.4f}")]

    gen = ROOT / "report" / "gen" / "bias_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {gen} with {len(out)} macros")


if __name__ == "__main__":
    main()
