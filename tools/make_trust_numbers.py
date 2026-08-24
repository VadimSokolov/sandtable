"""CR-61: verification as a signal-detection problem, not a dial.

Every earlier operator model in this paper spent operator time at a rate and charged for it. That
model cannot answer the question a program office actually asks, which is not "how often should the
operator check" but "how good does the operator have to BE at telling a wrong answer from a right
one before checking is worth anything." So the trust model was rebuilt as signal detection: the
operator sees a cue drawn from N(wrong * d', 1) and checks when the cue clears a criterion. The
check RATE names the criterion; `check_dprime` names the discriminability. Two knobs, and only one
of them is a capability.

The battery does four things. S6 confirms the instrument recovers the parameter it was given and
that the recovered d-prime does not move when only the criterion moves. S1 asks whether an operator
beats no operator at all. S3 locates the check rate against console load. S5 prices a wrong answer
three ways and finds that the optimal policy flips with the price, at fixed accuracy.

    st-trust-9450073.out   S1..S6
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import rate_floor  # noqa: E402
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = "st-trust-9450073.out"
S1 = "S1 does an operator beat no operator, and what carries the answer"
S2 = "S2 the threshold on what a waiting asset may do"
S3 = "S3 the optimal check rate against console load"
S4 = "S4 is the check rate scheduled by slack or by the channel"
S5 = "S5 three prices for a wrong answer, one grid"
S6 = "S6 discrimination against criterion, which is the ROC the gap asks for"
SPANS = ("4", "6", "8", "12", "16")
RATES = (("Zero", "r000"), ("Quarter", "r025"), ("Half", "r050"),
         ("ThreeQ", "r075"), ("One", "r100"))
FLOOR = rate_floor()


def _band(lv, i):
    """Arms within one rate floor of the best at sweep index i: the tolerance band, not the argmax.

    An argmax over a flat ladder is a coin flip dressed as a finding. The band is what the data can
    actually support, and its WIDTH is the honest statement of how sharply the optimum is located.
    """
    vals = {a: lv[a][i] for a in lv}
    top = max(vals.values())
    return [a for a in lv if vals[a] >= top - FLOOR]


def main() -> None:
    out: list[tuple[str, str]] = []

    # --- S6 first: an instrument check before any claim rests on the instrument. -----------------
    dp = survey(LOG, S6, "trust_dprime", quiet=True)
    cf = survey(LOG, S6, "check_frac", quiet=True)
    for tag, arm, nominal in (("Zero", "d00", "0.00"), ("Half", "d05", "0.50"),
                              ("One", "d10", "1.00"), ("Two", "d20", "2.00")):
        out += [(f"Td{tag}Set", nominal), (f"Td{tag}Got", f"{dp[arm][1]:.3f}")]
    # The criterion-invariance check: same discriminability, two very different check rates.
    out += [("TdLoGot", f"{dp['d10lo'][1]:.3f}"), ("TdHiGot", f"{dp['d10hi'][1]:.3f}"),
            ("TdLoFrac", f"{cf['d10lo'][1]:.3f}"), ("TdHiFrac", f"{cf['d10hi'][1]:.3f}"),
            ("TdCritSpread", f"{abs(dp['d10lo'][1] - dp['d10hi'][1]):.3f}"),
            ("TdFracSpread", f"{abs(cf['d10lo'][1] - cf['d10hi'][1]):.3f}")]
    hit, fa = survey(LOG, S6, "trust_hit_rate", quiet=True), survey(LOG, S6, "trust_fa_rate", quiet=True)
    out += [("TdOneHit", f"{hit['d10'][1]:.3f}"), ("TdOneFa", f"{fa['d10'][1]:.3f}"),
            ("TdTwoHit", f"{hit['d20'][1]:.3f}"), ("TdTwoFa", f"{fa['d20'][1]:.3f}")]

    # --- S1: does an operator beat no operator? The registered prediction was that a free check at
    # an idle console is free. It is not, and the falsification is the more useful result.
    for mtag, metric in (("Succ", "success"), ("Loss", "blue_loss_frac")):
        c = survey(LOG, S1, metric, ref="nop", quiet=True)
        for atag, arm in (("Never", "chk000"), ("Always", "chk100"),
                          ("FreeNever", "chk000free"), ("FreeAlways", "chk100free")):
            for stag, sp in (("Low", "4"), ("Full", "16")):
                r = c.get((arm, sp))
                if r:
                    out += [(f"To{atag}{mtag}{stag}", f"{r[0]:+.4f}"),
                            (f"To{atag}{mtag}{stag}V", r[4].replace("GATE ", "gates "))]
    gated_up = sum(1 for a in ("chk000", "chk100", "chk000free", "chk100free") for s in SPANS
                   if (v := survey(LOG, S1, "blue_loss_frac", ref="nop", quiet=True).get((a, s)))
                   and v[4] == "GATE up")
    out.append(("ToLossUpCells", f"{gated_up}"))

    # --- S3: the check rate against console load. Bands, then the two gated corners. -------------
    lv = survey(LOG, S3, "success", quiet=True)
    for stag, sp in zip(("Four", "Six", "Eight", "Twelve", "Sixteen"), SPANS):
        b = _band(lv, SPANS.index(sp))
        out += [(f"Tb{stag}Width", f"{len(b)}"),
                (f"Tb{stag}Best", max(lv, key=lambda a: lv[a][SPANS.index(sp)]).replace("r", "").lstrip("0") or "0")]
    c = survey(LOG, S3, "success", ref="r000", quiet=True)
    for stag, sp in (("Low", "4"), ("Coll", "8")):
        r = c.get(("r100", sp))
        if r:
            out += [(f"Tr{stag}", f"{r[0]:+.4f}"), (f"Tr{stag}T", f"{r[1]:+.1f}"),
                    (f"Tr{stag}V", r[4].replace("GATE ", "gates "))]
    out.append(("TrFloor", f"{FLOOR:.4f}"))

    # --- S5: the same accuracy, three prices, two policies. The channel where checking never pays
    # is the finding, because it is the channel where a program office would most expect it to.
    for ctag, lo, hi in (("Time", "timeR000", "timeR100"), ("Weak", "weakR000", "weakR100"),
                         ("Refl", "reflR000", "reflR100")):
        c = survey(LOG, S5, "success", ref=lo, quiet=True)
        for etag, err in (("Lo", "0.1"), ("Mid", "0.5"), ("Hi", "0.9")):
            r = c.get((hi, err))
            if r:
                out += [(f"Tp{ctag}{etag}", f"{r[0]:+.4f}"), (f"Tp{ctag}{etag}T", f"{r[1]:+.1f}"),
                        (f"Tp{ctag}{etag}V", r[4].replace("GATE ", "gates "))]
        # Where the sign turns over, reported as a bracket rather than a point: the grid has five
        # cells and cannot resolve a crossing finer than the gap between two of them.
        signs = [(e, c[(hi, e)][0]) for e in ("0.1", "0.3", "0.5", "0.7", "0.9") if (hi, e) in c]
        flip = next((signs[i + 1][0] for i in range(len(signs) - 1)
                     if signs[i][1] < 0.0 <= signs[i + 1][1]), None)
        out.append((f"Tp{ctag}Flip", flip if flip else "none"))

    # --- S2: how good must an unattended asset be before never checking wins? --------------------
    c = survey(LOG, S2, "success", ref="chk000", quiet=True)
    for qtag, q in (("Low", "0.3"), ("Mid", "0.5"), ("High", "0.7")):
        r = c.get(("chk100", q))
        if r:
            out += [(f"Ts{qtag}", f"{r[0]:+.4f}"), (f"Ts{qtag}V", r[4].replace("GATE ", "gates "))]

    # --- S4: is the check rate scheduled by slack or by the channel? ----------------------------
    c = survey(LOG, S4, "success", ref="n08r000", quiet=True)
    for ctag, cl in (("Clean", "0"), ("Deg", "3")):
        r = c.get(("n08r100", cl))
        if r:
            out += [(f"Tch{ctag}", f"{r[0]:+.4f}"), (f"Tch{ctag}V", r[4].replace("GATE ", "gates "))]

    dst = ROOT / "report" / "gen" / "trust_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:20s} {v}")


if __name__ == "__main__":
    main()
