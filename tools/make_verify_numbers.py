"""CR-63: the interior of the verification ladder, and the axis the crossing is actually on.

CR-61 measured the check rate at its two corners and one of those corners is a CONSTANT: at a
criterion that checks everything, the automation's error rate is irrelevant and the six cells are
byte-identical. A contrast against a reference that cannot move is a level wearing a difference,
which is instrument defect 15 in this project's ledger, and this battery exists to supply the
interior those two corners could not.

It supplied a retraction and a replacement. The registered claim, that the best rate is interior and
rises with the automation's error rate, is refuted by its own declared falsifier: in every cell of
all three harm channels a corner is either strictly best or inside the tolerance band. The crossing
is real and it is on the other axis, what a right answer is WORTH over autonomy, which is the
section the adversarial reviewer registered rather than the one I did.

    st-verify-9458832.out   R1 the check ladder interior, three harm channels
                            R2 the stakes ladder
                            R3 throughput or correctness
                            R4 the frontier against console load
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = "st-verify-9458832.out"
R1 = "R1 the check ladder interior, {} channel"
R2 = "R2 the stakes ladder, what a right answer is worth"
R3 = "R3 is the advantage throughput or correctness"
R4 = "R4 the frontier against console load"
ERRS = ("0.1", "0.3", "0.5", "0.7", "0.9")
RATES = (("Zero", "r000"), ("Quarter", "r025"), ("Half", "r050"),
         ("ThreeQ", "r075"), ("Full", "r100"))


def _v(r):
    return r[4].replace("GATE ", "gates ")


def main() -> None:
    out: list[tuple[str, str]] = []

    # --- R1. The retraction, stated as a count rather than as an argument. -----------------------
    # A corner counts as winning a cell when it is the argmax OR inside the tolerance band around
    # it. The registered falsifier was "a band that contains a corner in every cell", so the number
    # that settles it is how many of the fifteen cells have an interior rate strictly outside the
    # band around both corners. It is reported whatever it comes to.
    interior = corners = 0
    for ch in ("time", "weak", "reflect"):
        lv = survey(LOG, R1.format(ch), "success", quiet=True)
        if not lv:
            continue
        for i in range(len(ERRS)):
            col = {a: lv[a][i] for a, in ((a,) for _, a in RATES) if a in lv}
            best = max(col, key=col.get)
            corners += 1
            if best in ("r000", "r100"):
                continue
            # An interior argmax only counts if it clears the better corner by the gate's own
            # relative margin, which is what "strictly outside the band" means here.
            edge = max(col["r000"], col["r100"])
            if col[best] - edge > 0.06 * abs(edge):
                interior += 1
    out += [("DrCells", f"{corners}"), ("DrInterior", f"{interior}")]

    # The channel-by-channel corner contrast, which is what the retraction leaves standing.
    for ctag, ch in (("Time", "time"), ("Weak", "weak"), ("Refl", "reflect")):
        c = survey(LOG, R1.format(ch), "success", ref="r000", quiet=True)
        for etag, e in (("Lo", "0.1"), ("Mid", "0.5"), ("Hi", "0.9")):
            r = c.get(("r100", e))
            if r:
                out += [(f"Dr{ctag}{etag}", f"{r[0]:+.4f}"), (f"Dr{ctag}{etag}V", _v(r))]
        # The half rate too, because the retraction is about whether anything BETWEEN the corners
        # wins, and reporting only the corners would beg the question the section answers.
        r = c.get(("r050", "0.5"))
        if r:
            out += [(f"Dr{ctag}HalfMid", f"{r[0]:+.4f}"), (f"Dr{ctag}HalfMidV", _v(r))]

    # --- R2. The stakes ladder, where the crossing is. ------------------------------------------
    # `q_auto` is swept under a fixed operator, so the stakes g = q_operator - q_auto run the other
    # way: the FIRST sweep point is the highest stakes. Named by stakes, not by the knob, because a
    # requirement is written about what a decision is worth and not about a baseline parameter.
    for mtag, metric in (("", "success"), ("Loss", "blue_loss_frac")):
        c = survey(LOG, R2, metric, ref="g000", quiet=True)
        qs = sorted({k[1] for k in c}, key=float)
        if not qs:
            continue
        for stag, q in (("Hi", qs[0]), ("Mid", qs[2]), ("Lo", qs[-1])):
            for rtag, arm in (("Half", "g050"), ("Full", "g100")):
                r = c.get((arm, q))
                if r:
                    out += [(f"DrStake{rtag}{mtag}{stag}", f"{r[0]:+.4f}"),
                            (f"DrStake{rtag}{mtag}{stag}V", _v(r))]
        if mtag == "":
            out += [("DrStakeHiG", "0.45"), ("DrStakeMidG", "0.25"), ("DrStakeLoG", "0.05")]
            rh = c.get(("g100", qs[0]))
            if rh:
                out.append(("DrStakeHiV", _v(rh)))

    # --- R3. The one arm that can kill the throughput reading of the never-check result. ---------
    c = survey(LOG, R3, "success", ref="c000", quiet=True) if survey(LOG, R3, "success", quiet=True) else {}
    cs = sorted({k[1] for k in c}, key=float)
    for stag, q in zip(("Quarter", "Full"), (cs[0], cs[-1]) if cs else ((), ())):
        r = c.get(("c100", q))
        if r:
            out += [(f"DrComply{stag}", f"{r[0]:+.4f}"), (f"DrComply{stag}V", _v(r))]
    if cs:
        out += [("DrComplyLo", cs[0]), ("DrComplyHi", cs[-1])]

    # --- R4. The frontier against load, which is CR-61's S3 on the reflect channel at full tier. -
    c = survey(LOG, R4, "success", ref="l000", quiet=True) if survey(LOG, R4, "success", quiet=True) else {}
    for stag, sp in (("Four", "4"), ("Eight", "8"), ("Sixteen", "16")):
        r = c.get(("l100", sp))
        if r:
            out += [(f"DrLoad{stag}", f"{r[0]:+.4f}"), (f"DrLoad{stag}V", _v(r))]

    dst = ROOT / "report" / "gen" / "verify_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:20s} {v}")


if __name__ == "__main__":
    main()
