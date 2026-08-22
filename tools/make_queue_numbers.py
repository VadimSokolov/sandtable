"""Generate the operator-queue macros from the autoresearch run logs.

Every number the queue sections of the paper quote is produced here, from the AR_ROW lines the
evaluator wrote, so none of them is retyped. Writes `report/gen/queue_numbers.tex` for LaTeX and
appends a traceable block to `report/results/numbers.txt`.

The two closed-form thresholds are computed from the scenario file rather than read off a run, so
the paper's theory and its simulation cannot silently drift apart.

    python3 tools/make_queue_numbers.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "report" / "data" / "queue"
ROW = re.compile(r"^AR_ROW arm=(\S+) (?:(\S+?)=(\S+) )?mean=([-\d.eE+]+)(?: vals=(\S+))?")


def rows(logname: str) -> list[dict]:
    """Read one run log into (section, arm, sweep value, mean) records."""
    out, major, minor, prev_banner = [], "", "", False
    path = DATA / logname
    if not path.exists():
        sys.exit(f"missing run log {path}; copy it from runlogs/hopper/ first")
    for line in path.read_text(errors="replace").splitlines():
        # A battery writes a `###` banner per experiment and a `## ` banner per metric inside
        # it, so a row's identity is the pair. Matching on either alone picks the wrong rows.
        # A `###` banner may wrap over several lines, so consecutive ones are joined rather
        # than overwriting each other; otherwise only a prediction's last line is searchable.
        if line.startswith(("###", "@@@")):
            text = line.lstrip("#@ ").strip()
            major = f"{major} {text}" if prev_banner else text
            minor, prev_banner = "", True
            continue
        if line.startswith("## "):
            minor, prev_banner = line.lstrip("# ").strip(), False
            continue
        prev_banner = False
        m = ROW.match(line)
        if m:
            arm, _, val, mean, vals = m.groups()
            out.append({"sec": f"{major} | {minor}", "arm": arm, "val": val or "",
                        "mean": float(mean),
                        "vals": [float(v) for v in vals.split(",")] if vals else []})
    return out


def row(rs: list[dict], sec_has: str, arm: str, val: str = "") -> dict:
    """`sec_has` may be "major|minor"; each half is matched as a substring of its own banner,
    because the two banners have unrelated text between them."""
    parts = [q.strip().lower() for q in sec_has.split("|")]
    hits = [r for r in rs
            if all(q in r["sec"].lower().split(" | ")[i] for i, q in enumerate(parts))
            and r["arm"] == arm and (val == "" or r["val"] == val)]
    if not hits:
        sys.exit(f"no row for section~{sec_has!r} arm={arm} val={val!r}")
    return hits[0]


def pick(rs: list[dict], sec_has: str, arm: str, val: str = "") -> float:
    return row(rs, sec_has, arm, val)["mean"]


def paired(hi: dict, lo: dict) -> tuple[float, float, int, int]:
    """Blockwise effect, paired t, blocks won, blocks. The blocks are seed-matched, so the
    per-block difference is the paired quantity the keep/discard gate is defined on."""
    d = [a - b for a, b in zip(hi["vals"], lo["vals"], strict=True)]
    n = len(d)
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1)
    t = mean / ((var / n) ** 0.5) if var > 0 else float("inf")
    return mean, t, sum(1 for x in d if x > 0), n


def argmax(rs: list[dict], sec_has: str, arm: str) -> str:
    """The sweep value at which an arm peaks. Reported optima are read off the run, never
    eyeballed, so a re-run that moves the peak moves the number in the paper with it."""
    parts = [q.strip().lower() for q in sec_has.split("|")]
    hits = [r for r in rs
            if all(q in r["sec"].lower().split(" | ")[i] for i, q in enumerate(parts))
            and r["arm"] == arm]
    if not hits:
        sys.exit(f"no rows for section~{sec_has!r} arm={arm}")
    return max(hits, key=lambda r: r["mean"])["val"]


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def main() -> None:
    scn = json.loads((ROOT / "scenarios" / "sc_span_control.json").read_text())
    p = scn["params"]
    sr, pat, di = float(p["service_rate"]), float(p["patience"]), float(p["decision_interval"])
    n_star = (pat + di) * sr                       # collapse span, clean link, one console
    lat_cut = (pat - 1.0 / sr) / 2.0               # latency above which nothing is serviceable

    full = rows("local-full-tier.out")             # published physics, n=8, C0 and C2
    gate = rows("st-gateB-9437187.out")            # teleop gate + staffing curve
    srch = rows("st-searchC-9437188.out")          # fan-out, decoupling, terrain
    thry = rows("st-theory-i-9437166.out")         # the closed-form tests
    dur  = rows("st-duration-9439929.out")         # the deadline robustness check

    m = {
        # --- closed form, computed from the scenario file -------------------------------
        "qNStar":            f"{n_star:.2f}",
        "qNStarTwo":         f"{2 * n_star:.2f}",
        "qNStarThree":       f"{3 * n_star:.2f}",
        "qLatCut":           f"{lat_cut:.2f}",
        "qServiceRate":      f"{sr:g}",
        "qPatience":         f"{pat:g}",
        "qDecisionInterval": f"{di:g}",
        # --- published physics, n=8, full tier -----------------------------------------
        "qBlindClear":  pct(pick(full, "published physics", "blind", "0")),
        "qBlindJammed": pct(pick(full, "published physics", "blind", "2")),
        "qAdmitClear":  pct(pick(full, "published physics", "admit", "0")),
        "qAdmitJammed": pct(pick(full, "published physics", "admit", "2")),
        # --- teleoperation physics, n=8, full tier -------------------------------------
        "qTeleBlindClear": pct(pick(gate, "G4 FULL TIER", "blind", "0")),
        "qTeleBlindJam":   pct(pick(gate, "G4 FULL TIER", "blind", "2")),
        "qTeleAdmitClear": pct(pick(gate, "G4 FULL TIER", "admit", "0")),
        # --- staffing curve, goodput at C0 ---------------------------------------------
        "qGoodOneSix":    pct(pick(gate, "STAFFING comms_level=0 metric=operator_goodput", "c1_blind", "6")),
        "qGoodOneEight":  pct(pick(gate, "STAFFING comms_level=0 metric=operator_goodput", "c1_blind", "8")),
        "qGoodOneEightAdmit": pct(pick(gate, "STAFFING comms_level=0 metric=operator_goodput", "c1_admit", "8")),
        "qGoodTwoTwelve": pct(pick(gate, "STAFFING comms_level=0 metric=operator_goodput", "c2_blind", "12")),
        "qGoodTwoSixteen": pct(pick(gate, "STAFFING comms_level=0 metric=operator_goodput", "c2_blind", "16")),
        "qGoodThreeSixteen": pct(pick(gate, "STAFFING comms_level=0 metric=operator_goodput", "c3_blind", "16")),
        # --- throughput cliff, vehicles delivered --------------------------------------
        "qArrivedSix":    f"{pick(srch, 'C9 metric=arrived', 'blind', '6'):.2f}",
        "qArrivedEight":  f"{pick(srch, 'C9 metric=arrived', 'blind', '8'):.2f}",
        "qArrivedTwelve": f"{pick(srch, 'C9 metric=arrived', 'blind', '12'):.2f}",
        "qArrivedTwelveAdmit": f"{pick(srch, 'C9 metric=arrived', 'admit', '12'):.2f}",
        # --- the same span at a longer mission window (the deadline caveat) ----------------
        "qDeadline":          f"{scn['duration']:g}",
        "qLongWindow":        f"{json.loads((ROOT / 'experiments' / 'ar_scenarios' / 'sc_span_control_d3600.json').read_text())['duration']:g}",
        "qArrivedTenLong":    f"{pick(dur, 'DURATION metric=arrived scenario=sc_span_control_d3600', 'blind', '10'):.2f}",
        "qArrivedTwelveLong": f"{pick(dur, 'DURATION metric=arrived scenario=sc_span_control_d3600', 'blind', '12'):.2f}",
        # --- latency and loss do not act alike --------------------------------------------
        "qDecoupClean":  pct(pick(srch, "P3 metric=operator_goodput policy=blind", "lat0", "0.0")),
        "qDecoupPeak":   pct(pick(srch, "P3 metric=operator_goodput policy=blind", "lat0", "0.2")),
        "qDecoupHiLoss": pct(pick(srch, "P3 metric=operator_goodput policy=blind", "lat0", "0.55")),
        "qDecoupLatSix": pct(pick(srch, "P3 metric=operator_goodput policy=blind", "lat6", "0.0")),
        "qDecoupLatEight": pct(pick(srch, "P3 metric=operator_goodput policy=blind", "lat8", "0.2")),
        # --- patience moves the latency cut-off -------------------------------------------
        "qPatShortCfour": pct(pick(thry, "P2b patience", "pat20", "4")),
        "qPatMidCfour":   pct(pick(thry, "P2b patience", "pat30", "4")),
        "qPatMidCfive":   pct(pick(thry, "P2b patience", "pat30", "5")),
        "qPatLongCfive":  pct(pick(thry, "P2b patience", "pat45", "5")),
        # --- fan-out is load dependent --------------------------------------------------
        "qFanTwo":    f"{pick(srch, 'C9 metric=fan_out', 'blind', '2'):.2f}",
        "qFanEight":  f"{pick(srch, 'C9 metric=fan_out', 'blind', '8'):.2f}",
        "qFanTen":    f"{pick(srch, 'C9 metric=fan_out', 'blind', '10'):.2f}",
        "qFanTwelve": f"{pick(srch, 'C9 metric=fan_out', 'blind', '12'):.2f}",
        # --- terrain-correlated demand ---------------------------------------------------
        "qTerrainFlatSix": pct(pick(srch, "T1 terrain | metric=operator_goodput", "td0", "6")),
        "qTerrainHardSix": pct(pick(srch, "T1 terrain | metric=operator_goodput", "td2", "6")),
        "qRouteDirectBest": pct(pick(srch, "route_bias | metric=success", "dir_terr", "0.85")),
        "qRouteDirectFull": pct(pick(srch, "route_bias | metric=success", "dir_terr", "1.0")),
        "qRouteSupFull":    pct(pick(srch, "route_bias | metric=success", "sup_terr", "1.0")),
        "qRouteAdmFull":    pct(pick(srch, "route_bias | metric=success", "adm_terr", "1.0")),
        "qRouteFlatFull":   pct(pick(srch, "route_bias | metric=success", "dir_flat", "1.0")),
        "qRouteDirectArgmax": argmax(srch, "route_bias | metric=success", "dir_terr"),
        "qDecoupPeakDrop":  argmax(srch, "P3 metric=operator_goodput policy=blind", "lat0"),
        # --- the closed-form tests --------------------------------------------------------
        "qFastClear":  pct(pick(thry, "P2 metric=operator_goodput", "n8_fast", "0")),
        "qFastJammed": pct(pick(thry, "P2 metric=operator_goodput", "n8_fast", "3")),
        "qSlowClear":  pct(pick(thry, "P2 metric=operator_goodput", "n4_slow", "0")),
        "qSlowJammed": pct(pick(thry, "P2 metric=operator_goodput", "n4_slow", "2")),
    }

    # --- Table: the gated contrasts -------------------------------------------------------
    # Each row is a seed-matched paired comparison at the full tier; the statistics are
    # recomputed here from the per-block values in the log, not copied from the gate output.
    contrasts = [
        ("Admission control helps", "published", "$n{=}8$, C0",
         row(full, "published physics", "admit", "0"), row(full, "published physics", "blind", "0")),
        ("Admission control helps", "teleoperation", "$n{=}8$, C0",
         row(gate, "G4 FULL TIER", "admit", "0"), row(gate, "G4 FULL TIER", "blind", "0")),
        ("Jamming helps a blind queue", "published", "$n{=}8$, C2 vs.\\ C0",
         row(full, "published physics", "blind", "2"), row(full, "published physics", "blind", "0")),
        ("Jamming helps a blind queue", "teleoperation", "$n{=}8$, C2 vs.\\ C0",
         row(gate, "G4 FULL TIER", "blind", "2"), row(gate, "G4 FULL TIER", "blind", "0")),
        ("Admission reverses the sign", "published", "$n{=}8$, C0 vs.\\ C2",
         row(full, "published physics", "admit", "0"), row(full, "published physics", "admit", "2")),
    ]
    lines = ["\\begin{tabular}{llrrrr}", "\\toprule",
             "claim & physics & setting & $\\Delta$ (pp) & $t$ & blocks won \\\\", "\\midrule"]
    for name, phys, setting, hi, lo in contrasts:
        eff, t, wins, n = paired(hi, lo)
        lines.append(f"{name} & {phys} & {setting} & {100 * eff:+.1f} & {t:.1f} & {wins}/{n} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (ROOT / "report" / "gen" / "tab_queue_gate.tex").write_text("\n".join(lines) + "\n")

    # --- Table: the staffing curve ---------------------------------------------------------
    spans = ["2", "4", "6", "8", "10", "12", "16"]
    cols = [("c1_blind", "1, blind"), ("c1_admit", "1, admit"),
            ("c2_blind", "2, blind"), ("c3_blind", "3, blind")]
    staff = ["\\begin{tabular}{rrrrr}", "\\toprule",
             "& \\multicolumn{4}{c}{consoles, queue policy} \\\\", "\\cmidrule(lr){2-5}",
             "assets $n$ & " + " & ".join(h for _, h in cols) + " \\\\", "\\midrule"]
    for sp in spans:
        vals = []
        for arm, _ in cols:
            try:
                vals.append(f"{100 * pick(gate, 'STAFFING comms_level=0 metric=operator_goodput', arm, sp):.1f}")
            except SystemExit:
                vals.append("---")
        staff.append(f"{sp} & " + " & ".join(vals) + " \\\\")
    staff += ["\\bottomrule", "\\end{tabular}"]
    (ROOT / "report" / "gen" / "tab_staffing.tex").write_text("\n".join(staff) + "\n")

    gen = ROOT / "report" / "gen" / "queue_numbers.tex"
    gen.write_text("% AUTO-GENERATED by tools/make_queue_numbers.py -- do not edit.\n"
                   + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in m.items()))

    res = ROOT / "report" / "results" / "numbers.txt"
    body = res.read_text()
    tag = "\n\nOperator-queue numbers (source: tools/make_queue_numbers.py over report/data/queue/*.out)\n"
    body = body.split(tag)[0]
    body += tag + "=" * 78 + "\n"
    body += "".join(f"\\{k} = {v}\n" for k, v in m.items())
    res.write_text(body)
    print(f"wrote {gen} and appended {len(m)} numbers to {res}")


if __name__ == "__main__":
    main()
