"""The jitter recommendation on every metric that no policy can inflate.

The paragraph this feeds used to be stated on `operator_goodput`, which is serviced over requested.
A jittered hold and a fixed hold of the same mean do not offer the same load: jitter changes when a
rebuffed vehicle comes back, which changes how often it is refused again, which moves the
denominator. The claim therefore has to be made on mission success, which is bounded and cannot be
inflated, and on `served_per_step`, which is an absolute rate with no denominator at all.

Both are read here, and the rate is read against the floor that matters for a rate: six percent of
what one console can deliver, not six percent of a baseline that goes to zero when the console
collapses. That floor was adopted on adversarial review and its first real test was this paragraph.

Sources: hopper/batteries/desync.sh (job 9446092, section D1) for success at matched mean hold, and
hopper/batteries/cohort.sh (job 9446609, sections K1 and K2) for the absolute service rate.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import CAPACITY, FULL_FRAC, FULL_MPE, FULL_T, rate_floor  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

WORD = {"4": "Four", "5": "Five", "6": "Six", "8": "Eight", "10": "Ten"}


def main() -> None:
    m: dict[str, str] = {}

    # Mission success at a matched mean hold, three widths by two spans.
    d = load(find("st-desync-9446092.out"), "D1", "success")
    gated = []
    for w in ("04", "10", "18"):
        for n in ("5", "6"):
            if (f"jit{w}", n) not in d:
                continue
            e, t, ww, N = paired({"vals": d[(f"jit{w}", n)]}, {"vals": d[(f"fix{w}", n)]})
            base = sum(d[(f"fix{w}", n)]) / len(d[(f"fix{w}", n)])
            ok = abs(t) > FULL_T and ww >= FULL_FRAC * N and abs(e) > FULL_MPE * base
            if ok:
                gated.append((w, n, e, t, ww, N))
    m["jcSuccCells"] = str(sum(1 for w in ("04", "10", "18") for n in ("5", "6")
                               if (f"jit{w}", n) in d))
    m["jcSuccGated"] = str(len(gated))
    if gated:
        best = max(gated, key=lambda r: abs(r[2]))
        m["jcSuccBest"] = f"{100 * best[2]:+.1f}"
        m["jcSuccBestT"] = f"{best[3]:.2f}"
        m["jcSuccBestBlocks"] = str(best[4])
        m["jcSuccBestN"] = str(best[5])
        m["jcSuccSpan"] = "".join(sorted({WORD[r[1]] for r in gated}))
        m["jcSuccSpanNum"] = ", ".join(sorted({r[1] for r in gated}))

    # The absolute service rate, both channels, at the width the paragraph quotes.
    p = find("st-cohort-9446609.out")
    floor = rate_floor()
    m["jcFloor"] = f"{floor:.3f}"
    m["jcCapacity"] = f"{CAPACITY:.2f}"
    for sec, tag in (("K1", "Mem"), ("K2", "Ge")):
        r = load(p, sec, "served_per_step")
        if not r:
            continue
        rows = []
        for n in sorted({k for a, k in r if a == "jit18"}, key=float):
            e, t, w, N = paired({"vals": r[("jit18", n)]}, {"vals": r[("fix18", n)]})
            base = sum(r[("fix18", n)]) / len(r[("fix18", n)])
            rows.append((n, e, t, w, N, 100 * e / base if base else 0.0))
        m[f"jc{tag}Cells"] = str(len(rows))
        m[f"jc{tag}Gated"] = str(sum(1 for x in rows
                                     if abs(x[2]) > FULL_T and x[3] >= FULL_FRAC * x[4]
                                     and abs(x[1]) > floor))
        m[f"jc{tag}Max"] = f"{max(x[1] for x in rows):+.4f}"
        m[f"jc{tag}MaxT"] = f"{max(abs(x[2]) for x in rows):.1f}"
        m[f"jc{tag}RelLo"] = f"{min(x[5] for x in rows):+.0f}"
        m[f"jc{tag}RelHi"] = f"{max(x[5] for x in rows):+.0f}"
        m[f"jc{tag}MaxShare"] = f"{100 * max(x[1] for x in rows) / CAPACITY:.1f}"
        # The six-asset cell specifically, which is where the text compares the two channels.
        six = next((x for x in rows if x[0] == "6"), None)
        if six:
            m[f"jc{tag}Six"] = f"{six[1]:+.4f}"
            m[f"jc{tag}SixRel"] = f"{six[5]:+.0f}"
            m[f"jc{tag}SixT"] = f"{six[2]:.1f}"
            m[f"jc{tag}SixBlocks"] = str(six[3])
            m[f"jc{tag}SixN"] = str(six[4])

    gen = ROOT / "report" / "gen" / "jitclean_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write("\n\nJitter on uninflatable metrics (source: tools/make_jitclean_numbers.py)\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    print(f"  success: {m.get('jcSuccGated')} of {m.get('jcSuccCells')} cells gate, "
          f"best {m.get('jcSuccBest')} pts at n={m.get('jcSuccSpanNum')}")
    for tag in ("Mem", "Ge"):
        if f"jc{tag}Gated" in m:
            print(f"  served/step {tag}: {m[f'jc{tag}Gated']} of {m[f'jc{tag}Cells']} gate; "
                  f"largest {m[f'jc{tag}Max']} = {m[f'jc{tag}MaxShare']}% of capacity, "
                  f"relative {m[f'jc{tag}RelLo']}% to {m[f'jc{tag}RelHi']}%")


if __name__ == "__main__":
    main()
