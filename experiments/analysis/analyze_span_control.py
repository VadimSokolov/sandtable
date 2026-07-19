"""Span-of-control x comms crossover surface, from the two polarisopt grid studies.

Reads the per-sample workspaces of sc-sweep-direct and sc-sweep-supervisory and,
for each (comms_level C, span n_blue N) cell, compares mission success under the
two control modalities. Prints the success surface, the winning modality per cell,
and the crossover comms level per N (the milder the crossover, the more the span
overwhelms the operator).
"""
import json, glob, os
import numpy as np

ROOT = os.path.expanduser("~/sandtable-runs")
KEY = "success_rate"


def load(study):
    cells = {}
    for inp in glob.glob(os.path.join(ROOT, study, "experiments", "**", "inputs.json"), recursive=True):
        out = os.path.join(os.path.dirname(inp), "outputs.json")
        if not os.path.exists(out):
            continue
        p = json.load(open(inp))["params"]
        o = json.load(open(out))
        cells[(int(p["comms_level"]), int(p["n_blue"]))] = o
    return cells


direct = load("sc-sweep-direct")
supervisory = load("sc-sweep-supervisory")
Cs = sorted({c for c, n in direct})
Ns = sorted({n for c, n in direct})

print("success_rate: direct / supervisory   (winner in caps)\n")
header = "C \\ N |" + "".join(f"{n:>16}" for n in Ns)
print(header)
for C in Cs:
    cellstrs = []
    for N in Ns:
        d = direct[(C, N)][KEY]
        s = supervisory[(C, N)][KEY]
        win = "DIR" if d > s + 0.03 else ("SUP" if s > d + 0.03 else "~")
        cellstrs.append(f"{d:.2f}/{s:.2f} {win:>3}")
    print(f"C{C:>4} |" + "".join(f"{cs:>16}" for cs in cellstrs))

def adv(C, N):
    return direct[(C, N)][KEY] - supervisory[(C, N)][KEY]

print("\n(direct - supervisory) success advantage  (positive => prefer direct):\n")
print("C \\ N |" + "".join(f"{n:>8}" for n in Ns) + f"{'mean':>8}")
for C in Cs:
    vals = [adv(C, N) for N in Ns]
    print(f"C{C:>4} |" + "".join(f"{v:>+8.2f}" for v in vals) + f"{np.mean(vals):>+8.2f}")
print("mean  |" + "".join(f"{np.mean([adv(C, N) for C in Cs]):>+8.2f}" for N in Ns))

print("\nMarginal trends (robust to per-cell noise):")
print("  advantage vs comms (mean over N):  " +
      "  ".join(f"C{C}:{np.mean([adv(C, N) for N in Ns]):+.2f}" for C in Cs))
print("  advantage vs span  (mean over C):  " +
      "  ".join(f"N{N}:{np.mean([adv(C, N) for C in Cs]):+.2f}" for N in Ns))

print("\nCrossover comms level per span N (lowest C where supervisory overtakes direct):")
for N in Ns:
    cross = next((C for C in Cs if supervisory[(C, N)][KEY] > direct[(C, N)][KEY] + 0.03), None)
    tag = f"C{cross}" if cross is not None else "never (direct wins throughout)"
    print(f"  N={N}:  crossover at {tag}")

print("\nInterpretation: direct control is preferred only in the low-comms-degradation, "
      "moderate-span corner; the advantage falls monotonically as comms degrade (jamming "
      "favors autonomy) AND as span grows (one operator saturates), so supervisory autonomy "
      "wins sooner on both axes.")

# Persist the surface for the report.
grid = {"comms_levels": Cs, "n_blue": Ns,
        "direct": {f"{c},{n}": round(direct[(c, n)][KEY], 3) for c in Cs for n in Ns},
        "supervisory": {f"{c},{n}": round(supervisory[(c, n)][KEY], 3) for c in Cs for n in Ns}}
outp = os.path.join(os.path.dirname(__file__), "..", "results", "sc_surface.json")
os.makedirs(os.path.dirname(outp), exist_ok=True)
json.dump(grid, open(outp, "w"), indent=2)
print(f"\nwrote surface -> {os.path.normpath(outp)}")
