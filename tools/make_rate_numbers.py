"""The queue policies read on the absolute rate, because the ratio has a denominator they change.

`operator_goodput = n_serviced / n_request` and every policy in this paper changes `n_request`.
A refusal sends a vehicle back to autonomy sooner, so it re-consults sooner and the denominator
inflates. An AIMD rate rule does the opposite by construction, and the whole point of the rule is
to deflate it. So the metric flatters the rule and penalizes the refusal, and both effects are
invisible in the ratio itself. CR-23R established this for retries; it was never applied to the
policies, which change the asking at least as much.

`served_per_step` has no denominator to move. `requests_per_step` measures the inflation directly
rather than inferring it. Reading the two together is what separates a console doing more work from
a console being asked less.

Source: hopper/batteries/admitrate.sh, job 9446591.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-admitrate-9446591.out"
WORD = {"4": "Four", "6": "Six", "8": "Eight", "10": "Ten", "12": "Twelve"}


def load(sec: str, metric: str) -> dict:
    out, cur = {}, False
    for line in (ROOT / "report" / "data" / "queue" / LOG).read_text().splitlines():
        if line.startswith("### "):
            cur = line.startswith(f"### {sec} ") and f"({metric})" in line
        elif cur and line.startswith("AR_ROW"):
            f = dict(p.split("=", 1) for p in line.split()[1:])
            out[(f["arm"], f["n_blue"])] = [float(v) for v in f["vals"].split(",")]
    return out


def main() -> None:
    m: dict[str, str] = {}
    for sec, rung in (("E0", "Clear"), ("E2", "Jam")):
        for metric, mtag in (("served_per_step", "Served"), ("requests_per_step", "Asked")):
            d = load(sec, metric)
            if not d:
                continue
            for (hi, lo), ctag in ((("admit", "refund"), "AdmitOverRefund"),
                                   (("aimd", "admit"), "AimdOverAdmit")):
                for n, w in WORD.items():
                    if (hi, n) not in d or (lo, n) not in d:
                        continue
                    e, t, wins, N = paired({"vals": d[(hi, n)]}, {"vals": d[(lo, n)]})
                    ref = sum(d[(lo, n)]) / len(d[(lo, n)])
                    key = f"rt{mtag}{ctag}{rung}{w}"
                    # Relative, because these are rate metrics: the MPE for them is 6% of the
                    # control arm, not an absolute constant calibrated on [0,1] near 0.5.
                    m[key] = f"{100 * e / ref:+.1f}\\%"
                    m[key + "T"] = f"{t:.1f}"
                    m[key + "Blocks"] = str(wins)
                    m[key + "Gate"] = ("yes" if abs(t) > 1.70 and abs(e) >= 0.06 * ref
                                       and wins / N >= 0.6 else "no")
                    m["rtBlocks"] = str(N)
    # The two facts the rewritten prose turns on, computed rather than asserted.
    if "rtServedAimdOverAdmitClearTwelve" in m:
        m["rtAimdWorkVerdict"] = ("less" if m["rtServedAimdOverAdmitClearTwelve"].startswith("-")
                                  else "more")
    if "rtServedAdmitOverRefundClearTwelve" in m:
        m["rtAdmitWorkVerdict"] = ("less" if m["rtServedAdmitOverRefundClearTwelve"].startswith("-")
                                   else "more")
    gen = ROOT / "report" / "gen" / "rate_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nQueue policies on the absolute rate (source: tools/make_rate_numbers.py "
                 f"over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen} with {len(m)} numbers")


if __name__ == "__main__":
    main()
