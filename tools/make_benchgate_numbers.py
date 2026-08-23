"""The gate's own excess, computed exactly, which is the null every dwell reading needs.

`arrival_excess` normalizes collision multiplicity by the Poisson value at the stream's own measured
rate, so a perfectly scattered stream reads 1.0. A GATED stream does not: the gate correlates
arrivals over its dwell, and the correlation's effect at a window of fixed width depends on how the
dwell compares to the window. Below the window a gate REGULARIZES and the true excess falls below
one; above it, the excess rises. Neither is a retry cohort and neither has anything to do with the
model, and a dwell sweep read against a fixed null of 1.0 measures the difference between the two.

The numbers come from tools/bench_gate.py, which carries the joint law of (chain state, arrivals so
far) forward through the window by transfer matrix. That is a closed form evaluated numerically, not
a simulation, so it is a null and not another measurement.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT  # noqa: E402


def main() -> None:
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "bench_gate.py"),
                          "--blocks", "32", "--steps", "20000"],
                         capture_output=True, text=True,
                         env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
    rows = []
    for line in out.stdout.splitlines():
        f = line.split()
        if len(f) >= 8 and f[0].isdigit():
            rows.append((int(f[0]), float(f[3]), float(f[5])))       # dwell, true excess, bias
    if not rows:
        print("bench produced no rows:\n" + out.stdout + out.stderr)
        return
    rows.sort()
    cross = next((L for L, e, _ in rows if e >= 1.0), None)
    m = {"bgLowL": str(rows[0][0]), "bgLowNull": f"{rows[0][1]:.3f}",
         "bgHighL": str(rows[-1][0]), "bgHighNull": f"{rows[-1][1]:.3f}",
         "bgCrossL": str(cross) if cross else "n/a",
         "bgMaxBias": f"{max(abs(b) for _, _, b in rows):.4f}",
         "bgRows": str(len(rows))}
    gen = ROOT / "report" / "gen" / "benchgate_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write("\n\nGated-source null for arrival_excess (source: tools/bench_gate.py)\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}: null {m['bgLowNull']} at L={m['bgLowL']} to {m['bgHighNull']} "
          f"at L={m['bgHighL']}, crosses one near L={m['bgCrossL']}, "
          f"estimator bias never above {m['bgMaxBias']}")


if __name__ == "__main__":
    main()
