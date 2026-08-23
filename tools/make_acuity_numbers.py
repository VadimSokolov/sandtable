"""CR-56: what triage is worth to an operator who is not an oracle, and how to tell it is triage.

`admit_foresight` gives the console the exact service time before it commits. No human has that, so
the number it produces is a CEILING on what any real triage is worth and must be labelled as one.
`admit_acuity` is the same capability as a probability: the console recognises a hard request with
probability p and treats it as average otherwise, with the same Bayes rule either way. It is
bit-identical to the old switch at p = 1 and to the deadline-field console at p = 0.

The section rests on three measurements and one instrument.

    the value is LINEAR in p, so partial skill is worth a proportional amount and there is no
    threshold below which training is wasted;
    it costs the console NOTHING, since occupancy is equivalent across every acuity while delivered
    service rises by two thirds;
    the mechanism is length selection, and the instrument that proves it is length selection rather
    than admission rate is that every information-free console works at the population mean.

    st-acuity-9449506.out   A1 (acuity), A2 (the mu*cv scaling), A3 (the counter), A4 (the quantile)
    st-worked-9449525.out   W1 (what each console works against what it serves)
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_MPE, rate_floor  # noqa: E402
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
ACU, WRK = "st-acuity-9449506.out", "st-worked-9449525.out"
A1 = "A1 acuity, five points at cv 0.5"
W1 = "W1 what each console works, against what it serves"
SPANS = ["8", "12", "16"]
POP = 1.0 / 0.15                      # population mean service, steps


def main() -> None:
    out: list[tuple[str, str]] = []
    i16 = SPANS.index("16")

    # --- the acuity curve, at the published operating point -------------------------------------
    srv = survey(ACU, A1, "served_per_step", quiet=True)
    ps = ["p00", "p25", "p50", "p75", "p100"]
    lv = [srv[p][i16] for p in ps]
    out += [(f"Ac{n}", f"{v:.4f}") for n, v in
            zip(("Zero", "Quarter", "Half", "ThreeQ", "Full"), lv)]
    out.append(("AcGain", f"{lv[-1] - lv[0]:+.4f}"))
    out.append(("AcGainPct", f"{100 * (lv[-1] / lv[0] - 1):.0f}"))
    # Linearity: the largest departure from the chord, against the floor that decides materiality.
    chord = [lv[0] + (lv[-1] - lv[0]) * k / 4 for k in range(5)]
    out.append(("AcLinMax", f"{max(abs(a - b) for a, b in zip(lv, chord)):.4f}"))
    out.append(("AcFloor", f"{rate_floor():.4f}"))
    # A quarter of the capability, which is the sponsor's actual question.
    out.append(("AcQuarterGain", f"{lv[1] - lv[0]:+.4f}"))

    # --- what it costs the console, which is nothing --------------------------------------------
    busy = survey(ACU, A1, "busy_total", quiet=True)
    gated = survey(ACU, A1, "busy_total", ref="p00", quiet=True)
    out.append(("AcBusyZero", f"{busy['p00'][i16]:.4f}"))
    out.append(("AcBusyFull", f"{busy['p100'][i16]:.4f}"))
    out.append(("AcBusyT", f"{abs(gated[('p100', '16')][1]):.2f}"))
    srvg = survey(ACU, A1, "served_per_step", ref="p00", quiet=True)
    out.append(("AcSrvT", f"{srvg[('p100', '16')][1]:.0f}"))

    # --- the instrument: only a console that can see length selects on it -----------------------
    wk = survey(WRK, W1, "svc_worked_mean", quiet=True)
    sv = survey(WRK, W1, "svc_serviced_mean", quiet=True)
    free = ["cap", "coin", "mean", "quant"]
    vals = [wk[a][i16] for a in free]
    out += [("AcPop", f"{POP:.3f}"),
            ("AcFreeLo", f"{min(vals):.4f}"), ("AcFreeHi", f"{max(vals):.4f}"),
            ("AcFreeSpread", f"{max(vals) - min(vals):.4f}"),
            ("AcWorkFore", f"{wk['fore'][i16]:.4f}"), ("AcWorkHalf", f"{wk['half'][i16]:.4f}"),
            ("AcWorkMean", f"{wk['mean'][i16]:.4f}"), ("AcServeMean", f"{sv['mean'][i16]:.4f}"),
            ("AcServeFore", f"{sv['fore'][i16]:.4f}"),
            ("AcSelectGap", f"{POP - wk['fore'][i16]:.4f}")]

    # --- the counter against triage, which is where the published direction was backwards -------
    # A3 puts the counter and the deadline test in one job so the two levers can be read alone, in
    # combination, and against the triaging console. The registered claim was that the counter
    # FORECLOSES most of triage rather than substituting for it, which is worth checking because a
    # program office asked to buy both would naturally assume they add.
    A3 = "A3 the counter alone, against the counter plus a deadline test"
    a3 = survey(ACU, A3, "served_per_step", quiet=True)
    a3c = survey(ACU, A3, "served_per_step", ref="admf", quiet=True)
    i16 = 2
    out += [("AcBoundAlone", f"{a3['bound'][i16]:.4f}"),
            ("AcDeadlineAlone", f"{a3['adm'][i16]:.4f}"),
            ("AcBoundPlusTriage", f"{a3['boundadmf'][i16]:.4f}"),
            ("AcTriageAlone", f"{a3['admf'][i16]:.4f}"),
            # The counter is worth this much to a console that CANNOT triage ...
            ("AcBoundHelps", f"{a3['bound'][i16] - a3['adm'][i16]:+.4f}"),
            # ... and this much to one that can. It changes sign.
            ("AcBoundHurts", f"{a3c[('boundadmf', '16')][0]:+.4f}"),
            ("AcBoundHurtsT", f"{abs(a3c[('boundadmf', '16')][1]):.0f}"),
            # And the bit-identity check: foresight is inert on a console with no queue to triage.
            ("AcInertGap", f"{abs(a3['boundf'][i16] - a3['bound'][i16]):.4f}")]

    gen = ROOT / "report" / "gen" / "acuity_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {gen} with {len(out)} macros")


if __name__ == "__main__":
    main()
