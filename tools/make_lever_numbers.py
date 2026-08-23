"""CR-47 and CR-48 together: the four levers that rescue a collapsed console, and their price list.

The manuscript paragraph this feeds makes one claim that is stronger than the sum of its parts, so
the script is organised around the control that licenses it. Four policies reach nearly the same
delivered service on a blind console at sixteen assets. A fifth, RANDOM service order, does not. If
the mechanism were "oldest-first is a rigid order and any shake-up helps", random would work; it
recovers about a twentieth of what the others do. So the mechanism is not the order, and the four
results are one result seen from four sides.

Reads two full-tier batteries and writes the macros the manuscript inputs. Nothing is recomputed
here that a battery already measured.

    st-lifo-9448647.out   G1 (fifo / rand / lifo / admit), G2 (the comms ladder), G3 (substitution)
    st-qcap-9448688.out   Q1 (the capacity ladder, from which cap_two is k*)
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import rate_floor  # noqa: E402
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = {"8": "Eight", "12": "Twelve", "16": "Sixteen"}   # LaTeX macro names carry no digits
LIFO, QCAP = "st-lifo-9448647.out", "st-qcap-9448688.out"
G1 = "G1 newest-first against oldest-first on a blind console, clear link"
MPE = rate_floor()


def _pct(v: float) -> str:
    """Percentages that span three orders of magnitude here, so the precision follows the value."""
    return f"{v:.1f}" if v >= 1.0 else f"{v:.2f}"


def at(rows: dict, arm: str, pts: list[str], p: str) -> float:
    return rows[arm][pts.index(p)]


def main() -> None:
    out: list[tuple[str, str]] = []

    # --- the price list at sixteen assets, clear link -------------------------------------------
    srv, pts = survey(LIFO, G1, "served_per_step", quiet=True), ["4", "5", "6", "8", "10", "12", "16"]
    stl = survey(LIFO, G1, "stale_frac", quiet=True)
    bkl = survey(LIFO, G1, "backlog_mean", quiet=True)
    cap = survey(QCAP, "Q1 the capacity ladder", "served_per_step", quiet=True)
    cpts = ["6", "8", "10", "12", "16"]

    for tag, arm in (("Fifo", "fifo"), ("Rand", "rand"), ("Lifo", "lifo"), ("Admit", "adm")):
        out += [(f"LvSrv{tag}", f"{at(srv, arm, pts, '16'):.4f}"),
                (f"LvStale{tag}", _pct(100 * at(stl, arm, pts, '16'))),
                (f"LvBack{tag}", f"{at(bkl, arm, pts, '16'):.0f}")]
    out += [("LvSrvBound", f"{at(cap, 'cap_two', cpts, '16'):.4f}"),
            ("LvSrvNone", f"{at(cap, 'cap_none', cpts, '16'):.4f}")]

    # The random arm is the control the whole paragraph rests on, so it is reported as a SHARE of
    # what newest-first recovers, not as a bare level. Both are measured against the same baseline.
    gain = {a: at(srv, a, pts, "16") - at(srv, "fifo", pts, "16") for a in ("rand", "lifo", "adm")}
    out += [("LvRandGain", f"{gain['rand']:+.4f}"),
            ("LvLifoGain", f"{gain['lifo']:+.4f}"),
            ("LvRandShare", f"{100 * gain['rand'] / gain['lifo']:.0f}"),
            ("LvMPE", f"{MPE:.4f}"),
            # The capacity the whole comparison is against. `rate_floor` is FULL_MPE * CAPACITY, so
            # dividing recovers it rather than restating a constant that could drift out of step.
            ("LvMu", f"{MPE / __import__('ar_gate').FULL_MPE:.2f}")]

    # --- the bound's own ladder, which is what makes over-sizing legible ------------------------
    out += [(f"LvCap{n}", f"{at(cap, k, cpts, '16'):.4f}") for n, k in
            (("Two", "cap_two"), ("Three", "cap_three"), ("Four", "cap_four"), ("Six", "cap_six"),
             ("Ten", "cap_ten"))]

    # --- how the ordering lever decays along the comms ladder -----------------------------------
    g2 = survey(LIFO, "G2 the same on a degraded link", "served_per_step", quiet=True)
    r = ["0", "1", "2", "3", "4"]
    out += [(f"LvJam{t}", f"{at(g2, 'lifo', r, c) - at(g2, 'fifo', r, c):+.4f}")
            for t, c in (("Clear", "0"), ("One", "1"), ("Two", "2"), ("Three", "3"), ("Four", "4"))]

    # --- substitution: the same contrast once the console can refuse ---------------------------
    g3 = survey(LIFO, "G3 substitution: does newest-first still pay once the console can refuse",
                "served_per_step", quiet=True)
    d16 = at(g3, "adm_lifo", pts, "16") - at(g3, "adm_fifo", pts, "16")
    d8 = at(g3, "adm_lifo", pts, "8") - at(g3, "adm_fifo", pts, "8")
    out += [("LvSubSixteen", f"{d16:+.4f}"), ("LvSubEight", f"{d8:+.4f}")]

    # --- the same five levers in ONE allocation, and where the ladder inverts --------------------
    # The numbers above are cross-battery: the four blind arms come from st-lifo and the bound from
    # st-qcap, run days apart. st-capacity puts all five in one job so the comparison is paired the
    # way every other contrast in this paper is, and it carries the C3 rung, which is where the
    # recommendation changes.
    CAP, PC = "st-capacity-9449071.out", ["4", "5", "6", "8", "10", "12", "16"]
    BINS = ["served_per_step", "stale_per_step", "worked_lost_per_step", "worked_late_per_step"]
    for tag, sec in (("Clear", "K1 the five levers, clear link"), ("Jam", "K2 the five levers, C3")):
        try:
            b = {m: survey(CAP, sec, m, quiet=True) for m in BINS}
        except SystemExit:
            continue
        arms = ("fifo", "rand", "lifo", "bound", "admit")
        for a in arms:
            out.append((f"Kp{tag}Srv{a.capitalize()}", f"{at(b[BINS[0]], a, PC, '16'):.4f}"))
        # The sum of the four bins is the console's total effort. It is nearly the same for every
        # arm while delivered service spans a factor of sixty; that contrast is the whole finding
        # and it does not need the utilization metric to state.
        tot = {a: sum(at(b[m], a, PC, "16") for m in BINS) for a in arms}
        srv = {a: at(b[BINS[0]], a, PC, "16") for a in arms}
        out += [(f"Kp{tag}EffortSpread", f"{max(tot.values()) - min(tot.values()):.4f}"),
                (f"Kp{tag}SrvSpread", f"{max(srv.values()) - min(srv.values()):.4f}"),
                (f"Kp{tag}EffortMin", f"{min(tot.values()):.4f}"),
                (f"Kp{tag}EffortMax", f"{max(tot.values()):.4f}"),
                (f"Kp{tag}Ratio", f"{max(srv.values()) / max(min(srv.values()), 1e-9):.0f}")]
        # The bins that are not delivered service, named, because at C3 one of them is not a
        # queueing loss at all and no lever in this paper touches it.
        for a in ("admit", "bound", "fifo"):
            out += [(f"Kp{tag}Lost{a.capitalize()}", f"{at(b['worked_lost_per_step'], a, PC, '16'):.4f}"),
                    (f"Kp{tag}Late{a.capitalize()}", f"{at(b['worked_late_per_step'], a, PC, '16'):.4f}"),
                    (f"Kp{tag}Stale{a.capitalize()}", f"{at(b['stale_per_step'], a, PC, '16'):.4f}")]
        # Fairness, in the unit the harm is in. `starved_frac` is the share of vehicles that asked
        # at least once and were never once answered, so unlike mean backlog it cannot be large for
        # a policy that is doing well, and unlike any ratio over requests it cannot be moved by a
        # policy that changes the asking. Read from `st-capacity2`, which is the job that reached it.
        try:
            st = survey("st-capacity2-9449430.out", sec, "starved_frac", quiet=True)
            for a2 in arms:
                out.append((f"Kp{tag}Starve{a2.capitalize()}",
                            f"{100 * at(st, a2, PC, '16'):.1f}"))
            # The three fair policies are all at the resolution floor, so quote their worst case
            # once rather than three indistinguishable zeros.
            out.append((f"Kp{tag}StarveFair",
                        f"{100 * max(at(st, a2, PC, '16') for a2 in ('lifo', 'bound', 'admit')):.2f}"))
            # The onset is the collapse span showing up in a per-vehicle statistic, with no queue
            # quantity in it at all: zero for every policy up to six assets, and a quarter of the
            # force stranded at eight.
            out += [(f"Kp{tag}StarveOnsetLo", f"{100 * at(st, 'fifo', PC, '6'):.1f}"),
                    (f"Kp{tag}StarveOnsetHi", f"{100 * at(st, 'fifo', PC, '8'):.1f}")]
        except SystemExit:
            pass
        # And the inversion: bound minus admit, which is inside the floor clear and outside it at C3.
        for sp in ("8", "12", "16"):
            out.append((f"Kp{tag}BoundVsAdmit{NAMES[sp]}",
                        f"{at(b[BINS[0]], 'bound', PC, sp) - at(b[BINS[0]], 'admit', PC, sp):+.4f}"))

    dst = ROOT / "report" / "gen" / "lever_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:18s} {v}")


if __name__ == "__main__":
    main()
