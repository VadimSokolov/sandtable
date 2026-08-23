"""CR-37: the P1 re-run at a window taken from the bench power curve, not from an argument.

D1/D2 read P1 through `fano_window = 120`, the channel dwell, on the reasoning that the channel's
structure lives there. `tools/bench_fano.py` injects a cohort of known size and shows the estimator
recovers 0.681 of it at t = 4.7 at that window, against 0.936 at t = 25 at a window of 7. The
refutation was therefore read through an instrument with a fifth of the power available, and P1's
status was VOID, not refuted, pending this run.

Window 7 is one service time at 0.15 completions per step. It was registered before any number from
this battery was looked at, and it is not the window with the most power on the bench: window 1 has
more, and is deliberately not chosen, because a one-step window asks whether two requests land on
the same tick, and the mechanism is about landing inside one service.

Source: hopper/batteries/fanoredo.sh, job 9446726.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-fanoredo-9446726.out"
GATE_T, GATE_FRAC = 1.70, 0.60


def load(sec: str, metric: str) -> dict:
    """Rows of one section as {(arm, sweep value): [block values]}."""
    out: dict[tuple[str, str], list[float]] = {}
    cur = False
    for line in (ROOT / "report" / "data" / "queue" / LOG).read_text().splitlines():
        if line.startswith("### "):
            cur = line.startswith(f"### {sec} ") and line.rstrip().endswith(f"({metric})")
        elif cur and line.startswith("AR_ROW"):
            f = dict(p.split("=", 1) for p in line.split()[1:])
            key = next(v for k, v in f.items() if k not in ("arm", "mean", "vals"))
            out[(f["arm"], key)] = [float(v) for v in f["vals"].split(",")]
    return out


def pairs(d: dict) -> list[tuple[str, str, float, float, float, int, int]]:
    """Every (fixNN, jitNN) x sweep-point contrast present, as jit - fix."""
    got = []
    for rho in sorted({a[3:] for a, _ in d if a.startswith("fix")}):
        for n in sorted({k for a, k in d if a == f"fix{rho}"}, key=float):
            fix, jit = d.get((f"fix{rho}", n)), d.get((f"jit{rho}", n))
            if fix is None or jit is None:
                continue
            e, t, w, N = paired({"vals": jit}, {"vals": fix})
            got.append((rho, n, sum(fix) / len(fix), e, t, w, N))
    return got


def gated(row) -> bool:
    _, _, base, e, t, w, N = row
    return abs(t) > GATE_T and w >= GATE_FRAC * N and abs(e) > 0.06 * abs(base)


def main() -> None:
    m: dict[str, str] = {}
    for sec, tag in (("F1", "Ge"), ("F2", "Mem")):
        rows = pairs(load(sec, "arrival_fano"))
        if not rows:
            continue
        red = [r for r in rows if r[3] < 0 and gated(r)]
        m[f"fr{tag}Pairs"] = str(len(rows))
        m[f"fr{tag}Red"] = str(len(red))
        # The two extremes of the reduction, absolute and as a share of the fixed arm's own Fano,
        # so the prose can say how big without picking a pair by hand.
        m[f"fr{tag}Min"] = f"{max(r[3] for r in red):+.2f}"
        m[f"fr{tag}Max"] = f"{min(r[3] for r in red):+.2f}"
        m[f"fr{tag}MinPct"] = f"{100 * max(r[3] / r[2] for r in red):.0f}"
        m[f"fr{tag}MaxPct"] = f"{100 * min(r[3] / r[2] for r in red):.0f}"
        m[f"fr{tag}MinT"] = f"{min(abs(r[4]) for r in red):.0f}"
        m[f"fr{tag}MaxT"] = f"{max(abs(r[4]) for r in red):.0f}"
        m[f"fr{tag}Blocks"] = str(min(r[5] for r in red))
        m[f"fr{tag}BlocksN"] = str(rows[0][6])
        # The largest fix-arm Fano, which is what the jitter is working against.
        m[f"fr{tag}Base"] = f"{max(r[2] for r in rows):.2f}"
    # The goodput at the same settings, to say whether the desynchronization is free here.
    good = pairs(load("F1", "operator_goodput"))
    if good:
        m["frGoodPairs"] = str(len(good))
        m["frGoodUp"] = str(sum(1 for r in good if r[3] > 0 and gated(r)))
        m["frGoodDown"] = str(sum(1 for r in good if r[3] < 0 and gated(r)))
        m["frGoodMax"] = f"{max(r[3] for r in good):+.3f}"
    # Excess at the same window: a Fano is a variance and cannot separate many small clusters
    # from few large ones, so the multiplicity-based statistic runs alongside it.
    exc = pairs(load("F1", "arrival_excess"))
    if exc:
        m["frExcPairs"] = str(len(exc))
        m["frExcRed"] = str(sum(1 for r in exc if r[3] < 0 and gated(r)))

    gen = ROOT / "report" / "gen" / "fanoredo_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nP1 re-run at the benched window (source: tools/make_fanoredo_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    for sec, tag in (("F1", "Ge"), ("F2", "Mem")):
        if f"fr{tag}Red" in m:
            print(f"  {sec} {tag}: {m[f'fr{tag}Red']} of {m[f'fr{tag}Pairs']} gated reductions, "
                  f"{m[f'fr{tag}Min']} to {m[f'fr{tag}Max']} "
                  f"({m[f'fr{tag}MinPct']}% to {m[f'fr{tag}MaxPct']}%), "
                  f"|t| {m[f'fr{tag}MinT']} to {m[f'fr{tag}MaxT']}")
    if good:
        print(f"  goodput: {m['frGoodUp']} up / {m['frGoodDown']} down of {m['frGoodPairs']}")
    if exc:
        print(f"  excess:  {m['frExcRed']} of {m['frExcPairs']} gated reductions")


if __name__ == "__main__":
    main()
