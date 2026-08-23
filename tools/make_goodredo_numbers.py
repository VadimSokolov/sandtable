"""The last three goodput sites, re-read on the rate no policy can inflate.

`operator_goodput` is serviced over requested, and every policy in this paper moves the
denominator, including the two I had argued could not. This battery re-runs the three remaining
manuscript sites on `served_per_step`, with `requests_per_step` logged on the same seeds so the
contamination is measured rather than assumed. Two of the three claims survive; the third's
falsifier fires, independently confirming what the cohort battery had already forced.

The interesting half is the direction of the bias. On the burst interaction the denominator moved
so as to HIDE the effect, where the two earlier findings had it inflating one. A bias whose sign is
not predictable from the treatment is why the fix is a gate rule and not a habit of checking.

Source: hopper/batteries/goodredo.sh, job 9447205.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_FRAC, FULL_T, rate_floor  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-goodredo-9447205.out"
FLOOR = rate_floor()


def did(d: dict, hi: tuple[str, str], lo: tuple[str, str], k: str) -> tuple:
    """A difference in differences, paired at the block. Both inner contrasts share the seed
    stream, so the outer difference is itself a paired quantity and gets a paired t."""
    a = [x - y for x, y in zip(d[(hi[0], k)], d[(hi[1], k)], strict=True)]
    b = [x - y for x, y in zip(d[(lo[0], k)], d[(lo[1], k)], strict=True)]
    return paired({"vals": a}, {"vals": b})


def mean(v: list[float]) -> float:
    return sum(v) / len(v)


def main() -> None:
    p = find(LOG)
    m: dict[str, str] = {}
    words = {"5": "NFive", "6": "NSix", "8": "NEight", "10": "NTen",
             "1": "ROne", "2": "RTwo", "3": "RThree"}

    # G1. Admission control's burst interaction, on delivered service.
    d = load(p, "G1", "served_per_step")
    q = load(p, "G1", "requests_per_step")
    spans = sorted({k for a, k in d if a == "bern_blind"}, key=float)
    gated = []
    for n in spans:
        e, t, w, N = did(d, ("ge_ref", "ge_blind"), ("bern_ref", "bern_blind"), n)
        ok = abs(t) > FULL_T and w >= FULL_FRAC * N and abs(e) > FLOOR
        tag = words[n]
        m[f"gr{tag}Did"] = f"{e:+.4f}"
        m[f"gr{tag}DidT"] = f"{abs(t):.1f}"
        m[f"gr{tag}Ge"] = f"{mean(d[('ge_ref', n)]) - mean(d[('ge_blind', n)]):+.4f}"
        m[f"gr{tag}Bern"] = f"{mean(d[('bern_ref', n)]) - mean(d[('bern_blind', n)]):+.4f}"
        # The denominator on the same seeds: which arm's asking moved further.
        for arm, lab in (("ge", "GeAsk"), ("bern", "BernAsk")):
            hi, lo = mean(q[(f"{arm}_ref", n)]), mean(q[(f"{arm}_blind", n)])
            m[f"gr{tag}{lab}"] = f"{100 * (hi - lo) / lo:+.1f}"
        if ok:
            gated.append(n)
    m["grSpans"] = str(len(spans))
    m["grGated"] = str(len(gated))
    m["grGatedLo"] = gated[0]
    m["grGatedHi"] = gated[-1]
    m["grBlocks"] = str(len(d[("ge_ref", spans[0])]))

    # G2. The self-collision decomposition. Registered falsifier: a null on the absolute rate.
    d2 = load(p, "G2", "served_per_step")
    sp2 = sorted({k for a, k in d2 if a == "bern_fix"}, key=float)
    best = 0.0
    for n in sp2:
        for arm in ("bern", "ge"):
            e, t, w, N = paired({"vals": d2[(f"{arm}_jit", n)]}, {"vals": d2[(f"{arm}_fix", n)]})
            best = max(best, abs(e))
    m["grJitCells"] = str(2 * len(sp2))
    m["grJitMax"] = f"{best:.4f}"
    m["grFloor"] = f"{FLOOR:.3f}"

    # G3. The reliance loop, where the LEVELS flip sign rather than a difference of differences.
    d3 = load(p, "G3", "served_per_step")
    rungs = sorted({k for a, k in d3 if a == "bern_off"}, key=float)
    opens, closeds, ts, blocks = [], [], [], []
    for r in rungs:
        eo, to, wo, N = paired({"vals": d3[("ge_off", r)]}, {"vals": d3[("bern_off", r)]})
        ec, tc, wc, _ = paired({"vals": d3[("ge_retry", r)]}, {"vals": d3[("bern_retry", r)]})
        e, t, w, _ = did(d3, ("ge_retry", "bern_retry"), ("ge_off", "bern_off"), r)
        tag = words[r]
        m[f"grFlip{tag}Open"] = f"{eo:+.4f}"
        m[f"grFlip{tag}Closed"] = f"{ec:+.4f}"
        m[f"grFlip{tag}Did"] = f"{e:+.4f}"
        m[f"grFlip{tag}DidT"] = f"{abs(t):.1f}"
        opens.append(eo)
        closeds.append(ec)
        ts.append(abs(t))
        blocks.append(w)
    m["grFlipRungs"] = str(len(rungs))
    m["grFlipOpenPos"] = str(sum(1 for x in opens if x > 0))
    m["grFlipClosedNeg"] = str(sum(1 for x in closeds if x < 0))
    m["grFlipMinT"] = f"{min(ts):.0f}"
    m["grFlipMaxT"] = f"{max(ts):.0f}"
    m["grFlipMinBlocks"] = str(min(blocks))
    m["grFlipBlocks"] = str(N)

    gen = ROOT / "report" / "gen" / "goodredo_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nThe last three goodput sites (source: tools/make_goodredo_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    print(f"  burst DiD gates at {m['grGated']} of {m['grSpans']} spans, "
          f"n={m['grGatedLo']} and n={m['grGatedHi']}")
    print(f"  asking moved {m['grNTenGeAsk']}% bursty against {m['grNTenBernAsk']}% memoryless at ten")
    print(f"  jit-fix peaks at {m['grJitMax']} over {m['grJitCells']} cells, floor {m['grFloor']}")
    print(f"  levels flip: {m['grFlipOpenPos']} of {m['grFlipRungs']} open positive, "
          f"{m['grFlipClosedNeg']} of {m['grFlipRungs']} closed negative, |t| {m['grFlipMinT']}-{m['grFlipMaxT']}")


if __name__ == "__main__":
    main()
