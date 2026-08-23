"""The control that settles what a randomized hold actually removes.

Every earlier reading of the retry cohort compared a jittered arm against a closed-form floor: the
excess a perfectly scattered stream would show, or a Bernoulli-source calculation, or a gated-source
one. Three references, three different answers, and two rounds of argument about which was right.
The question is unnecessary. The reference a fleet that retries should be compared against is a
fleet that does not, measured under everything else identical, and this battery runs it.

`noretry` has the reliance loop open: a rebuffed vehicle goes autonomous and does not come back. It
is the same code path, the same seeds, and the same channel as the retry arms, so every nuisance
parameter that made the closed forms disagree cancels.

Source: hopper/batteries/noretry.sh, job 9446872.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_FRAC, FULL_MPE, FULL_T  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-noretry-9446872.out"


def main() -> None:
    p = find(LOG)
    m: dict[str, str] = {}
    for sec, tag in (("N1", "Mem"), ("N2", "Ge")):
        d = load(p, sec, "arrival_excess")
        if not d:
            continue
        spans = sorted({k for a, k in d if a == "noretry"}, key=float)
        jit, fix = [], []
        for n in spans:
            for arm, out in (("jit18", jit), ("fix18", fix)):
                if (arm, n) not in d:
                    continue
                e, t, w, N = paired({"vals": d[(arm, n)]}, {"vals": d[("noretry", n)]})
                base = sum(d[("noretry", n)]) / len(d[("noretry", n)])
                ok = abs(t) > FULL_T and w >= FULL_FRAC * N and abs(e) > FULL_MPE * base
                out.append((n, e, t, w, N, 100 * e / base, ok))
        m[f"nr{tag}Spans"] = str(len(spans))
        m[f"nr{tag}SpanLo"] = spans[0]
        m[f"nr{tag}SpanHi"] = spans[-1]
        # The jittered arm against the control: the claim is that nothing survives.
        m[f"nr{tag}JitGated"] = str(sum(1 for x in jit if x[6]))
        m[f"nr{tag}JitMaxT"] = f"{max(abs(x[2]) for x in jit):.2f}"
        m[f"nr{tag}JitMaxPct"] = f"{max(abs(x[5]) for x in jit):.1f}"
        m[f"nr{tag}JitMinBlocks"] = str(min(x[3] for x in jit))
        m[f"nr{tag}JitMaxBlocks"] = str(max(x[3] for x in jit))
        m[f"nr{tag}Blocks"] = str(jit[0][4])
        # The fixed arm against the same control: the scale of what jitter removes.
        m[f"nr{tag}FixGated"] = str(sum(1 for x in fix if x[6]))
        m[f"nr{tag}FixCells"] = str(len(fix))
        m[f"nr{tag}FixLoPct"] = f"{fix[0][5]:.1f}"
        m[f"nr{tag}FixHiPct"] = f"{fix[-1][5]:.1f}"
        m[f"nr{tag}FixMinT"] = f"{min(abs(x[2]) for x in fix):.0f}"
        m[f"nr{tag}FixMaxT"] = f"{max(abs(x[2]) for x in fix):.0f}"
        # Monotone growth in span is the shape, so it is counted rather than asserted.
        m[f"nr{tag}FixRising"] = str(sum(1 for a, b in zip(fix, fix[1:]) if b[5] > a[5]))
        m[f"nr{tag}FixSteps"] = str(len(fix) - 1)

    gen = ROOT / "report" / "gen" / "noretry_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nThe no-retry control (source: tools/make_noretry_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    for tag in ("Mem", "Ge"):
        if f"nr{tag}JitGated" in m:
            print(f"  {tag}: jitter vs no-retry gates {m[f'nr{tag}JitGated']} of "
                  f"{m[f'nr{tag}Spans']} spans, |t| at most {m[f'nr{tag}JitMaxT']}; "
                  f"fixed vs no-retry gates {m[f'nr{tag}FixGated']} of {m[f'nr{tag}FixCells']}, "
                  f"{m[f'nr{tag}FixLoPct']}% to {m[f'nr{tag}FixHiPct']}%, "
                  f"{m[f'nr{tag}FixRising']} of {m[f'nr{tag}FixSteps']} steps rising")


if __name__ == "__main__":
    main()
