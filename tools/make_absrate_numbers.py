"""CR-35: whether the service the response rule gives up is service that was going to be wasted.

The rate rule's finding was stated as a throughput gain and is not one: the console serves LESS.
What survives is a mission gain, and a mission gain with no account of its mechanism is a story. The
account on offer is that the forgone service was doomed service, and it is testable on two absolute
rates measured on the same runs: if the rule suppresses requests that would have been abandoned, the
fall in abandonment must be much larger than the fall in service.

The registered falsifier named `wasted_frac` as its second limb. The gate now refuses that metric,
because its denominator is the request count and the rule moves the request count by construction.
The limb is unreadable rather than failed, and `abandoned_per_step` carries the same question with no
denominator to move. That is recorded here rather than quietly substituted.

Source: hopper/batteries/absrate.sh, job 9446698.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_FRAC, FULL_T, rate_floor  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-absrate-9446698.out"
FLOOR = rate_floor()
WORDS = {"2": "NTwo", "4": "NFour", "6": "NSix", "8": "NEight",
         "10": "NTen", "12": "NTwelve", "16": "NSixteen"}


def contrast(d: dict, hi: str, lo: str, n: str) -> tuple:
    e, t, w, N = paired({"vals": d[(hi, n)]}, {"vals": d[(lo, n)]})
    base = sum(d[(lo, n)]) / len(d[(lo, n)])
    ok = abs(t) > FULL_T and w >= FULL_FRAC * N and abs(e) > FLOOR
    return e, t, w, N, base, (100 * e / base if base else 0.0), ok


def main() -> None:
    p = find(LOG)
    m: dict[str, str] = {}
    for sec, tag in (("A0", "Clear"), ("A3", "Jam")):
        srv = load(p, sec, "served_per_step")
        aba = load(p, sec, "abandoned_per_step")
        spans = sorted({k for a, k in srv if a == "admit"}, key=float)
        ratios, gated = [], []
        for n in spans:
            s = contrast(srv, "aimd", "admit", n)
            a = contrast(aba, "aimd", "admit", n)
            w = WORDS[n]
            m[f"ab{tag}{w}Srv"] = f"{s[5]:+.1f}"
            m[f"ab{tag}{w}Aba"] = f"{a[5]:+.1f}"
            m[f"ab{tag}{w}AbaAbs"] = f"{a[0]:+.4f}"
            m[f"ab{tag}{w}SrvAbs"] = f"{s[0]:+.4f}"
            m[f"ab{tag}{w}AbaT"] = f"{abs(a[1]):.0f}"
            if s[0] < 0 and a[0] < 0:
                # The exchange rate: abandonment removed per unit of service given up. This is the
                # statistic the mechanism claim is really about, and it is a ratio of two absolute
                # rates rather than of a rate to its own moving denominator.
                ratios.append((n, a[0] / s[0], a[5] / s[5]))
            if a[6]:
                gated.append(n)
        m[f"ab{tag}Spans"] = str(len(spans))
        m[f"ab{tag}AbaGated"] = str(len(gated))
        m[f"ab{tag}Blocks"] = str(len(srv[("admit", spans[0])]))
        if ratios:
            big = max(ratios, key=lambda r: r[1])
            m[f"ab{tag}RateHi"] = f"{big[1]:.0f}"
            m[f"ab{tag}RateHiSpan"] = big[0]
            m[f"ab{tag}RelMore"] = str(sum(1 for r in ratios if r[2] > 1.0))
            m[f"ab{tag}RelCells"] = str(len(ratios))

    # The second limb of the registered falsifier, and why it cannot be read.
    wf = load(p, "A0", "wasted_frac")
    rq = load(p, "A0", "requests_per_step")
    n = "12"
    e, t, w, N = paired({"vals": wf[("aimd", n)]}, {"vals": wf[("admit", n)]})
    de, dt, dw, dN = paired({"vals": rq[("aimd", n)]}, {"vals": rq[("admit", n)]})
    dbase = sum(rq[("admit", n)]) / len(rq[("admit", n)])
    m["abWfMove"] = f"{100 * e / (sum(wf[('admit', n)]) / len(wf[('admit', n)])):+.1f}"
    m["abWfDenom"] = f"{100 * de / dbase:+.1f}"

    gen = ROOT / "report" / "gen" / "absrate_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nCR-35, the doomed-service account (source: tools/make_absrate_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    for tag in ("Clear", "Jam"):
        print(f"  {tag}: abandonment falls faster than service in {m[f'ab{tag}RelMore']} of "
              f"{m[f'ab{tag}RelCells']} spans; best exchange {m[f'ab{tag}RateHi']} abandonments "
              f"removed per unit of service given up, at n={m[f'ab{tag}RateHiSpan']}; "
              f"abandonment gates at {m[f'ab{tag}AbaGated']} of {m[f'ab{tag}Spans']}")
    print(f"  wasted_frac moves {m['abWfMove']}% on a denominator that moves {m['abWfDenom']}%")


if __name__ == "__main__":
    main()
