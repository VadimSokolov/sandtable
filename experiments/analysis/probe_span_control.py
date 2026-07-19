"""Probe the span-of-control C2 mechanism: does direct beat supervisory at good
comms and lose at bad comms (the crossover)? And does larger N move the crossover
earlier?"""
import sys
from sandtable.scenario import load_scenario
from sandtable.sim import evaluate

scn = load_scenario("scenarios/sc_span_control.json")
N_REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
Ns = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["4", "8"])]
SERVICE_RATE = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
DEC_INT = int(sys.argv[4]) if len(sys.argv) > 4 else 30
print(f"service_rate={SERVICE_RATE}, decision_interval={DEC_INT}")

for N in Ns:
    util = N * (1.0 / SERVICE_RATE) / DEC_INT
    print(f"\n===== N (agents/operator) = {N},  n_reps={N_REPS},  operator_util~{util:.2f} =====")
    print(f"{'C':>2} | {'direct succ':>11} {'sup succ':>9} | "
          f"{'dir bLoss':>9} {'sup bLoss':>9} | {'dir time':>8} {'sup time':>8} | winner")
    for C in range(6):
        row = {}
        for mode in ("direct", "supervisory"):
            r = evaluate(scn, n_reps=N_REPS, seed=11,
                         params={"control_mode": mode, "comms_level": C, "n_blue": N,
                                 "service_rate": SERVICE_RATE, "decision_interval": DEC_INT})
            row[mode] = r
        d, s = row["direct"], row["supervisory"]
        win = "direct" if d["success"] > s["success"] + 0.02 else (
              "supervisory" if s["success"] > d["success"] + 0.02 else "tie")
        print(f"{C:>2} | {d['success']:>11.2f} {s['success']:>9.2f} | "
              f"{d['blue_losses']:>9.2f} {s['blue_losses']:>9.2f} | "
              f"{d['time_to_objective']:>8.0f} {s['time_to_objective']:>8.0f} | {win}")
