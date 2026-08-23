"""Decompose the wide-jitter contrast across channels, and bench the instrument that reads it.

Two numbers the paper needs and did not have.

FIRST, the decomposition. The wide-jitter contrast on the bursty link was originally read as one
effect. It is two: vehicles desynchronizing from EACH OTHER, which a channel with no dwell isolates
by construction, and whatever the channel's dwell adds on top. D1 and D2 are sections of one
battery run, so block `i` carries the same seed in both and the cross-channel difference in
differences is itself a paired quantity. No new compute is required to separate them.

SECOND, the bench. The paper wanted to explain the missing Fano signature on the bursty link by
saying the channel's own variance drowns the cohort's. That is a claim about the instrument, and it
is testable against a stream whose Fano is known in closed form. `tools/bench_fano.py` injects a
cohort of known size into both a memoryless and an on-off stream and reports what the shipped
estimator recovers. If it recovers the injected component on the bursty stream, the drowning
explanation is wrong and the null means the cohort is absent, which is a different paper.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-desync-9446092.out"
MPE = 0.03          # absolute; both metrics here live on a [0,1]-like scale
TCRIT = 1.70
MINWIN = 0.6


def load(sec: str, metric: str) -> dict:
    out, cur = {}, False
    for line in (ROOT / "report" / "data" / "queue" / LOG).read_text().splitlines():
        if line.startswith("### "):
            cur = sec in line and f"({metric})" in line
        elif cur and line.startswith("AR_ROW"):
            f = dict(p.split("=", 1) for p in line.split()[1:])
            out[(f["arm"], f["n_blue"])] = [float(v) for v in f["vals"].split(",")]
    return out


def gated(eff: float, t: float, w: int, n: int) -> bool:
    return abs(t) > TCRIT and abs(eff) >= MPE and w / n >= MINWIN


def main() -> None:
    m: dict[str, str] = {}
    words = {"5": "Five", "6": "Six"}

    # --- the decomposition ------------------------------------------------------------------
    ungated = []
    for metric, tag in (("operator_goodput", "Good"), ("arrival_fano", "Fano")):
        d1, d2 = load("### D1", metric), load("### D2", metric)
        for n, word in words.items():
            if ("jit18", n) not in d2:
                continue
            ge = [a - b for a, b in zip(d1[("jit18", n)], d1[("fix18", n)])]
            be = [a - b for a, b in zip(d2[("jit18", n)], d2[("fix18", n)])]
            # the self-collision part, isolated: no dwell exists for it to be confounded with
            e, t, w, N = paired({"vals": d2[("jit18", n)]}, {"vals": d2[("fix18", n)]})
            m[f"dc{tag}Self{word}"] = f"{e:+.4f}"
            m[f"dc{tag}Self{word}T"] = f"{t:.1f}"
            m[f"dc{tag}Self{word}Blocks"] = str(w)
            # the residue the dwell is responsible for, paired block by block across channels
            e2, t2, w2, N2 = paired({"vals": ge}, {"vals": be})
            m[f"dc{tag}Dwell{word}"] = f"{e2:+.4f}"
            m[f"dc{tag}Dwell{word}T"] = f"{t2:.1f}"
            m[f"dc{tag}Dwell{word}Blocks"] = str(w2)
            m[f"dc{tag}Dwell{word}Gate"] = "yes" if gated(e2, t2, w2, N2) else "no"
            if not gated(e2, t2, w2, N2):
                ungated.append((tag, word))
            m["dcBlocks"] = str(N)
    # the two dwell residues on goodput carry opposite signs; state it as a computed fact
    lo = float(m["dcGoodDwellFive"])
    hi = float(m["dcGoodDwellSix"])
    m["dcGoodDwellFlips"] = "yes" if lo * hi < 0 else "no"
    m["dcDwellUngated"] = str(len(ungated))

    # --- the bench --------------------------------------------------------------------------
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "bench_fano.py")],
                         capture_output=True, text=True, check=True).stdout
    rows = {}
    for line in out.splitlines():
        p = line.split()
        if len(p) == 8 and p[0] in ("memoryless", "on-off"):
            rows[(p[0], p[1])] = p
    for chan, key in (("memoryless", "Mem"), ("on-off", "Burst")):
        for wnd, wd in (("1", "One"), ("10", "Ten")):
            r = rows[(chan, wnd)]
            m[f"fb{key}W{wd}"] = f"{float(r[4]):.3f}"
            m[f"fb{key}W{wd}T"] = f"{float(r[5]):.0f}"
            m[f"fb{key}W{wd}Base"] = f"{float(r[2]):.2f}"
    # the worst recovery error over every channel and window: the headline the bench supports
    worst = max(abs(1.0 - float(r[4])) for r in rows.values())
    m["fbWorstErr"] = f"{100 * worst:.0f}"
    m["fbBurstWorstErr"] = f"{100 * max(abs(1.0 - float(r[4])) for k, r in rows.items() if k[0] == 'on-off'):.0f}"
    m["fbBlocks"] = "32"

    gen = ROOT / "report" / "gen" / "decomp_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    nums = ROOT / "report" / "results" / "numbers.txt"
    with nums.open("a") as fh:
        fh.write(f"\n\nCross-channel decomposition and Fano bench "
                 f"(source: tools/make_decomp_numbers.py over {LOG} and tools/bench_fano.py)\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen} and appended {len(m)} numbers to {nums}")


if __name__ == "__main__":
    main()
