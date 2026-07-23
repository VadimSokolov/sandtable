"""Generate the paper's numbers (LaTeX macros) and result tables from the study CSVs.

Single source of truth for every value the manuscript cites. Reads report/data/*.csv (tidy
per-design KPI means from the Hopper studies) and writes:
  report/gen/numbers.tex      -- \\newcommand macros, \\input by main.tex
  report/gen/tab_centerpiece.tex, tab_uc3.tex, tab_uc5.tex, tab_lanchester.tex
  report/results/numbers.txt  -- human-readable audit trail (every macro + provenance)

    PYTHONPATH=src python tools/make_numbers.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("report/data")
GEN = Path("report/gen"); GEN.mkdir(parents=True, exist_ok=True)
RES = Path("report/results"); RES.mkdir(parents=True, exist_ok=True)
NREP = 300

_macros: dict[str, str] = {}
_audit: list[str] = []


def put(name: str, value, note: str) -> None:
    """Register a macro (LaTeX-safe name -> string value) and an audit line."""
    _macros[name] = str(value)
    _audit.append(f"\\{name} = {value}    # {note}")


def _fmt(x, nd=0):
    return f"{x:.{nd}f}"


# --------------------------------------------------------------------------- centerpiece
def centerpiece() -> None:
    d = pd.read_csv(DATA / "centerpiece_direct.csv")
    s = pd.read_csv(DATA / "centerpiece_supervisory.csv")
    m = d.merge(s, on=["comms_level", "n_blue"], suffixes=("_d", "_s"))
    m["delta"] = (m["success_rate_s"] - m["success_rate_d"]) * 100

    def dsucc(mode_df, span, c):
        v = mode_df[(mode_df.n_blue == span) & (mode_df.comms_level == c)]["success_rate"].iloc[0]
        return round(v * 100)

    put("cpDirClearLoSpan", dsucc(d, 2, 0), "direct success%% span1:2 C0")
    put("cpDirSevereLoSpan", dsucc(d, 2, 5), "direct success%% span1:2 C5")
    put("cpDirClearHiSpan", dsucc(d, 8, 0), "direct success%% span1:8 C0")
    put("cpSupClearHiSpan", dsucc(s, 8, 0), "supervisory success%% span1:8 C0")

    # supervisory comms-invariance: spread across comms for span 1:2.
    # Round endpoints first, then take their difference, so the reported spread is consistent
    # with the reported (rounded) endpoints (avoids "71 to 78 = 6.3" rounding drift).
    row = s[s.n_blue == 2].sort_values("comms_level")["success_rate"].values * 100
    lo, hi = round(row.min()), round(row.max())
    put("cpSupLoSpanMin", lo, "supervisory span1:2 min success%% over comms (rounded)")
    put("cpSupLoSpanMax", hi, "supervisory span1:2 max success%% over comms (rounded)")
    put("cpSupLoSpanSpread", hi - lo, "supervisory span1:2 comms spread (pp, rounded endpoints)")

    # crossover C* per span (first comms where delta >= 0)
    stars = {}
    for n in sorted(m.n_blue.unique()):
        sub = m[m.n_blue == n].sort_values("comms_level")
        star = sub[sub.delta >= 0]["comms_level"].min()
        stars[n] = None if pd.isna(star) else int(star)
    put("cpStarLoSpan", stars[2], "crossover C* at span 1:2")
    put("cpStarHiSpan", stars[8], "crossover C* at span 1:8")

    # max supervisory advantage (largest positive delta)
    put("cpDeltaMax", _fmt(m.delta.max()), "max supervisory-minus-direct advantage (pp)")
    put("cpDeltaHiSpanClear",
        _fmt(m[(m.n_blue == 8) & (m.comms_level == 0)]["delta"].iloc[0]),
        "supervisory advantage at span 1:8, C0 (pp)")

    # table: delta grid
    piv = m.pivot(index="n_blue", columns="comms_level", values="delta").sort_index()
    lines = [r"\begin{tabular}{r" + "r" * len(piv.columns) + "}", r"\toprule",
             "span & " + " & ".join(f"C{c}" for c in piv.columns) + r" \\", r"\midrule"]
    for n, r in piv.iterrows():
        cells = " & ".join(f"{v:+.0f}" for v in r.values)
        lines.append(f"1:{n} & {cells}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_centerpiece.tex").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- UC-3
def uc3() -> None:
    f = pd.read_csv(DATA / "uc3_frontier.csv").sort_values("route_bias")
    g = f.groupby("route_bias", as_index=False).mean(numeric_only=True)
    lo, hi = g.iloc[0], g.iloc[-1]
    put("ucThreeSuccFast", round(lo.success_rate * 100), "UC3 success%% route_bias 0 (fast corridor)")
    put("ucThreeSuccCover", round(hi.success_rate * 100), "UC3 success%% route_bias 1 (defilade)")
    put("ucThreeLossFast", _fmt(lo.blue_losses, 1), "UC3 blue losses route_bias 0 (of 8)")
    put("ucThreeLossCover", _fmt(hi.blue_losses, 1), "UC3 blue losses route_bias 1 (of 8)")
    put("ucThreeTimeFast", round(lo.t_obj_success), "UC3 time-to-obj (s) route_bias 0")
    put("ucThreeTimeCover", round(hi.t_obj_success), "UC3 time-to-obj (s) route_bias 1")
    put("ucThreeTempoRatio", _fmt(hi.t_obj_success / lo.t_obj_success, 1), "UC3 tempo ratio cover/fast")

    # table: a subset of route_bias rows
    keep = [0.0, 0.25, 0.5, 0.75, 1.0]
    sub = g[g.route_bias.isin(keep)]
    lines = [r"\begin{tabular}{rrrrr}", r"\toprule",
             r"route bias & success (\%) & blue losses (of 8) & red losses (of 6) & $t_{\text{obj}}$ (s) \\",
             r"\midrule"]
    for _, r in sub.iterrows():
        lines.append(f"{r.route_bias:.2f} & {r.success_rate*100:.0f} & {r.blue_losses:.1f} & "
                     f"{r.red_losses:.1f} & {r.t_obj_success:.0f}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_uc3.tex").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- UC-5
def uc5() -> None:
    path = DATA / "uc5_swarm_jam.csv"
    if not path.exists():
        _audit.append("# UC-5 CSV absent - macros skipped (regen after Hopper)")
        return
    u = pd.read_csv(path)

    def cell(n, c, col):
        r = u[(u.n_uas == n) & (u.comms_level == c)]
        return None if r.empty else r[col].iloc[0]

    nmax = int(u.n_uas.max())
    put("ucFiveSwarmMax", nmax, "UC5 largest swarm size")
    put("ucFiveSuccBlind", round(cell(0, 0, "success_rate") * 100), "UC5 success%% no recon (n=0)")
    put("ucFiveSuccBestClear", round(cell(nmax, 0, "success_rate") * 100), "UC5 success%% max swarm, C0")
    put("ucFiveSuccBestSevere", round(cell(nmax, 5, "success_rate") * 100), "UC5 success%% max swarm, C5")
    put("ucFiveCovBlind", _fmt(cell(0, 0, "detection_coverage"), 2), "UC5 coverage no recon")
    put("ucFiveCovBestClear", _fmt(cell(nmax, 0, "detection_coverage"), 2), "UC5 coverage max swarm C0")
    put("ucFiveCovBestSevere", _fmt(cell(nmax, 5, "detection_coverage"), 2), "UC5 coverage max swarm C5")
    # a mid swarm size (3) to show the operating point + jam collapse
    put("ucFiveSuccMidClear", round(cell(3, 0, "success_rate") * 100), "UC5 success%% n=3 C0")
    put("ucFiveSuccMidSevere", round(cell(3, 5, "success_rate") * 100), "UC5 success%% n=3 C5")

    # table: coverage & success at C0/C3/C5 across swarm size
    show_c = [0, 3, 5]
    ns = sorted(u.n_uas.unique())
    lines = [r"\begin{tabular}{r" + "r" * (2 * len(show_c)) + "}", r"\toprule",
             " & " + " & ".join([r"\multicolumn{2}{c}{" + f"C{c}" + "}" for c in show_c]) + r" \\"]
    cmid = " ".join([f"\\cmidrule(lr){{{2*i+2}-{2*i+3}}}" for i in range(len(show_c))])
    lines.append(cmid)
    lines.append("swarm & " + " & ".join(["cov & succ"] * len(show_c)) + r" \\")
    lines.append(r"\midrule")
    for n in ns:
        cells = []
        for c in show_c:
            cov = cell(n, c, "detection_coverage"); su = cell(n, c, "success_rate")
            cells.append(f"{cov:.2f} & {su*100:.0f}")
        lines.append(f"{n} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_uc5.tex").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- Lanchester cross-check
def lanchester() -> None:
    """Analytic aimed-fire (square-law) attrition vs the sim, on a controlled duel.

    Reads report/data/lanchester.csv if present (produced by tools/lanchester_check.py);
    otherwise skips. Kept here so the table lives with the other generated tables.
    """
    path = DATA / "lanchester.csv"
    if not path.exists():
        _audit.append("# Lanchester CSV absent - table skipped (run tools/lanchester_check.py)")
        return
    L = pd.read_csv(path)
    lines = [r"\begin{tabular}{rrrrr}", r"\toprule",
             r"$B_0$ & $R_0$ & sim $B$ surv. & Lanchester $B$ & rel. err. \\", r"\midrule"]
    for _, r in L.iterrows():
        lines.append(f"{int(r.B0)} & {int(r.R0)} & {r.sim_surv:.2f} & {r.lanch_surv:.2f} & "
                     f"{r.rel_err*100:.1f}\\%" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_lanchester.tex").write_text("\n".join(lines) + "\n")
    put("lanchMaxErr", _fmt(L.rel_err.abs().max() * 100, 1), "max Lanchester relative error (%)")


def belief() -> None:
    """Belief/track-layer demo (UC-3): baseline seen-model vs the opt-in belief model under decoys
    and jamming. Reads report/data/belief_demo.csv (from tools/make_belief_numbers.py); else skips.
    """
    path = DATA / "belief_demo.csv"
    if not path.exists():
        _audit.append("# belief_demo CSV absent - macros skipped (run tools/make_belief_numbers.py)")
        return
    B = pd.read_csv(path).set_index("condition")
    put("beliefNRep", int(B["n_rep"].iloc[0]), "belief-demo replications")
    put("beliefBaseLoss", _fmt(B.loc["baseline", "blue_losses"], 1),
        "UC3 mean blue losses, baseline seen-bit model")
    put("beliefCleanLoss", _fmt(B.loc["clear", "blue_losses"], 1),
        "UC3 mean blue losses, belief tracks, clear comms")
    put("beliefDecoyLoss", _fmt(B.loc["decoy", "blue_losses"], 1),
        "UC3 mean blue losses, belief tracks + decoys (spoofing)")
    put("beliefJamLoss", _fmt(B.loc["jam", "blue_losses"], 1),
        "UC3 mean blue losses, belief tracks, jammed C5 (stale)")


def killweb() -> None:
    """Kill-web mechanics: the suppression sweep, the munitions sweep, and the UC-7 layered case.
    Reads report/data/{suppression_sweep,munitions_sweep,uc7_layers}.csv (from
    tools/make_killweb_numbers.py). Each block is skipped independently if its CSV is absent.
    """
    sp = DATA / "suppression_sweep.csv"
    if sp.exists():
        S = pd.read_csv(sp).sort_values("supp_fire")
        lo, hi = S.iloc[0], S.iloc[-1]
        put("killwebNRep", int(S["n_rep"].iloc[0]), "kill-web study replications")
        put("suppBaseLoss", _fmt(lo.blue_losses, 1), "UC3 blue losses, suppression off (supp_fire 0)")
        put("suppMaxLoss", _fmt(hi.blue_losses, 1), "UC3 blue losses, full suppression (supp_fire 1)")
        put("suppBaseSucc", round(lo.success * 100), "UC3 success%% suppression off")
        put("suppMaxSucc", round(hi.success * 100), "UC3 success%% full suppression")
    else:
        _audit.append("# suppression_sweep CSV absent - macros skipped (run make_killweb_numbers.py)")

    mp = DATA / "munitions_sweep.csv"
    if mp.exists():
        M = pd.read_csv(mp).sort_values("ammo_load")
        plenty = M.iloc[-1]                                   # ammo_load ~ unlimited (fixed-Pk limit)
        s4 = M[M.ammo_load == 4].iloc[0] if (M.ammo_load == 4).any() else M.iloc[0]
        put("muniScarceAmmo", int(s4.ammo_load), "defender basic load, scarce reference")
        put("muniScarceLoss", _fmt(s4.blue_losses, 1), "UC3 blue losses, scarce defender ammo")
        put("muniScarceSucc", round(s4.success * 100), "UC3 success%% scarce defender ammo")
        put("muniPlentyLoss", _fmt(plenty.blue_losses, 1), "UC3 blue losses, unlimited defender ammo")
        put("muniPlentySucc", round(plenty.success * 100), "UC3 success%% unlimited defender ammo")
    else:
        _audit.append("# munitions_sweep CSV absent - macros skipped (run make_killweb_numbers.py)")

    up = DATA / "uc7_layers.csv"
    if up.exists():
        U = pd.read_csv(up).set_index("layer")
        put("ucSevenNRep", int(U["n_rep"].iloc[0]), "UC7 layered study replications")
        for layer, macro in [("truth", "ucSevenTruthLoss"), ("belief", "ucSevenBeliefLoss"),
                             ("jam", "ucSevenJamLoss"), ("decoys", "ucSevenDecoyLoss"),
                             ("suppress", "ucSevenSuppLoss"), ("full", "ucSevenFullLoss")]:
            put(macro, _fmt(U.loc[layer, "blue_losses"], 1), f"UC7 blue losses, layer={layer}")
        put("ucSevenTruthSucc", round(U.loc["truth", "success"] * 100), "UC7 success%% truth baseline")
        put("ucSevenFullSucc", round(U.loc["full", "success"] * 100), "UC7 success%% full contested")

        label = {"truth": "truth (fires vs truth)", "belief": "+ belief tracks", "jam": "+ jamming",
                 "decoys": "+ decoys (spoofing)", "suppress": "+ suppression",
                 "full": "+ munitions (full)"}
        Uo = pd.read_csv(up).sort_values("order")
        lines = [r"\begin{tabular}{lrrr}", r"\toprule",
                 r"configuration & blue losses (of 8) & red losses (of 8) & success (\%) \\",
                 r"\midrule"]
        for _, r in Uo.iterrows():
            lines.append(f"{label[r.layer]} & {r.blue_losses:.1f} & {r.red_losses:.1f} & "
                         f"{r.success*100:.0f}" + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (GEN / "tab_killweb.tex").write_text("\n".join(lines) + "\n")
    else:
        _audit.append("# uc7_layers CSV absent - macros skipped (run make_killweb_numbers.py)")


def personality() -> None:
    """Personality-movement demo (UC-3): the scripted route planner vs the opt-in propensity mode
    (ISAAC/EINSTein/MANA weighted attraction-repulsion). Reads report/data/personality_sweep.csv
    (from tools/make_personality_numbers.py); else skips. Shows that enemy repulsion produces an
    emergent threat-avoiding maneuver that beats the hand-scripted covered route.
    """
    path = DATA / "personality_sweep.csv"
    if not path.exists():
        _audit.append("# personality_sweep CSV absent - macros skipped (run make_personality_numbers.py)")
        return
    P = pd.read_csv(path)

    def row(mode, knob):
        r = P[(P["mode"] == mode) & (np.isclose(P["knob"], knob))]
        return r.iloc[0]

    put("personalityNRep", int(P["n_rep"].iloc[0]), "personality-demo replications")
    # scripted planner endpoints (the baseline the emergent maneuver is judged against)
    sf, sc = row("scripted", 0.0), row("scripted", 1.0)
    put("persScriptFastLoss", _fmt(sf.blue_losses, 1), "UC3 blue losses, scripted fast corridor")
    put("persScriptFastSucc", round(sf.success * 100), "UC3 success%% scripted fast corridor")
    put("persScriptCoverLoss", _fmt(sc.blue_losses, 1), "UC3 blue losses, scripted covered route (best scripted)")
    put("persScriptCoverSucc", round(sc.success * 100), "UC3 success%% scripted covered route")
    put("persScriptCoverTime", round(sc.time), "UC3 time-to-obj (s), scripted covered route")
    # personality mode: off (w_enemy=0) reproduces the fast corridor; on (w_enemy=1) is emergent maneuver
    p0, p1, p2 = row("personality", 0.0), row("personality", 1.0), row("personality", 2.0)
    put("persStraightLoss", _fmt(p0.blue_losses, 1), "UC3 blue losses, personality w_enemy=0 (drives straight)")
    put("persStraightSucc", round(p0.success * 100), "UC3 success%% personality w_enemy=0")
    put("persAvoidLoss", _fmt(p1.blue_losses, 1), "UC3 blue losses, personality w_enemy=1 (emergent maneuver)")
    put("persAvoidSucc", round(p1.success * 100), "UC3 success%% personality w_enemy=1")
    put("persAvoidTime", round(p1.time), "UC3 time-to-obj (s), personality w_enemy=1")
    put("persOverTime", round(p2.time), "UC3 time-to-obj (s), personality w_enemy=2 (over-caution)")
    put("persTimeSavePct", round((sc.time - p1.time) / sc.time * 100),
        "emergent maneuver time saving vs scripted covered route (%)")

    label = {("scripted", 0.0): r"scripted & fast corridor",
             ("scripted", 1.0): r"scripted & covered route",
             ("personality", 0.0): r"personality & $w_e{=}0$",
             ("personality", 0.5): r"personality & $w_e{=}0.5$",
             ("personality", 1.0): r"personality & $w_e{=}1$",
             ("personality", 2.0): r"personality & $w_e{=}2$"}
    lines = [r"\begin{tabular}{llrrr}", r"\toprule",
             r"movement & setting & blue losses (of 8) & success (\%) & $t_{\text{obj}}$ (s) \\",
             r"\midrule"]
    for _, r in P.iterrows():
        lab = label[(r["mode"], round(float(r["knob"]), 2))]
        lines.append(f"{lab} & {r.blue_losses:.1f} & {r.success*100:.0f} & {r.time:.0f}" + r" \\")
        if r["mode"] == "scripted" and np.isclose(r["knob"], 1.0):
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_personality.tex").write_text("\n".join(lines) + "\n")


def bayes_te() -> None:
    """Bayesian test-and-evaluation demo: credible intervals vs frequentist, the decision chart and
    optimal stopping, the paired contrast, and SandTable as a discounted prior for high-fidelity
    testing. Reads report/data/bayes_te_*.csv (from tools/make_bayes_te_numbers.py); else skips.
    """
    ip = DATA / "bayes_te_intervals.csv"
    if not ip.exists():
        _audit.append("# bayes_te CSVs absent - macros skipped (run make_bayes_te_numbers.py)")
        return
    I = pd.read_csv(ip).set_index("label")
    full, small = I.loc["full"], I.loc["small"]
    put("bteN", int(full.n), "Bayesian T&E headline replications")
    put("bteHits", int(full.h), "Bayesian T&E headline successes")
    put("bteBetaLo", _fmt(full.beta_lo, 2), "headline Beta 95%% CrI lower")
    put("bteBetaHi", _fmt(full.beta_hi, 2), "headline Beta 95%% CrI upper")
    put("bteWaldLo", _fmt(full.wald_lo, 2), "headline Wald 95%% CI lower")
    put("bteWaldHi", _fmt(full.wald_hi, 2), "headline Wald 95%% CI upper")
    put("bteComplyEighty", _fmt(full.p_ge_80, 2), "P(success>=0.80 | data)")
    put("bteComplySixty", _fmt(full.p_ge_60, 2), "P(success>=0.60 | data)")
    put("bteSmallN", int(small.n), "small-sample n")
    put("bteSmallHits", int(small.h), "small-sample successes")
    put("bteWaldHiSmall", _fmt(small.wald_hi, 2), "small-sample Wald upper (runs past 1.0)")
    put("bteBetaHiSmall", _fmt(small.beta_hi, 2), "small-sample Beta upper (honest)")

    # B. decision chart + optimal stopping
    S = pd.read_csv(DATA / "bayes_te_stopping.csv")
    P = pd.read_csv(DATA / "bayes_te_paths.csv")
    put("bteMaxRep", int(P.k.max() + 1), "fixed testing budget (reps) the stopping rule undercuts")
    cheap = S[S.cost == S.cost.min()].set_index("design")
    dear = S[S.cost == S.cost.max()].set_index("design")
    put("bteStopAccept", int(cheap.loc["compliant", "n_used"]), "reps to accept the compliant design")
    put("bteStopBorder", int(cheap.loc["borderline", "n_used"]), "reps to decide the borderline design")
    put("bteStopReject", int(cheap.loc["noncompliant", "n_used"]), "reps to reject the bad design")
    put("bteBorderDecision", str(cheap.loc["borderline", "decision"]), "borderline design verdict")
    put("bteContinueCheap", int(cheap.iloc[0]["continue_states"]), "continue-test states, low cost")
    put("bteContinueDear", int(dear.iloc[0]["continue_states"]), "continue-test states, high cost")

    # C. paired contrast (direct vs supervisory) + the CRN finding
    C = pd.read_csv(DATA / "bayes_te_contrast.csv").iloc[0]
    put("bteContrastMean", _fmt(C.delta_mean, 2), "posterior mean success-rate advantage (super-direct)")
    put("bteContrastLo", _fmt(C.delta_lo, 2), "advantage 95%% CrI lower")
    put("bteContrastHi", _fmt(C.delta_hi, 2), "advantage 95%% CrI upper")
    put("bteProbSupBetter", _fmt(C.p_b_gt_a, 2), "P(supervisory better than direct | data)")
    put("bteCrnCorr", _fmt(C.crn_corr, 2), "CRN correlation of paired outcomes (near zero)")

    # D. M&S as a discounted prior for high-fidelity testing
    D = pd.read_csv(DATA / "bayes_te_prior.csv").iloc[0]
    put("bteLam", _fmt(D.lam, 2), "M&S discount factor")
    put("bteLamHalf", _fmt(D.lam_half, 2), "lighter M&S discount factor")
    put("bteSimN", int(D.n_sim), "cheap M&S replications forming the prior")
    put("bteRunsInformed", _fmt(D.runs_informed, 1), "expected high-fidelity runs to confidence, M&S prior")
    put("bteRunsUninformed", _fmt(D.runs_uninformed, 1), "expected high-fidelity runs to confidence, no prior")
    put("bteRunsSaved", _fmt(D.runs_saved, 0), "expensive runs saved by the M&S prior")
    put("bteConflictP", _fmt(D.conflict_p, 2), "conflicting high-fidelity truth (M&S prior is wrong)")
    put("bteOverrideMain", _fmt(D.override_main, 0), "high-fidelity runs to overturn a wrong prior, main lambda")
    put("bteOverrideHalf", _fmt(D.override_half, 0), "high-fidelity runs to overturn a wrong prior, lighter lambda")

    # table: interval comparison (Bayesian vs frequentist), full and small sample
    def _iv(r):
        return (f"[{r.beta_lo:.2f}, {r.beta_hi:.2f}] & [{r.wald_lo:.2f}, {r.wald_hi:.2f}] & "
                f"[{r.wilson_lo:.2f}, {r.wilson_hi:.2f}]")
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"sample & Bayesian 95\% CrI & Wald 95\% CI & Wilson 95\% CI & $P(p\!\ge\!0.8)$ \\",
             r"\midrule",
             f"$N={int(full.n)}$ ({int(full.h)} succ) & {_iv(full)} & {full.p_ge_80:.2f}" + r" \\",
             f"$N={int(small.n)}$ ({int(small.h)} succ) & {_iv(small)} & {small.p_ge_80:.2f}" + r" \\",
             r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_bayes_te.tex").write_text("\n".join(lines) + "\n")


def drone() -> None:
    """Drone-war increment: EW-immune command link (M1) and counter-UAS swarm + cost-exchange (M2/M3).
    Reads report/data/{drone_fiber_link,drone_cuas_swarm}.csv (from tools/make_drone_numbers.py).
    Each block is skipped independently if its CSV is absent.
    """
    fp = DATA / "drone_fiber_link.csv"
    if fp.exists():
        F = pd.read_csv(fp)
        put("droneNRep", int(F["n_rep"].iloc[0]), "drone-increment study replications")
        piv = F.pivot(index="comms_level", columns="link", values="success")
        clear = piv.loc[0]
        put("fiberClearJam", round(clear["jammable"] * 100), "direct-control success%% clear comms, jammable link")
        put("fiberClearImm", round(clear["immune"] * 100), "direct-control success%% clear comms, immune link")
        gain = (piv["immune"] - piv["jammable"])
        lvl = int(gain.idxmax())                              # comms level where the immune link helps most
        hi = piv.loc[lvl]
        put("fiberHeavyLabel", f"C{lvl}", "comms level of the maximal immune-link advantage")
        hj, hi_imm = round(hi["jammable"] * 100), round(hi["immune"] * 100)
        put("fiberHeavyJam", hj, "direct-control success%% heavy jamming, jammable link")
        put("fiberHeavyImm", hi_imm, "direct-control success%% heavy jamming, immune link")
        put("fiberHeavyGain", hi_imm - hj, "immune-link success advantage (pp) at heavy jamming")
    else:
        _audit.append("# drone_fiber_link CSV absent - macros skipped (run make_drone_numbers.py)")

    cp = DATA / "drone_cuas_swarm.csv"
    if cp.exists():
        C = pd.read_csv(cp)
        off = C[C.cuas == "off"].set_index("n_uas").sort_index()
        on = C[C.cuas == "on"].set_index("n_uas").sort_index()
        lo_n, hi_n = int(on.index.min()), int(on.index.max())
        put("cuasOffSmallSucc", round(off.loc[lo_n, "success"] * 100), "UC5 unopposed success%% smallest swarm")
        put("cuasOffLargeSucc", round(off.loc[hi_n, "success"] * 100), "UC5 unopposed success%% largest swarm")
        pk = int(on["success"].idxmax())                     # interior optimum swarm size under counter-UAS
        peak_succ, large_succ = round(on.loc[pk, "success"] * 100), round(on.loc[hi_n, "success"] * 100)
        put("cuasPeakSize", pk, "counter-UAS survivable-swarm optimum size")
        put("cuasOnPeakSucc", peak_succ, "UC5 counter-UAS success%% at the optimum")
        put("cuasOnSmallSucc", round(on.loc[lo_n, "success"] * 100), "UC5 counter-UAS success%% smallest swarm")
        put("cuasOnLargeSucc", large_succ, "UC5 counter-UAS success%% largest swarm")
        put("cuasOnDrop", peak_succ - large_succ, "success drop (pp) from the optimum to the oversized swarm")
        put("cuasLargeAirLoss", _fmt(on.loc[hi_n, "air_losses"], 1),
            "recon drones lost by the oversized swarm under counter-UAS")
        cpk = int(on["cost_exchange"].idxmax())
        put("cuasCostPeakSize", cpk, "swarm size maximizing the cost-exchange under counter-UAS")
        put("cuasCostPeak", _fmt(on.loc[cpk, "cost_exchange"], 2), "peak cost-exchange under counter-UAS")
        put("cuasCostLarge", _fmt(on.loc[hi_n, "cost_exchange"], 2), "cost-exchange of the oversized swarm")

        lines = [r"\begin{tabular}{rrrrrr}", r"\toprule",
                 r"swarm & \multicolumn{2}{c}{success (\%)} & coverage & drones & cost \\",
                 r"size & unopposed & counter-UAS & (C-UAS) & lost & exchange \\",
                 r"\midrule"]
        for n in on.index:
            lines.append(f"{n} & {off.loc[n,'success']*100:.0f} & {on.loc[n,'success']*100:.0f} & "
                         f"{on.loc[n,'coverage']:.2f} & {on.loc[n,'air_losses']:.1f} & "
                         f"{on.loc[n,'cost_exchange']:.2f}" + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (GEN / "tab_drone.tex").write_text("\n".join(lines) + "\n")
    else:
        _audit.append("# drone_cuas_swarm CSV absent - macros skipped (run make_drone_numbers.py)")


def main() -> None:
    centerpiece()
    uc3()
    uc5()
    lanchester()
    belief()
    killweb()
    personality()
    bayes_te()
    drone()
    put("nRep", NREP, "Monte-Carlo replications per design")
    tex = "% AUTO-GENERATED by tools/make_numbers.py -- do not edit.\n"
    tex += "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in _macros.items()) + "\n"
    (GEN / "numbers.tex").write_text(tex)
    (RES / "numbers.txt").write_text(
        "SandTable paper -- generated numbers (source: tools/make_numbers.py over report/data/*.csv)\n"
        + "=" * 78 + "\n" + "\n".join(_audit) + "\n")
    print(f"wrote {GEN/'numbers.tex'} ({len(_macros)} macros)")
    print(f"wrote tables -> {GEN}")
    print(f"wrote audit  -> {RES/'numbers.txt'}")


if __name__ == "__main__":
    main()
