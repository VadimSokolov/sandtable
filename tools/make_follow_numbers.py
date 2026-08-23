"""CR-55 and CR-57: what a mission-level model can inherit from a path-error result, measured.

The convoy-control literature optimises PATH ERROR, and the sharpest finding this project's
literature review turned up (Cheung, Rawashdeh and Mohammadi 2022) reports reductions in it for a
behaviour-based controller under jamming. Inheriting that at mission level requires station-keeping
error to predict mission outcome. It does not, and the counterexample is inside a single arm:
disturbing a follower's ESTIMATE of where its station is and MOVING where the station is produce the
same mean error and mission outcomes differing by a factor of two.

    st-follow-9449505.out  F1 (the channel by topology 2x2 across the ladder)
    st-stale-9449524.out   G1 (forced track age, cut-off on and off), G2 (commanded spread)
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_survey import survey  # noqa: E402
from ar_gate import margin, tost  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOL, STL = "st-follow-9449505.out", "st-stale-9449524.out"
F1 = "F1 the ladder, channel x topology"
G1 = "G1 mission outcome against forced track age, reversion on and off"
G2 = "G2 commanded geometry on the same arm that the estimator disturbs"
AS = ["0", "20", "40", "80", "160", "320"]
SP = ["10", "30", "60", "120", "300", "600"]


def main() -> None:
    out: list[tuple[str, str]] = []

    # --- the 2x2 across the ladder, which is where the conjecture died -------------------------
    suc = survey(FOL, F1, "success", quiet=True)
    ste = survey(FOL, F1, "station_err_mean", quiet=True)
    con = survey(FOL, F1, "success", ref="ls", quiet=True)
    out += [("FoLsClear", f"{suc['ls'][0]:.4f}"), ("FoLsSevere", f"{suc['ls'][5]:.4f}"),
            ("FoBcAll", f"{suc['bc'][0]:.4f}"),
            ("FoGapClear", f"{con[('bc', '0')][0]:+.4f}"),
            ("FoGapSevere", f"{con[('bc', '4')][0]:+.4f}"),
            ("FoCells", str(len(con))),
            ("FoStErrClear", f"{ste['ls'][0]:.1f}"), ("FoStErrSevere", f"{ste['ls'][5]:.1f}")]

    # --- the dissociation: one metric, one arm, two mechanisms ---------------------------------
    g1s, g1e = survey(STL, G1, "success", quiet=True), survey(STL, G1, "station_err_mean", quiet=True)
    g2s, g2e = survey(STL, G2, "success", quiet=True), survey(STL, G2, "station_err_mean", quiet=True)
    # The matched pair the argument turns on: nearly equal station error, mission outcomes apart.
    i_est, i_cmd = AS.index("40"), SP.index("300")
    out += [("FoDisEstErr", f"{g1e['noreverts'][i_est]:.0f}"),
            ("FoDisEstSuc", f"{g1s['noreverts'][i_est]:.4f}"),
            ("FoDisCmdErr", f"{g2e['commanded'][i_cmd]:.0f}"),
            ("FoDisCmdSuc", f"{g2s['commanded'][i_cmd]:.4f}"),
            # And the second pair, where the larger error is the harmless one.
            ("FoDisEstBigErr", f"{g1e['noreverts'][AS.index('320')]:.0f}"),
            ("FoDisEstBigSuc", f"{g1s['noreverts'][AS.index('320')]:.4f}"),
            ("FoDisCmdBigErr", f"{g2e['commanded'][SP.index('600')]:.0f}"),
            ("FoDisCmdBigSuc", f"{g2s['commanded'][SP.index('600')]:.4f}")]

    # --- the cut-off, which is what makes the disturbance immaterial ---------------------------
    cut = survey(STL, G1, "success", ref="revert", quiet=True)
    lost = survey(STL, G1, "follow_lost_frac", quiet=True)
    out += [("FoCutClear", f"{g1s['revert'][0]:.4f}"),
            ("FoCutWorst", f"{g1s['revert'][AS.index('320')]:.4f}"),
            ("FoCutSpread", f"{max(g1s['revert']) - min(g1s['revert']):.4f}"),
            ("FoNoCutWorst", f"{g1s['noreverts'][AS.index('320')]:.4f}"),
            ("FoCutGain", f"{-cut[('noreverts', '320')][0]:+.4f}"),
            ("FoCutT", f"{abs(cut[('noreverts', '320')][1]):.2f}"),
            ("FoLostWorst", f"{100 * lost['revert'][AS.index('320')]:.0f}"),
            ("FoLostMid", f"{100 * lost['revert'][AS.index('80')]:.0f}")]

    # --- what the follow stack is worth against what else is on the same table -----------------
    # F3 is the matched-rate comparison: same mean drop rate, i.i.d. against Gilbert-Elliot. The
    # channel statistic a programme reports, packet delivery ratio, is identical by construction;
    # the tracking statistic differs by two orders of magnitude; the mission does not move.
    F3 = "F3 matched mean drop rate, i.i.d. against bursty"
    trk = survey(FOL, F3, "track_err_mean", quiet=True)
    bst = survey(FOL, F3, "success", ref="iid", quiet=True)
    iid5, ge5 = trk["iid"][2], trk["ge240"][2]
    # The weakest one-sided TOST statistic across the six cells, recomputed from the gate rather
    # than read off the contrast tuple, whose fourth field is the block count and not a margin.
    base = survey(FOL, F3, "success", quiet=True)["iid"][2]
    m = margin("success", base)
    worst = min(tost(v[0], v[1], v[3], m)[1] for v in bst.values())
    out += [("FoBurstTrkIid", f"{iid5:.2f}"), ("FoBurstTrkGe", f"{ge5:.1f}"),
            ("FoBurstRatio", f"{ge5 / iid5:.0f}"),
            ("FoBurstSucGap", f"{bst[('ge240', '5')][0]:+.4f}"),
            ("FoBurstCells", str(len(bst))),
            ("FoBurstTost", f"{worst:.1f}")]

    # F4 and F5 put the three levers on one table: what the column is COMMANDED to be, what holds
    # it there, and what the console does. Only two of the three clear the gate.
    F4 = "F4 what column geometry is worth, scripted path"
    F5 = "F5 does the platform lever compose with the console lever"
    scr = survey(FOL, F4, "success", quiet=True)["scripted"]
    lev = survey(FOL, F5, "success", ref="admit_bc", quiet=True)
    levb = survey(FOL, F5, "success", quiet=True)["admit_bc"][0]   # the margin's own base
    out += [("FoSpreadTight", f"{scr[0]:.4f}"), ("FoSpreadWide", f"{scr[-1]:.4f}"),
            ("FoConsoleLever", f"{-lev[('blind_bc', '8')][0]:+.4f}"),
            ("FoConsoleT", f"{abs(lev[('blind_bc', '8')][1]):.2f}"),
            ("FoPlatformLever", f"{lev[('admit_ls', '8')][0]:+.4f}"),
            ("FoPlatformT", f"{abs(lev[('admit_ls', '8')][1]):.2f}"),
            ("FoPlatformTost", f"{tost(*[lev[('admit_ls', '8')][i] for i in (0, 1, 3)],
                                         margin('success', levb))[1]:.2f}")]

    # --- the eight-times-tier test of the one claim that rests on a forced disturbance ---------
    # The cut-off's value was measured against a sawtooth no channel produces, so the claim that it
    # is inert under real channels had to be tested at power rather than asserted. 256 blocks.
    BRG, E1 = "st-bridge-9449639.out", "E1 the bridge, Gilbert-Elliot mean bad run 60 and 240"
    E3 = "E3 the control: Bernoulli, where the cut-off can never fire"
    br = survey(BRG, E1, "success", ref="nocut", quiet=True)
    bb = survey(BRG, E1, "success", quiet=True)["nocut"][0]
    lo = survey(BRG, E1, "follow_lost_frac", quiet=True)
    e3 = survey(BRG, E3, "success", ref="nocut", quiet=True)
    mb = margin("success", bb)
    out += [("FoBrGap", f"{br[('cut', '60')][0]:+.4f}"),
            ("FoBrTost", f"{min(tost(v[0], v[1], v[3], mb)[1] for v in br.values()):.1f}"),
            ("FoBrBlocks", str(br[('cut', '60')][3])),
            ("FoBrLost", f"{100 * lo['cut'][0]:.1f}"),
            ("FoBrCtrl", f"{max(abs(v[0]) for v in e3.values()):.4f}")]

    gen = ROOT / "report" / "gen" / "follow_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {gen} with {len(out)} macros")


if __name__ == "__main__":
    main()
