"""CR-53 v2: what an inconsistent operator costs, what a discerning one is worth, and which is bigger.

`service_cv` makes the console's service time a gamma with the SAME mean, so anything that moves is
variability and not speed. `admit_foresight` decides whether the console's feasibility test may look
at the realization: false, the default, compares the deadline against the mean, which is all a
deadline field could give it; true compares it against the draw, which models an operator who can
tell a hard request from an easy one at a glance. The two are identical at `service_cv = 0`.

Separating them is the point. Left together, as they were until instrument defect 7 was found, the
triage console's numbers read as an argument that erratic operators do better, which is absurd.
Apart, they price two different things a program office can actually buy: consistency, and
discernment. The measurement says which is worth more, and by how much, and it says something
neither of them predicted, which is that the cheap structural fix substitutes for the expensive human
one.

    st-svccv-9449062.out   C2 (admitting console, three consoles), C3 (the same under the bound)
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import rate_floor  # noqa: E402
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = "st-svccv-9449062.out"
C2 = "C2 the honest admitting console against the triage one"
C3 = "C3 does the bound blunt foresight"
P = ["4", "6", "8", "10", "12", "16"]


def main() -> None:
    out: list[tuple[str, str]] = []
    a = survey(LOG, C2, "served_per_step", quiet=True)
    i = P.index("16")

    # The three consoles, all admitting, at the published operating point. Only `cv` and whether the
    # feasibility test may see the draw differ between them.
    metro, noisy, seeing = a["adm_cv00"][i], a["adm_cv50"][i], a["fore_cv50"][i]
    out += [("FsMetro", f"{metro:.4f}"), ("FsNoisy", f"{noisy:.4f}"), ("FsSeeing", f"{seeing:.4f}"),
            ("FsSeeingHi", f"{a['fore_cv100'][i]:.4f}"), ("FsNoisyHi", f"{a['adm_cv100'][i]:.4f}"),
            # Consistency is what the metronome buys over the variable console that cannot triage.
            # Discernment is what triage buys on top of the variable console. Both are gated up.
            ("FsConsistency", f"{metro - noisy:+.4f}"),
            ("FsDiscernment", f"{seeing - noisy:+.4f}"),
            ("FsRatio", f"{(seeing - noisy) / max(metro - noisy, 1e-9):.1f}"),
            ("FsNetOverMetro", f"{seeing - metro:+.4f}"),
            ("FsMPE", f"{rate_floor():.4f}")]
    # Discernment's value rises with span, because triage needs something to triage away.
    for sp, nm in (("6", "Six"), ("8", "Eight"), ("12", "Twelve")):
        j = P.index(sp)
        out.append((f"FsDiscern{nm}", f"{a['fore_cv50'][j] - a['adm_cv50'][j]:+.4f}"))

    b = survey(LOG, C3, "served_per_step", quiet=True)
    # The substitution. Under the derived bound the console is holding two requests, so there is
    # almost nothing left for discernment to choose between, and its value collapses.
    bn, bs = b["boundadm_cv50"][i], b["boundfore_cv50"][i]
    out += [("FsBoundNoisy", f"{bn:.4f}"), ("FsBoundSeeing", f"{bs:.4f}"),
            ("FsBoundMetro", f"{b['bound_cv00'][i]:.4f}"),
            ("FsBoundDiscernment", f"{bs - bn:+.4f}"),
            ("FsBoundShrink", f"{(seeing - noisy) / max(bs - bn, 1e-9):.1f}")]

    dst = ROOT / "report" / "gen" / "foresight_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:20s} {v}")


if __name__ == "__main__":
    main()
