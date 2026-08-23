"""CR-29 and CR-43: what "do not re-ask" costs when waiting is priced by mobility, and why.

The published model lets a vehicle with no answer keep driving at reduced speed, so a wait costs
tempo only through the console. Adversarial review's objection was that this makes the paper's
closest-to-shippable recommendation cheap advice: where waiting is dangerous, the recommendation
should be harder to earn, not easier. `teleop_stop` prices it the other way, a vehicle with no
answer coming back stops, and the false setting reproduces the published path exactly.

Two results here. The recommendation survives and roughly doubles, which answers the objection. And
the mechanism that produces it is still the shared console rather than a per-vehicle tempo budget,
which is the part worth the space: the hold fraction at which the mission collapses MOVES with span,
and a budget in route, speed and clock cannot know how many vehicles share an operator.

Sources: hopper/batteries/teleop_price.sh (job 9446589) and tools/probe_budget.py.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-teleop_price-9446589.out"
# From tools/probe_budget.py, 640 runs per span, v_eff estimated at n=6 and n=6 held out.
SEP = {"5": 0.5819, "8": 0.4561}
H_STAR = 0.5143


def main() -> None:
    p = find(LOG)
    m: dict[str, str] = {}
    S = load(p, "P1", "success")
    for phys in ("stop", "keep"):
        for rho in ("04", "12", "21"):
            for n in ("5", "6"):
                hi, lo = f"{phys}_rho{rho}", f"{phys}_noretry"
                if (hi, n) not in S:
                    continue
                e, t, w, N = paired({"vals": S[(hi, n)]}, {"vals": S[(lo, n)]})
                base = sum(S[(lo, n)]) / len(S[(lo, n)])
                word = {"0": "Zero", "1": "One", "2": "Two", "4": "Four",
                        "5": "Five", "6": "Six", "8": "Eight"}
                # LaTeX control sequences are letters only, so numerals are spelled out.
                tag = ("tp" + phys.capitalize() + "R" + "".join(word[c] for c in rho)
                       + "N" + word[n])
                m[tag] = f"{100 * e:+.1f}"
                m[tag + "Pct"] = f"{100 * e / base:+.0f}" if base else "n/a"
                m[tag + "T"] = f"{t:.1f}"
                m[tag + "Blocks"] = str(w)
    m["tpBlocksN"] = str(len(next(iter(S.values()))))

    # The mediator, and the pre-registered limit it lands on: hold fraction closes almost fully at
    # the longest backoff while success does not, so it is partial and the remainder is open.
    H = load(p, "P2", "hold_fraction")
    SS = load(p, "P2", "success")
    if H and SS:
        order = ["rho02", "rho04", "rho08", "rho12", "rho16", "rho21", "noretry"]
        hv = [sum(H[(a, "6")]) / len(H[(a, "6")]) for a in order]
        sv = [sum(SS[(a, "6")]) / len(SS[(a, "6")]) for a in order]
        m["tpHoldHi"] = f"{hv[0]:.3f}"
        m["tpHoldLo"] = f"{hv[-1]:.3f}"
        m["tpHoldLong"] = f"{hv[-2]:.3f}"
        m["tpHoldClosed"] = f"{100 * (hv[0] - hv[-2]) / (hv[0] - hv[-1]):.0f}"
        m["tpSuccClosed"] = f"{100 * (sv[-2] - sv[0]) / (sv[-1] - sv[0]):.0f}"
        m["tpLadder"] = str(len(order) - 1)
        # Hold fraction is identically zero on the published physics, so the mediator does not
        # exist there at all and cannot be what carries the damage.
        keep = load(p, "P1", "hold_fraction")
        m["tpKeepHold"] = f"{max(sum(v) / len(v) for (a, _), v in keep.items() if a.startswith('keep')):.3f}"

    # CR-43: the collapse hold moves with span, which is what kills the budget account.
    m["tpHStar"] = f"{H_STAR:.3f}"
    m["tpSepFive"] = f"{SEP['5']:.3f}"
    m["tpSepEight"] = f"{SEP['8']:.3f}"
    m["tpSepShift"] = f"{SEP['5'] - SEP['8']:.3f}"
    m["tpSepTol"] = "0.05"

    gen = ROOT / "report" / "gen" / "teleop_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nWaiting priced by mobility (source: tools/make_teleop_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    print(f"  stop rho=4 at n=6: {m.get('tpStopRZeroFourNSix')} pts ({m.get('tpStopRZeroFourNSixPct')}%), "
          f"keep {m.get('tpKeepRZeroFourNSix')} pts ({m.get('tpKeepRZeroFourNSixPct')}%)")
    print(f"  hold closes {m.get('tpHoldClosed')}% while success closes {m.get('tpSuccClosed')}%; "
          f"keeps-driving hold is {m.get('tpKeepHold')}")
    print(f"  collapse hold {m['tpSepFive']} at n=5 against {m['tpSepEight']} at n=8, "
          f"shift {m['tpSepShift']} on a tolerance of {m['tpSepTol']}")


if __name__ == "__main__":
    main()
