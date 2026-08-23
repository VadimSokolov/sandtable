"""Lewis et al. 2010, transcribed once from the source PDF and never retyped into prose.

The numbers below are read off the Results section of the author-hosted PDF (recovered from the
Internet Archive; the Pittsburgh URL is dead). They are external data, not a run of this simulator,
so there is no log to parse and the transcription IS the provenance. Keeping them here rather than
inline in the manuscript means the derived quantities, the coverage ratio and the yield ratio, are
computed rather than asserted, and a transcription error shows up in one place.

Source: doi 10.1177/0018720810366859, Human Factors 52(2):225-233, Results.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_queue_numbers import ROOT  # noqa: E402

# robots -> (victims found, sd) in each condition
FULL = {4: (4.80, 1.57), 8: (7.06, 2.25), 12: (4.73, 1.98)}
PERC = {4: (6.93, 1.22), 8: (8.20, 0.86), 12: (8.33, 0.62)}
# robots -> (area explored, sd), full task and exploration-only
AREA_FULL = {4: (129.2, 48.48), 8: (327.6, 55.4), 12: (285.8, 60.0)}
AREA_EXPL = {4: (173.8, 52.2), 8: (348.9, 73.9), 12: (377.8, 48.0)}

WORD = {4: "Four", 8: "Eight", 12: "Twelve"}


def main() -> None:
    m: dict[str, str] = {}
    for n, w in WORD.items():
        m[f"lwFull{w}"] = f"{FULL[n][0]:.2f}"
        m[f"lwPerc{w}"] = f"{PERC[n][0]:.2f}"
        m[f"lwAreaFull{w}"] = f"{AREA_FULL[n][0]:.1f}"
        m[f"lwAreaExpl{w}"] = f"{AREA_EXPL[n][0]:.1f}"

    # The two derived quantities the argument turns on, computed rather than asserted.
    m["lwAreaRatio"] = f"{AREA_FULL[12][0] / AREA_FULL[4][0]:.1f}"
    m["lwYieldRatio"] = f"{FULL[12][0] / FULL[4][0]:.2f}"
    m["lwYieldDelta"] = f"{FULL[12][0] - FULL[4][0]:+.2f}"
    # Peak-to-endpoint drop, the collapse itself
    m["lwDrop"] = f"{100 * (FULL[8][0] - FULL[12][0]) / FULL[8][0]:.0f}"
    # Perceptual search is monotone; state it as a computed fact, not an eyeball
    m["lwPercMono"] = ("yes" if all(PERC[a][0] < PERC[b][0]
                                    for a, b in ((4, 8), (8, 12))) else "no")
    m["lwFullHump"] = ("yes" if FULL[4][0] < FULL[8][0] > FULL[12][0] else "no")

    # Reported statistics, transcribed verbatim.
    m["lwInterF"] = "8.45"
    m["lwInterDf"] = "2, 56"
    m["lwInterP"] = ".001"
    m["lwInterEta"] = "0.23"
    m["lwFourTwelveP"] = ".08"
    m["lwEightTwelveP"] = ".006"
    m["lwFourEightP"] = "<.001"
    m["lwPercF"] = "27.4"
    m["lwPercDf"] = "1, 28"
    m["lwAreaTwelveP"] = ".001"

    gen = ROOT / "report" / "gen" / "lewis_numbers.tex"
    gen.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(m.items())))
    with (ROOT / "report" / "results" / "numbers.txt").open("a") as fh:
        fh.write("\n\nLewis et al. 2010 retrodiction (source: tools/make_lewis_numbers.py, "
                 "transcribed from doi 10.1177/0018720810366859 Results)\n")
        for k, v in sorted(m.items()):
            fh.write(f"  {k} = {v}\n")
    print(f"wrote {gen} with {len(m)} numbers")


if __name__ == "__main__":
    main()
