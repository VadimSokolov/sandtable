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

    gen = ROOT / "report" / "gen" / "follow_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {gen} with {len(out)} macros")


if __name__ == "__main__":
    main()
