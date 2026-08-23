"""CR-52: what changes when the map changes, and what does not.

Every result in this paper before today was found on one map, a lateral Gaussian band of cover with
no longitudinal structure. Two more were built to attack from opposite sides: `open` has no cover at
all and is the negative control for anything terrain is claimed to do, and `chokepoint` is a
transverse ridge with one gap, so a dispersed force converges where the MAP chooses rather than
where the operator does.

The script exists to make one contrast easy to state and hard to overstate. The console-level lever
is nearly identical on all three maps; the mission-level one is not, and the difference between
those two facts is the finding. Reading either alone gives the wrong answer about how general the
result is.

    st-maps-9448824.out   M1 (blind against admit, three maps), M2 (the capacity ladder, three maps)
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import rate_floor  # noqa: E402
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = "st-maps-9448824.out"
M1 = "M1 the lever against the map"
M2 = "M2 the capacity ladder against the map"
MAPS = (("Band", "band"), ("Choke", "choke"), ("Open", "open"))
MPE = rate_floor()


def main() -> None:
    out: list[tuple[str, str]] = []
    p1, p2 = ["4", "6", "8", "10", "12", "16"], ["8", "12", "16"]

    srv = survey(LOG, M1, "served_per_step", quiet=True)
    suc = survey(LOG, M1, "success", quiet=True)
    for tag, m in MAPS:
        # The console lever, where the three maps should agree, and the mission lever, where they
        # should not. Both at the same two spans so the pair can be read as a pair.
        for span, sp in (("Coll", "8"), ("Full", "16")):
            i = p1.index(sp)
            out += [(f"Mp{tag}Srv{span}", f"{srv[m + '_admit'][i] - srv[m + '_blind'][i]:+.4f}"),
                    (f"Mp{tag}Suc{span}", f"{100 * (suc[m + '_admit'][i] - suc[m + '_blind'][i]):+.1f}")]
        out.append((f"Mp{tag}BlindFull", f"{100 * suc[m + '_blind'][p1.index('16')]:.1f}"))
    # The spread of the console lever across maps, which is the number that licenses "map-invariant".
    at16 = [srv[m + "_admit"][p1.index("16")] - srv[m + "_blind"][p1.index("16")] for _, m in MAPS]
    out += [("MpSrvSpread", f"{max(at16) - min(at16):.4f}"), ("MpMPE", f"{MPE:.4f}")]

    try:
        cap = survey(LOG, M2, "served_per_step", quiet=True)
    except SystemExit:
        cap = None
    if cap:
        # The capacity ladder's shape, counted rather than tabulated: how many of the nine cells put
        # k* above one below it, and how many put it above two above it. Both should be nine, and
        # what separates them is that only the second is a MATERIAL margin.
        lo = sum(1 for _, m in MAPS for i in range(len(p2)) if cap[m + "_c2"][i] > cap[m + "_c1"][i])
        hi = sum(1 for _, m in MAPS for i in range(len(p2))
                 if cap[m + "_c2"][i] - cap[m + "_c4"][i] > MPE)
        worst = min(cap[m + "_c2"][i] - cap[m + "_c4"][i] for _, m in MAPS for i in range(len(p2)))
        best_lo = max(cap[m + "_c2"][i] - cap[m + "_c1"][i] for _, m in MAPS for i in range(len(p2)))
        out += [("MpCapCells", f"{3 * len(p2)}"), ("MpCapLoWin", f"{lo}"), ("MpCapHiWin", f"{hi}"),
                ("MpCapUnderWorst", f"{best_lo:.4f}"), ("MpCapOverWorst", f"{worst:.4f}")]

    dst = ROOT / "report" / "gen" / "maps_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:18s} {v}")


if __name__ == "__main__":
    main()
