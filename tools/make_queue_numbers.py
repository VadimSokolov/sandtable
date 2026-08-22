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


def measured_cycle(n_blue: int = 16, seeds: int = 6) -> float:
    """The observed request-to-request cycle deep in collapse, in steps.

    The closed form claims the cycle is `patience + decision_interval + 1`. That trailing step is
    easy to get wrong by inspection, so it is measured against a live run rather than asserted:
    if the implementation's timing ever changes, this number moves and the paper's equation stops
    matching it.
    """
    import numpy as np
    sys.path.insert(0, str(ROOT / "src"))
    from sandtable import c2, sim
    from sandtable.scenario import Scenario, load_scenario

    base = load_scenario(ROOT / "scenarios" / "sc_span_control.json")
    prm = dict(base.params, control_mode="direct", comms_level=0, n_blue=n_blue)
    scn = Scenario(**{**base.__dict__, "params": prm})

    fires: dict = {}
    orig, cur = c2.step, [0]

    def spy(ent, op, comms, sc, k, rng, world=None):
        before = ent.await_until.copy()
        orig(ent, op, comms, sc, k, rng, world)
        for i in np.nonzero((before < 0) & (ent.await_until >= 0))[0]:
            fires.setdefault((cur[0], int(i)), []).append(k)

    c2.step = spy
    try:
        for sd in range(seeds):
            cur[0] = sd
            sim.run_mission(scn, seed=sd)
    finally:
        c2.step = orig
    gaps = [d for ks in fires.values() for d in np.diff(ks)]
    return float(np.mean(gaps))


def fanout_bookings(n_blue: int = 8, seeds: int = 32) -> dict:
    """The three defensible bookings of a request's wait, at the collapsed operating point.

    The implemented statistic counts the whole held period as interaction. Wait in a queue is a
    third category (Cummings and Mitchell's wait-in-queue), so a referee can rebook it two other
    ways from numbers this pipeline already emits. Reporting all three is what makes the negative
    result about fan-out rather than about our choice of denominator.
    """
    import numpy as np
    sys.path.insert(0, str(ROOT / "src"))
    from sandtable import sim
    from sandtable.scenario import Scenario, load_scenario

    base = load_scenario(ROOT / "scenarios" / "sc_span_control.json")
    prm = dict(base.params, control_mode="direct", comms_level=0, n_blue=n_blue,
               blue_behavior="auto", teleop_stop=True)
    scn = Scenario(**{**base.__dict__, "params": prm})
    ms = [sim.run_mission(scn, seed=sd) for sd in range(seeds)]

    impl, classic, util = [], [], []
    for m in ms:
        inter = m["interventions"]
        if inter <= 0 or m["hold_fraction"] <= 0:
            continue
        live = (m["interaction_steps"] + m["neglect_steps"]) * inter    # live vehicle-steps
        busy = m["operator_utilization"] * m["mission_time"]            # console-busy steps
        if busy <= 0:
            continue
        impl.append(m["fan_out"])                                       # wait as interaction
        classic.append(1.0 + (live - m["hold_fraction"] * live) / busy)  # wait in neither
        util.append(live / busy)                                        # wait as neglect
    return {"impl": float(np.mean(impl)), "classic": float(np.mean(classic)),
            "util": float(np.mean(util))}


