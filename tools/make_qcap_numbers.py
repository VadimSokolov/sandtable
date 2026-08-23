"""CR-48 and CR-49: what bounding the console's backlog is worth, and how wrong you can size it.

Reads the fine lambda scans produced by `tools/queue_kstar.py`, the second and independent
implementation of the console queue, and writes the macros the manuscript inputs.

The scan asks, for each lambda = (P - 2L) mu, how much useful service a console delivers at each
backlog bound. The naive reading is "find the argmax and check the closed form predicts it". That
reading is wrong here and the script deliberately does not offer it: the response is a plateau
whose width grows with lambda, so the highest pixel on a flat ridge is noise. Every statement below
is instead about PLATEAU MEMBERSHIP, where the plateau is every bound delivering within one
material effect, `ar_gate.rate_floor()`, of the best one.

Regenerate the inputs with, for n in 8, 12, 24:

    LAM=$(python3 -c "print(','.join(f'{1.3+0.1*i:.2f}' for i in range(67)))")
    PYTHONPATH=src python3 tools/queue_kstar.py --lam "$LAM" --n $n --reps 12 \
        --horizon 40000 --caps=-1,0,1,2,3,4,5,6,7,8 > report/data/queue/kscan-n$n.txt
"""
from __future__ import annotations

import math
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import rate_floor  # noqa: E402

# `FULL_MPE` is a FRACTION of capacity, not a rate. Using it directly as a threshold on
# served_per_step is a factor of 6.7 too generous and swallows the whole capacity ladder into one
# plateau; the first version of this script did exactly that. `rate_floor()` is the rate.
MPE = rate_floor()

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAPS = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8]
NAMES = {1: "One", 2: "Two", 3: "Three", 8: "Eight", 12: "Twelve",
         24: "Twentyfour"}   # LaTeX macro names cannot contain digits
RULES = {"floor": lambda x: math.floor(x) - 1,
         "third": lambda x: math.floor(x + 1.0 / 3.0) - 1,
         "half": lambda x: math.floor(x + 0.5) - 1}


def read(n: int) -> list[tuple[float, dict[int, float]]]:
    rows = []
    for ln in (ROOT / "report" / "data" / "queue" / f"kscan-n{n}.txt").read_text().splitlines():
        m = re.match(r"\s*([\d.]+)\s+([\d.]+) \| (.*) \|", ln)
        if m:
            rows.append((float(m.group(2)),
                         dict(zip(CAPS, [float(x) for x in m.group(3).split()]))))
    if not rows:
        raise SystemExit("no scan rows parsed; regenerate with the command in this file's docstring")
    return rows


def plateau(v: dict[int, float]) -> list[int]:
    best = max(v.values())
    return [c for c, x in v.items() if c >= 0 and best - x <= MPE]


