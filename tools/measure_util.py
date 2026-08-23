"""Console utilization at the cells where the jitter recommendation is read.

Adversarial review's ruling on the capacity-anchored rate floor came with a condition: a relative
reading may appear beside an absolute one only if the reader can see what regime the console is in.
A seven percent rise in delivered service means one thing on a console running at capacity and
another on one running at a fifth of it, and the difference is exactly why the absolute floor
exists. This measures the regime rather than asserting it.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from sandtable.scenario import load_scenario  # noqa: E402
from sandtable.sim import run_mission  # noqa: E402

SC = "scenarios/sc_span_control.json"
SEEDS = 24
W = '{"retry_prob": 1.0, "fano_window": 7, "mult_window": 7}'


def main() -> None:
    scn = load_scenario(SC)
    base = {"control_mode": "direct", "comms_level": 3, "retry_prob": 1.0,
            "fano_window": 7, "mult_window": 7, "retry_backoff": 18}
    print(f"{'chan':>10} {'n':>3} {'arm':>4} {'util':>7} {'served/step':>12} {'share of cap':>13}")
    rows = []
    for chan, extra in (("memoryless", {}),
                        ("bursty", {"channel": "gilbert_elliot", "channel_clock": "step",
                                    "ge_burst_len": 120})):
        for n in (4, 5, 6, 8, 10):
            for arm, spread in (("fix", 0), ("jit", 17)):
                u = s = 0.0
                for seed in range(SEEDS):
                    m = run_mission(scn, seed=seed,
                                    params={**base, **extra, "n_blue": n, "retry_spread": spread})
                    u += m["operator_utilization"]
                    s += m["served_per_step"]
                u /= SEEDS
                s /= SEEDS
                rows.append((chan, n, arm, u, s))
                print(f"{chan:>10} {n:>3} {arm:>4} {u:7.3f} {s:12.4f} {100 * s / 0.15:12.1f}%")
    lo = min(r[3] for r in rows)
    hi = max(r[3] for r in rows)
    print(f"\nutilization across every cell the jitter paragraph reads: {lo:.3f} to {hi:.3f}")
    print("This is the console's BUSY fraction. Delivered useful service is a much smaller share of")
    print("capacity, because under the blind policy most of that busy time produces answers whose")
    print("requester has already given up, which is the congestion collapse of Section 5.")


if __name__ == "__main__":
    main()
