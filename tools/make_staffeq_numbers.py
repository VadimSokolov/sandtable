"""CR-38: what one line of console software is worth in operators, on metrics no policy inflates.

The staffing table is the most sponsor-legible object in this paper and it was built on
`operator_goodput`, which the admission arm inflates by up to a third and the extra-console arm does
not inflate at all. That is the exact configuration CR-31 showed produces a spurious gap: an arm
whose denominator moved against an arm whose denominator did not.

Re-read on the delivered rate and on mission success, the equivalence survives and gets a number
rather than an impression. It also splits: the software is worth less in throughput than in
outcomes, and a program office buys the second.

The battery pays for one more thing it was not registered for. It runs one, two and three consoles
across the same span sweep, and Equation nstar says the collapse span scales linearly in consoles.
Three arms, three collapse brackets, one prediction with no free parameters.

Source: hopper/batteries/staffeq.sh, job 9446740.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import FULL_FRAC, FULL_MPE, FULL_T, margin, rate_floor, tost  # noqa: E402
from ar_read import find, load  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402

LOG = "st-staffeq-9446740.out"
WORDS = {"2": "NTwo", "4": "NFour", "6": "NSix", "8": "NEight",
         "10": "NTen", "12": "NTwelve", "16": "NSixteen"}
# Equation (nstar) at the published operating point: c (P + tau + 1) mu / (1 - p_drop)^2 with
# P = 20, tau = 22, mu = 0.15 and a clear link. One console is 6.45.
NSTAR_ONE = (20 + 22 + 1) * 0.15


def mean(v: list[float]) -> float:
    return sum(v) / len(v)


def main() -> None:
    p = find(LOG)
    m: dict[str, str] = {}
    for sec, tag in (("G0", "Clear"), ("G3", "Jam")):
        srv = load(p, sec, "served_per_step")
        suc = load(p, sec, "success")
        spans = sorted({k for a, k in srv if a == "c1_blind"}, key=float)
        m[f"se{tag}Blocks"] = str(len(srv[("c1_blind", spans[0])]))
        # The equivalence, as a fraction of the way from one blind console to two.
        for metric, d, mtag in (("served", srv, "Srv"), ("success", suc, "Suc")):
            for n in ("8", "10", "12"):
                if ("c2_blind", n) not in d:
                    continue
                lo, mid, hi = (mean(d[(f"c1_{a}", n)]) if a != "c2" else mean(d[("c2_blind", n)])
                               for a in ("blind", "admit", "c2"))
                w = WORDS[n]
                m[f"se{tag}{mtag}{w}Share"] = f"{100 * (mid - lo) / (hi - lo):.0f}"
                m[f"se{tag}{mtag}{w}One"] = f"{lo:.4f}" if metric == "served" else f"{100*lo:.1f}"
                m[f"se{tag}{mtag}{w}Admit"] = f"{mid:.4f}" if metric == "served" else f"{100*mid:.1f}"
                m[f"se{tag}{mtag}{w}Two"] = f"{hi:.4f}" if metric == "served" else f"{100*hi:.1f}"
        # The stack against a second console, on the metric a program buys.
        for n in ("10", "12", "16"):
            if ("c2_blind", n) not in suc:
                continue
            e, t, w2, N = paired({"vals": suc[("c1_aimd", n)]}, {"vals": suc[("c2_blind", n)]})
            base = mean(suc[("c2_blind", n)])
            m[f"se{tag}Stack{WORDS[n]}"] = f"{100 * e:+.1f}"
            m[f"se{tag}Stack{WORDS[n]}T"] = f"{t:+.2f}"
            m[f"se{tag}Stack{WORDS[n]}Gate"] = ("gated" if abs(t) > FULL_T and w2 >= FULL_FRAC * N
                                                and abs(e) > FULL_MPE * base else "null")
            # A gate that says "null" has established nothing, and in a simulator, where we choose
            # the replication count, failing to separate two arms gets EASIER the more carelessly
            # the run is done. The affirmative form is the only one that is stable under a budget we
            # control, so the same contrast is also read as an equivalence against the same margin
            # the gate uses to call a difference material. That margin predates every contrast here.
            marg = margin("success", base)
            eq, stat = tost(e, t, N, marg)
            m[f"se{tag}Stack{WORDS[n]}Eq"] = "equivalent" if eq else "inconclusive"
            m[f"se{tag}Stack{WORDS[n]}EqT"] = f"{stat:.2f}" if stat != float("inf") else "$\\infty$"
            m[f"se{tag}Stack{WORDS[n]}Marg"] = f"{100 * marg:.1f}"
        # Two different answers to two different questions: the rate rule serves less and wins more.
        for n in ("8", "12"):
            for metric, d, mtag, fl in (("served", srv, "Srv", rate_floor()),
                                        ("success", suc, "Suc", None)):
                e, t, w2, N = paired({"vals": d[(f"c1_aimd", n)]}, {"vals": d[("c1_admit", n)]})
                base = mean(d[("c1_admit", n)])
                ok = (abs(t) > FULL_T and w2 >= FULL_FRAC * N
                      and abs(e) > (fl if fl else FULL_MPE * base))
                m[f"se{tag}Ai{mtag}{WORDS[n]}"] = f"{100 * e / base:+.1f}"
                m[f"se{tag}Ai{mtag}{WORDS[n]}T"] = f"{t:+.1f}"
                m[f"se{tag}Ai{mtag}{WORDS[n]}Gate"] = "gated" if ok else "null"

    # The staffing curve itself, on the metric with no denominator. The manuscript reads these
    # brackets on `operator_goodput`, which is the contaminated metric, and the point of re-reading
    # them here is that the brackets do not move: the c-scaling of Equation nstar is not an artifact
    # of the ratio.
    srv0 = load(p, "G0", "served_per_step")
    for arm, c, ns in (("c1_blind", "One", ("6", "8")), ("c2_blind", "Two", ("12", "16")),
                       ("c3_blind", "Three", ("16",))):
        for n in ns:
            if (arm, n) in srv0:
                m[f"seSrv{c}{WORDS[n]}"] = f"{mean(srv0[(arm, n)]):.4f}"
    m["seSrvOneNEightAdmit"] = f"{mean(srv0[('c1_admit', '8')]):.4f}"

    # The c-scaling of the closed form, read off the blind arms on the clear link. The collapse
    # bracket is the pair of adjacent spans across which delivered service falls by more than half.
    srv = load(p, "G0", "served_per_step")
    spans = sorted({k for a, k in srv if a == "c1_blind"}, key=float)
    for c, arm in ((1, "c1_blind"), (2, "c2_blind"), (3, "c3_blind")):
        seq = [(n, mean(srv[(arm, n)])) for n in spans if (arm, n) in srv]
        peak = max(v for _, v in seq)
        drop = next((i for i in range(1, len(seq)) if seq[i][1] < 0.5 * peak and seq[i - 1][1] >= 0.5 * peak), None)
        tag = ("One", "Two", "Three")[c - 1]
        m[f"seNstar{tag}"] = f"{c * NSTAR_ONE:.1f}"
        if drop is None:
            m[f"seBracket{tag}"] = "none"
            m[f"seBracket{tag}Hi"] = spans[-1]
        else:
            m[f"seBracket{tag}"] = f"{seq[drop - 1][0]} and {seq[drop][0]}"
            m[f"seBracket{tag}Lo"] = seq[drop - 1][0]
            m[f"seBracket{tag}Hi"] = seq[drop][0]

    gen = ROOT / "report" / "gen" / "staffeq_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write(f"\n\nStaffing equivalence (source: tools/make_staffeq_numbers.py over {LOG})\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen}")
    for n in ("NEight", "NTen", "NTwelve"):
        print(f"  {n}: admit is {m.get(f'seClearSrv{n}Share')}% of a second console on service, "
              f"{m.get(f'seClearSuc{n}Share')}% on success")
    for n in ("NTen", "NTwelve", "NSixteen"):
        if f"seClearStack{n}" in m:
            print(f"  stack vs two blind consoles at {n}: {m[f'seClearStack{n}']} points, "
                  f"t={m[f'seClearStack{n}T']}, {m[f'seClearStack{n}Gate']}")
    for tag in ("One", "Two", "Three"):
        print(f"  {tag} console(s): nstar {m[f'seNstar{tag}']}, collapse between {m[f'seBracket{tag}']}"
              if m[f"seBracket{tag}"] != "none"
              else f"  {tag} console(s): nstar {m[f'seNstar{tag}']}, no collapse by {m[f'seBracket{tag}Hi']}")


if __name__ == "__main__":
    main()