def served_per_step(n_blue: int = 8, seeds: int = 32) -> dict:
    """Useful service completions per step, for the two slot-freeing policies.

    `operator_goodput` is a RATIO (serviced / requested), so it falls when a policy raises the
    request rate even if the operator is completing more work. Under `refund` and `admit` the
    console is never claimed for a request it cannot finish, so utilization times service rate is
    the rate of completions that actually reach someone. Reporting it stops the goodput ordering
    from being read as an efficiency loss, which it is not.
    """
    import numpy as np
    sys.path.insert(0, str(ROOT / "src"))
    from sandtable import sim
    from sandtable.scenario import Scenario, load_scenario

    base = load_scenario(ROOT / "scenarios" / "sc_span_control.json")
    mu = float(base.params["service_rate"])
    out = {}
    for pol in ("refund", "admit"):
        prm = dict(base.params, control_mode="direct", comms_level=0,
                   n_blue=n_blue, queue_policy=pol)
        scn = Scenario(**{**base.__dict__, "params": prm})
        ms = [sim.run_mission(scn, seed=sd) for sd in range(seeds)]
        out[pol] = float(np.mean([m["operator_utilization"] for m in ms])) * mu
    return out


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def main() -> None:
    scn = json.loads((ROOT / "scenarios" / "sc_span_control.json").read_text())
    p = scn["params"]
    sr, pat, di = float(p["service_rate"]), float(p["patience"]), float(p["decision_interval"])
    # Collapse span on a clean link, one console. The trailing +1 is the step the decision event
    # itself fires on, after the cooldown counter has been decremented `di` times; the measured
    # cycle deep in collapse is 42.84 against this formula's 43.00.
    n_star = (pat + di + 1.0) * sr
    lat_cut = (pat - 1.0 / sr) / 2.0               # latency above which nothing is serviceable

    full = rows("local-full-tier.out")             # published physics, n=8, C0 and C2
    gate = rows("st-gateB-9437187.out")            # teleop gate + staffing curve
    srch = rows("st-searchC-9437188.out")          # fan-out, decoupling, terrain
    thry = rows("st-theory-i-9437166.out")         # the closed-form tests
    dur  = rows("st-duration-9439929.out")         # the deadline robustness check
    ref  = rows("st-refund-9442831.out")           # the three-way policy decomposition

    _book = fanout_bookings()
    _sps = served_per_step()
    wc = rows("st-waitcost-9443162.out")
    sf = rows("st-stopf-9443653.out")
    hy = rows("st-hyst-9443432.out")

    def _did(sec: str, n: str) -> tuple:
        """[stag - burst | retry] - [stag - burst | no retry], paired on the shared block set.

        Staggering the first decision events also perturbs the RNG stream and has a direct effect
        on the mission, so the retry-off arm is the control and only this interaction isolates the
        reliance loop.
        """
        a, b, c, d = (row(hy, sec, arm, n)["vals"] for arm in
                      ("stag_retry", "burst_retry", "stag_off", "burst_off"))
        diff = [(w - x) - (y - z) for w, x, y, z in zip(a, b, c, d)]
        n_ = len(diff)
        mean = sum(diff) / n_
        var = sum((v - mean) ** 2 for v in diff) / (n_ - 1)
        return mean, (mean / ((var / n_) ** 0.5) if var > 0 else float("inf"))

    def _band() -> tuple:
        """The fold band at the published operating point, with the MEASURED healthy abandonment.

        The link-drop floor is zero at C0, which would put the upper edge back on the no-retry
        threshold and predict bistability at six vehicles, where the simulator shows none. The
        healthy abandonment fraction is read off the retry-off arm instead.
        """
        sys.path.insert(0, str(ROOT / "tools"))
        import queue_theory as qt
        a_h = 1.0 - pick(hy, "H2", "burst_off", "6")
        return (qt.fold_band(0.0, sr, pat, di, retry_prob=1.0, retry_backoff=4.0,
                             abandon_healthy=a_h),
                qt.backoff_floor(sr, di, 1.0), a_h)

    _bd = _band()

    def _sf(stop: str, q: str) -> tuple:
        """admit minus refund in one cell of the teleop_stop x q_stall factorial."""
        return paired(row(sf, "F1", f"admit_{stop}", q), row(sf, "F1", f"refund_{stop}", q))

    def _wc(sec: str, q: str) -> tuple:
        """admit minus refund at one wait cost, paired on the shared block set."""
        return paired(row(wc, sec, "admit", q), row(wc, sec, "refund", q))
    m = {
        # --- closed form, computed from the scenario file -------------------------------
        "qNStar":            f"{n_star:.2f}",
        "qNStarTwo":         f"{2 * n_star:.2f}",
        "qNStarThree":       f"{3 * n_star:.2f}",
        "qLatCut":           f"{lat_cut:.2f}",
        "qCyclePredicted":   f"{pat + di + 1.0:.2f}",
        "qCycleMeasured":    f"{measured_cycle():.2f}",
        "qFanFloor":         f"{1.0 + (di + 1.0) / pat:.2f}",
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
        # --- the three-way decomposition: which half of admission control does the work? ------
        "qRefundClear":     pct(pick(ref, "R1 published", "refund", "0")),
        "qRefundJammed":    pct(pick(ref, "R1 published", "refund", "2")),
        "qTeleRefundClear": pct(pick(ref, "R2 teleoperation", "refund", "0")),
        "qRefundShare":      f"{100 * paired(row(ref, 'R1 published', 'refund', '0'), row(ref, 'R1 published', 'blind', '0'))[0] / paired(row(ref, 'R1 published', 'admit', '0'), row(ref, 'R1 published', 'blind', '0'))[0]:.0f}",
        "qTeleRefundShare":  f"{100 * paired(row(ref, 'R2 teleoperation', 'refund', '0'), row(ref, 'R2 teleoperation', 'blind', '0'))[0] / paired(row(ref, 'R2 teleoperation', 'admit', '0'), row(ref, 'R2 teleoperation', 'blind', '0'))[0]:.0f}",
        "qNotifyPub":        f"{100 * paired(row(ref, 'R1 published', 'admit', '0'), row(ref, 'R1 published', 'refund', '0'))[0]:+.1f}",
        "qNotifyPubT":       f"{paired(row(ref, 'R1 published', 'admit', '0'), row(ref, 'R1 published', 'refund', '0'))[1]:.2f}",
        "qNotifyTele":       f"{100 * paired(row(ref, 'R2 teleoperation', 'admit', '0'), row(ref, 'R2 teleoperation', 'refund', '0'))[0]:+.1f}",
        "qNotifyTeleT":      f"{paired(row(ref, 'R2 teleoperation', 'admit', '0'), row(ref, 'R2 teleoperation', 'refund', '0'))[1]:.2f}",
        "qGoodRefundEight":  pct(pick(ref, "R3 goodput", "refund", "8")),
        "qGoodAdmitEight":   pct(pick(ref, "R3 goodput", "admit", "8")),
        "qGoodRefundTwelve": pct(pick(ref, "R3 goodput", "refund", "12")),
        "qGoodAdmitTwelve":  pct(pick(ref, "R3 goodput", "admit", "12")),
        # The wait-cost sweep (st-waitcost). `q_stall` is the control quality of a vehicle
        # awaiting a decision and `q_fallback` = 0.50 that of one that gave up, so the top of the
        # sweep is a setting in which waiting costs nothing.
        # --- CR-17, the fold band -----------------------------------------------------------
        "qBandLo":           f"{_bd[0][0]:.2f}",
        "qBandHi":           f"{_bd[0][1]:.2f}",
        "qBandFloor":        f"{_bd[1]:.2f}",
        "qBandAbandon":      f"{_bd[2]:.3f}",
        "qBandSuccess":      f"{_did('H1', '5')[0]:+.3f}",
        "qBandSuccessT":     f"{_did('H1', '5')[1]:.2f}",
        "qBandGood":         f"{_did('H2', '5')[0]:+.3f}",
        "qBandGoodT":        f"{_did('H2', '5')[1]:.2f}",
        "qBandBelow":        f"{_did('H1', '4')[0]:+.3f}",
        "qBandAbove":        f"{_did('H1', '6')[0]:+.3f}",
        "qBandBlind":        f"{paired(row(hy, 'H3', 'stag', 'blind'), row(hy, 'H3', 'burst', 'blind'))[0]:+.3f}",
        "qBandRefund":       f"{paired(row(hy, 'H3', 'stag', 'refund'), row(hy, 'H3', 'burst', 'refund'))[0]:+.3f}",
        "qBandAdmit":        f"{paired(row(hy, 'H3', 'stag', 'admit'), row(hy, 'H3', 'burst', 'admit'))[0]:+.3f}",
        "qStallLow":         "0.10",
        "qStallPub":         "0.30",
        # The 2x2 factorial: the same contrast in four cells, each gated on its own, so the
        # conditional is read off the cells rather than computed by subtracting between them.
        "qFacStopPub":       f"{100 * _sf('stop', '0.3')[0]:+.1f}",
        "qFacStopPubT":      f"{_sf('stop', '0.3')[1]:.2f}",
        "qFacStopFree":      f"{100 * _sf('stop', '0.5')[0]:+.1f}",
        "qFacStopFreeT":     f"{_sf('stop', '0.5')[1]:.2f}",
        "qFacGoPub":         f"{100 * _sf('go', '0.3')[0]:+.1f}",
        "qFacGoPubT":        f"{_sf('go', '0.3')[1]:.2f}",
        "qFacGoFree":        f"{100 * _sf('go', '0.5')[0]:+.1f}",
        "qFacGoFreeT":       f"{_sf('go', '0.5')[1]:.2f}",
        "qStallFree":        "0.50",
        "qNotifyTeleLow":    f"{100 * _wc('W2', '0.1')[0]:+.1f}",
        "qNotifyTeleFree":   f"{100 * _wc('W2', '0.5')[0]:+.1f}",
        "qNotifyTeleFreeT":  f"{_wc('W2', '0.5')[1]:.2f}",
        "qNotifyPubFree":    f"{100 * _wc('W1', '0.5')[0]:+.1f}",
        "qNotifyPubFreeT":   f"{_wc('W1', '0.5')[1]:.2f}",
        "qServedRefund":     f"{_sps['refund']:.4f}",
        "qServedAdmit":      f"{_sps['admit']:.4f}",
        "qFanClassic": f"{_book['classic']:.2f}",
        "qFanUtil":    f"{_book['util']:.2f}",
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
        # Which half of admission control does the work: freeing the slot, or telling the
        # requester? Reported because the answer is not the same at both request rates.
        ("Freeing the slot alone", "published", "$n{=}8$, C0",
         row(ref, "R1 published", "refund", "0"), row(ref, "R1 published", "blind", "0")),
        ("Freeing the slot alone", "teleoperation", "$n{=}8$, C0",
         row(ref, "R2 teleoperation", "refund", "0"), row(ref, "R2 teleoperation", "blind", "0")),
        ("Notifying, on top of freeing", "published", "$n{=}8$, C0",
         row(ref, "R1 published", "admit", "0"), row(ref, "R1 published", "refund", "0")),
        ("Notifying, on top of freeing", "teleoperation", "$n{=}8$, C0",
         row(ref, "R2 teleoperation", "admit", "0"), row(ref, "R2 teleoperation", "refund", "0")),
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