def main() -> None:
    out, loads = [], (8, 12, 24)
    scans = {n: read(n) for n in loads}

    # 1. What bounding is worth at all, against the unbounded buffer the console has today.
    ratios = [max(v[c] for c in CAPS if c >= 0) / max(v[-1], 1e-9) for _, v in scans[12]]
    out.append(("QcapUnboundedGainMin", f"{min(ratios):.0f}"))
    out.append(("QcapUnboundedGainMed", f"{sorted(ratios)[len(ratios) // 2]:.0f}"))

    # 2. Which direction of mis-sizing hurts. The first version of this script averaged over all
    #    loads and reported a single asymmetry; that number is a mixture of two opposite regimes and
    #    meant nothing. A length cap does not have a fixed meaning in time: at high arrival rates a
    #    buffer of k is a short delay because it is refilled constantly, and at low rates the same k
    #    is a long one. So the direction of the risk REVERSES with load, and the honest statistic is
    #    per load.
    for n in loads:
        lo, hi, over = [], [], 0
        for _lam, v in scans[n]:
            k = max((c for c in CAPS if c >= 0), key=lambda c: v[c])
            best = v[k]
            if k - 1 >= 0 and k + 1 in v and best > 0:
                a, b = 100.0 * (best - v[k - 1]) / best, 100.0 * (best - v[k + 1]) / best
                lo.append(a)
                hi.append(b)
                over += b > a
        out.append((f"QcapUnderCost{NAMES[n]}", f"{sum(lo) / len(lo):.1f}"))
        out.append((f"QcapOverCost{NAMES[n]}", f"{sum(hi) / len(hi):.1f}"))
        out.append((f"QcapOverWorseFrac{NAMES[n]}", f"{100.0 * over / len(lo):.0f}"))

    # 3. Plateau geometry: the lower edge barely moves, the upper edge tracks lambda.
    edges = [(lam, min(plateau(v)), max(plateau(v))) for lam, v in scans[12]]
    wide = [(hi_ - lo_ + 1) for _l, lo_, hi_ in edges]
    out.append(("QcapPlateauLoMin", f"{min(e[1] for e in edges)}"))
    out.append(("QcapPlateauLoMax", f"{max(e[1] for e in edges)}"))
    out.append(("QcapPlateauWideMax", f"{max(wide)}"))
    for n in loads:
        sharp = sum(1 for _l, v in scans[n] if len(plateau(v)) <= 2)
        out.append((f"QcapSharp{NAMES[n]}", f"{sharp}"))
    out.append(("QcapLamMax", f"{max(e[0] for e in edges):.1f}"))

    # 4. How the three candidate rules score, and where the published one fails.
    for name, f in RULES.items():
        miss = [(n, lam) for n in loads for lam, v in scans[n] if f(lam) not in plateau(v)]
        tag = name.capitalize()
        out.append((f"Qcap{tag}Miss", f"{len(miss)}"))
        if miss:
            out.append((f"Qcap{tag}MissLo", f"{min(m[1] for m in miss):.1f}"))
            out.append((f"Qcap{tag}MissHi", f"{max(m[1] for m in miss):.1f}"))
    out.append(("QcapPoints", f"{sum(len(scans[n]) for n in loads)}"))

    # 5. Whether a single fixed bound would do, which is what a program office will actually ship.
    for fixed in (1, 2, 3):
        ok = [lam for n in loads for lam, v in scans[n] if fixed in plateau(v)]
        allm = [lam for n in loads for lam, v in scans[n]]
        out.append((f"QcapFixed{NAMES[fixed]}Frac", f"{100.0 * len(ok) / len(allm):.0f}"))
        bad = [lam for n in loads for lam, v in scans[n] if fixed not in plateau(v)]
        if bad:
            out.append((f"QcapFixed{NAMES[fixed]}BadHi", f"{max(bad):.1f}"))

    # 6. The requirements ladder, run here rather than read from a log so that every number in the
    #    paragraph it feeds is regenerated by this script. Roughly three minutes.
    import numpy as np  # noqa: PLC0415
    sys.path.insert(0, str(ROOT / "tools"))
    from queue_kstar import simulate  # noqa: PLC0415

    R, H, PP, MU, NN = 12, 40000.0, 20.0, 0.15, 12

    def arm(lat, cap, age, reps=R, sw=None):
        return np.array([simulate(NN, PP, lat, MU, cap, 22.0, H, 1000 + s, "fifo",
                                  age_cap=age, lat_switch=sw)["useful"] for s in range(reps)])

    lats, counters, ages = [0, 1, 2, 3, 4, 5, 6], [0, 1, 2, 3, 4, 6], [4, 7, 10, 13, 16, 20, 26]
    cvals = {c: {L: arm(L, c, None).mean() for L in lats} for c in counters}
    avals = {a: {L: arm(L, -1, a).mean() for L in lats} for a in ages}
    ceiling = {L: max(max(cvals[c][L] for c in counters), max(avals[a][L] for a in ages))
               for L in lats}

    def score(tbl):
        best, cov, short = None, -1, None
        for k, row in tbl.items():
            n = sum(1 for L in lats if ceiling[L] - row[L] <= MPE)
            w = max(ceiling[L] - row[L] for L in lats)
            if n > cov or (n == cov and w < short):
                best, cov, short = k, n, w
        return best, cov, short

    bc, bcov, bshort = score(cvals)
    ba, acov, ashort = score(avals)
    out += [("QcapBestCounter", f"{bc}"), ("QcapBestCounterCov", f"{bcov}"),
            ("QcapBestCounterShort", f"{bshort:.4f}"),
            ("QcapBestAge", f"{ba}"), ("QcapBestAgeCov", f"{acov}"),
            ("QcapBestAgeShort", f"{ashort:.4f}"), ("QcapLinks", f"{len(lats)}"),
            ("QcapCounterClear", f"{cvals[bc][0]:.4f}"), ("QcapCounterDeep", f"{cvals[bc][6]:.4f}"),
            ("QcapAgeClear", f"{avals[ba][0]:.4f}"), ("QcapAgeDeep", f"{avals[ba][6]:.4f}"),
            ("QcapDeepGain", f"{100 * (avals[ba][6] / cvals[bc][6] - 1):.0f}")]

    # The moving link: the limb that decides whether the timestamp is worth its message field.
    k1 = arm(0.0, bc, None, reps=32, sw=(500.0, 4.0))
    t7 = arm(0.0, -1, ba, reps=32, sw=(500.0, 4.0))
    d = t7 - k1
    out += [("QcapSwitchCounter", f"{k1.mean():.4f}"), ("QcapSwitchAge", f"{t7.mean():.4f}"),
            ("QcapSwitchDiff", f"{d.mean():+.4f}"),
            ("QcapSwitchT", f"{d.mean() / (d.std(ddof=1) / np.sqrt(32)):.1f}")]

    # Given the counter, does the discipline still matter? At a bound of one there is no order left
    # to permute, which is the cleanest form the answer takes.
    for tag, lam, pp in (("Clear", 3.0, 20.0), ("Jam", 1.8, 12.0)):
        k = math.floor(lam + 0.5) - 1
        f = np.array([simulate(NN, pp, 0.0, MU, k, 22.0, H, 1000 + s, "fifo")["useful"]
                      for s in range(24)])
        l = np.array([simulate(NN, pp, 0.0, MU, k, 22.0, H, 1000 + s, "lifo")["useful"]
                      for s in range(24)])
        out += [(f"QcapDisc{tag}K", f"{k}"), (f"QcapDisc{tag}Fifo", f"{f.mean():.4f}"),
                (f"QcapDisc{tag}Lifo", f"{l.mean():.4f}"),
                (f"QcapDisc{tag}Diff", f"{abs(f.mean() - l.mean()):.4f}")]

    # 7. The mechanism behind 2, measured rather than asserted. A request entering a full buffer of
    #    k advances one place per removal, and at equilibrium removals (services plus drop-oldest
    #    evictions) happen at the ARRIVAL rate, so the age of the request the console picks up is
    #    about (k-1)/Lambda. That is what makes a cap in requests a different delay at each load.
    KAGE = 4
    ages = {}
    for nn in (8, 24):
        r = [simulate(nn, PP, 0.0, MU, KAGE, 22.0, H, 1000 + s, "fifo") for s in range(8)]
        ages[nn] = (float(np.mean([x["age"] for x in r])),
                    float(np.mean([x["arr_rate"] for x in r])))
    out += [("QcapAgeK", f"{KAGE}")]
    for nn, tag in ((8, "Light"), (24, "Heavy")):
        a, lam = ages[nn]
        # Two regimes, not one. While the buffer overflows, every arrival evicts the oldest and a
        # request advances one place per removal at the arrival rate, giving k/Lambda. While it
        # drains, advancement is by service alone and the age is j/mu, which does not depend on the
        # load at all. The measured age sits between the two bounds and the mixture weight is what
        # moves with load; only the inverse dependence on Lambda is claimed in the text.
        out += [(f"QcapAge{tag}", f"{a:.1f}"), (f"QcapAgeRate{tag}", f"{lam:.2f}"),
                (f"QcapAgeForm{tag}", f"{(KAGE - 1) / lam:.1f}"),
                (f"QcapAgeFlow{tag}", f"{KAGE / lam:.1f}")]

    # 8. CR-51: the console in this paper is a metronome, and every closed form was derived on one.
    #    The mean service is held exactly, so anything that moves is variability and not speed.
    CVS = (0.0, 0.25, 0.5, 1.0)
    ladder = (1.8, 3.0, 6.0)
    caps8 = list(range(8))
    plate0, worst_shift, outside = {}, 0, 0
    for lam in ladder:
        pp = lam / MU
        k0 = None
        for cv in CVS:
            vv = {c: float(np.mean([simulate(NN, pp, 0.0, MU, c, 22.0, H, 1000 + sd, "fifo",
                                             cv=cv)["useful"] for sd in range(R)]))
                  for c in caps8}
            best = max(vv.values())
            pl = [c for c, x in vv.items() if best - x <= MPE]
            am = max(vv, key=lambda c: vv[c])
            if cv == 0.0:
                k0, plate0[lam] = am, best
            else:
                worst_shift = min(worst_shift, am - k0)
                outside += k0 not in pl
            if cv == CVS[-1]:
                out += [(f"QcapCvBest{'Jam' if lam < 2 else ('Pub' if lam < 4 else 'Long')}",
                         f"{best:.4f}"),
                        (f"QcapCvLoss{'Jam' if lam < 2 else ('Pub' if lam < 4 else 'Long')}",
                         f"{100 * (1 - best / plate0[lam]):.0f}")]
    out += [("QcapCvShiftWorst", f"{abs(worst_shift)}"), ("QcapCvOutside", f"{outside}"),
            ("QcapCvCells", f"{len(ladder) * (len(CVS) - 1)}"), ("QcapCvMax", f"{CVS[-1]:.2f}")]

    # And whether the lever itself survives a variable operator.
    pp = 3.0 / MU
    k = math.floor(3.0 + 0.5) - 1
    for cv, tag in ((0.0, "Metro"), (1.0, "Noisy")):
        b = np.array([simulate(NN, pp, 0.0, MU, -1, 22.0, H, 1000 + sd, "fifo", cv=cv)["useful"]
                      for sd in range(24)])
        g = np.array([simulate(NN, pp, 0.0, MU, k, 22.0, H, 1000 + sd, "fifo", cv=cv)["useful"]
                      for sd in range(24)])
        a = np.array([simulate(NN, pp, 0.0, MU, -1, 22.0, H, 1000 + sd, "fifo",
                               age_cap=pp - 1 / MU, cv=cv)["useful"] for sd in range(24)])
        out += [(f"QcapCvBound{tag}", f"{(g - b).mean():+.4f}"),
                (f"QcapCvAge{tag}", f"{(a - b).mean():+.4f}")]

    # 9. And the same rule inside SandTable itself, at full tier, which is where the paper's
    #    numbers have to come from. The auxiliary model above is the mechanism; this is the claim.
    from ar_survey import survey  # noqa: PLC0415

    LOG = "st-qcap-9448688.out"
    for sec, tag, kstar in (("Q1 the capacity ladder", "Clear", 2), ("Q2 the capacity ladder",
                                                                    "Jam", 1)):
        try:
            lv = survey(LOG, sec, "served_per_step", quiet=True)
        except SystemExit:
            continue
        pts = ["6", "8", "10", "12", "16"]
        # The FULL ladder, not the four rungs nearest the answer. Searching an argmax over a
        # truncated ladder is a way of being right by construction, and an earlier version of this
        # script did it: `names` stopped at three, so a cap of six could never have won even if it
        # had. Every capacity the battery ran is now a candidate.
        names = {0: "cap_zero", 1: "cap_one", 2: "cap_two", 3: "cap_three", 4: "cap_four",
                 5: "cap_five", 6: "cap_six", 10: "cap_ten"}
        idx = {p: i for i, p in enumerate(pts)}
        have = [c for c in names if names[c] in lv]
        arg = [max(have, key=lambda c: lv[names[c]][idx[p]]) for p in pts]
        # A cell whose plateau is wide cannot discriminate between rules, so counting argmax hits
        # over such cells inflates the claim: the argmax there is chosen by rounding. A cell is
        # SHARP when at most two capacities sit within one material effect of the best, and the
        # honest statement is the hit rate over the sharp cells plus how many cells were sharp.
        def st_plateau(p):   # named apart from the module-level `plateau`, which is the lam scan
            best = max(lv[names[c]][idx[p]] for c in have)
            return [c for c in have if lv[names[c]][idx[p]] >= best - MPE]
        widths = [len(st_plateau(p)) for p in pts]
        sharp = [i for i, w in enumerate(widths) if w <= 2]
        out += [(f"StQcap{tag}Argmax", "/".join(str(a) for a in arg)),
                (f"StQcap{tag}Hit", f"{sum(1 for a in arg if a == kstar)}"),
                (f"StQcap{tag}Spans", f"{len(pts)}"),
                (f"StQcap{tag}Sharp", f"{len(sharp)}"),
                (f"StQcap{tag}SharpHit", f"{sum(1 for i in sharp if arg[i] == kstar)}"),
                (f"StQcap{tag}SoleWidth", f"{sum(1 for w in widths if w == 1)}"),
                (f"StQcap{tag}WidestPlateau", f"{max(widths)}"),
                (f"StQcap{tag}Best", f"{lv[names[kstar]][idx['16']]:.4f}"),
                (f"StQcap{tag}None", f"{lv['cap_none'][idx['16']]:.4f}"),
                (f"StQcap{tag}Ratio", f"{lv[names[kstar]][idx['16']] / max(lv['cap_none'][idx['16']], 1e-9):.0f}")]
        if kstar == 1 and "cap_zero" in lv:
            out.append(("StQcapJamFloorGap", f"{lv['cap_one'][idx['16']] - lv['cap_zero'][idx['16']]:+.4f}"))
    try:
        su = survey(LOG, "Q1 the capacity ladder", "success", quiet=True)
        out += [("StQcapSuccBound", f"{100 * su['cap_two'][1]:.1f}"),
                ("StQcapSuccNone", f"{100 * su['cap_none'][1]:.1f}"),
                ("StQcapSuccGain", f"{100 * (su['cap_two'][1] - su['cap_none'][1]):.1f}")]
    except (SystemExit, KeyError):
        pass

    dst = ROOT / "report" / "gen" / "qcap_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:24s} {v}")


if __name__ == "__main__":
    main()
