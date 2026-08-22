"""Parameter provenance and the MAGIC 2010 retrodiction.

The queue results rest on three numbers: the operator's service rate, the requester's patience, and
the consultation cadence. Until now the paper declared them. This script does two things with them.

First, it converts each to the units the supervisory-control literature reports, which is possible
because the scenario's timestep is one second, and states for each whether a published measurement
fixes it, brackets it, or does not exist. That table is the honest answer to "where do your
parameters come from", and one row of it is empty on purpose.

Second, it runs the one retrodiction the literature makes possible without a new experiment. Olson
et al. (2012) report the winning MAGIC 2010 team's fourteen robots under one task operator, and the
operator's own interaction rate. Those two numbers fix a neglect time, and the fan-out identity and
Equation nstar then predict a capacity, with nothing fitted. The test is whether the predicted
capacity is comfortably above fourteen, since the reported operator was busy but not saturated,
and whether the implied neglect time explains the gap between that fourteen and SandTable's own
collapse span of about six under direct control.

    python3 tools/make_provenance.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCN = ROOT / "scenarios" / "sc_span_control.json"


def main() -> None:
    scn = json.loads(SCN.read_text())
    dt = float(scn["dt"])                       # seconds per step; the whole table depends on it
    par = scn["params"]
    mu = float(par["service_rate"])
    P = float(par["patience"])
    tau = float(par["decision_interval"])

    it = dt / mu                                # interaction time, seconds
    nt = tau * dt                               # neglect time, seconds
    pat = P * dt                                # patience, seconds
    fanout = 1.0 + nt / it
    nstar = mu * (P + tau + 1.0)                # clear link, one console

    # --- MAGIC 2010, Olson et al. 2012, 10.1002/rob.21426 -------------------------------------
    # Reported: a fourteen-robot team under one task operator, who "averaged 4.25 interactions per
    # minute over the entire competition" and "went up to 2 min without interacting". The sensor
    # operator only assisted the global state estimate, so the task operator is the single server.
    magic_n = 14
    magic_rate = 4.25 / 60.0                    # task-operator interactions per second
    magic_nt = magic_n / magic_rate             # seconds between consultations of ONE robot
    magic_fanout = 1.0 + magic_nt / it          # fan-out at SandTable's own interaction time
    magic_nstar = mu * (P + magic_nt / dt + 1.0)
    magic_util = magic_rate * it                # fraction of the operator's time spent interacting
    magic_headroom = magic_n / magic_fanout
    # The retrodiction is conditional on an interaction time MAGIC did not report, so state what
    # their own report of a non-saturated operator implies about it. Fan-out reaches fourteen at
    # 1 + magic_nt/it = 14, so any interaction time above this would have saturated them.
    magic_it_bound = magic_nt / (magic_n - 1.0)

    m = {
        "provStep": f"{dt:.0f}",
        "provIT": f"{it:.2f}",
        "provNT": f"{nt:.0f}",
        "provPatience": f"{pat:.0f}",
        "provFanout": f"{fanout:.1f}",
        "provNstarClear": f"{nstar:.2f}",
        "provMagicN": f"{magic_n}",
        "provMagicRate": "4.25",
        "provMagicNT": f"{magic_nt:.0f}",
        "provMagicFanout": f"{magic_fanout:.0f}",
        "provMagicNstar": f"{magic_nstar:.0f}",
        "provMagicUtil": f"{100 * magic_util:.0f}",
        "provMagicHeadroom": f"{100 * magic_headroom:.0f}",
        "provMagicITBound": f"{magic_it_bound:.0f}",
        "provAutonomyDividend": f"{magic_nt / nt:.0f}",
    }

    # --- Table: where each queue parameter comes from -----------------------------------------
    # One row is deliberately empty. The point of the table is that it is.
    rows = [
        (r"interaction time $1/\mu$", rf"{it:.2f}\,s",
         r"IT, defined and measured \citep{olsen2004fanout,cummings2008predicting}",
         rf"below the {magic_it_bound:.0f}\,s MAGIC's non-saturation implies"),
        (r"consultation cadence $\tau$", rf"{nt:.0f}\,s",
         r"NT, defined and measured \citep{olsen2004fanout}",
         rf"MAGIC's autonomy implies {magic_nt:.0f}\,s, a factor of {magic_nt/nt:.0f}"),
        (r"patience $P$", rf"{pat:.0f}\,s",
         r"\emph{none found}",
         r"the open measurement"),
        (r"round-trip delivery $d$", r"$(1-p_{\text{drop}})^2$",
         r"per rung, Table~\ref{tab:ladder}",
         r"a set parameter, not link data"),
        (r"consoles $c$", "1",
         r"MAGIC fielded two \citep{olson2012magic}",
         r"swept in Table~\ref{tab:staffing}"),
    ]
    tab = [r"\begin{tabular}{@{}p{0.20\textwidth}p{0.11\textwidth}p{0.30\textwidth}p{0.31\textwidth}@{}}",
           r"\toprule",
           r"quantity & \sandtable{} & published measurement & status \\", r"\midrule"]
    tab += [" & ".join(r) + r" \\" for r in rows]
    tab += [r"\bottomrule", r"\end{tabular}"]
    (ROOT / "report" / "gen" / "tab_provenance.tex").write_text("\n".join(tab) + "\n")

    gen = ROOT / "report" / "gen" / "provenance_numbers.tex"
    gen.write_text("% AUTO-GENERATED by tools/make_provenance.py -- do not edit.\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in m.items()))

    res = ROOT / "report" / "results" / "numbers.txt"
    body = res.read_text()
    tag = "\n\nParameter provenance and the MAGIC retrodiction (source: tools/make_provenance.py)\n"
    body = body.split(tag)[0]
    body += tag + "=" * 78 + "\n"
    body += "".join(f"\\{k} = {v}\n" for k, v in m.items())
    res.write_text(body)

    for k, v in m.items():
        print(f"{k:22s} {v}")
    print(f"\nwrote {gen}")


if __name__ == "__main__":
    main()
