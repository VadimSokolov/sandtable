"""CR-60: which reading of the same positions predicts whether the mission survives.

Every position-error metric in this paper before this battery was a scalar distance from each
vehicle to the station it was commanded to hold. That metric cannot distinguish a formation that has
been displaced as a body, which costs nothing, from one that has come apart, which is fatal. The
battery drives both families on one grid and asks which reading orders the design space the way
mission success does.

The registered answer was the CROSS-TRACK component of the station error, on the reasoning that a
displacement along the axis of advance is harmless and one across it is not. That is falsified. The
reading that survives is one that never looks at the commanded formation at all: the RMS distance of
the living assault force from its own centroid. It needs no knowledge of the intended geometry and
is recoverable from bare position tracks, which is what makes it writable into a requirement.

    st-cross-9449945.out   L1 the two families on one grid; L2 the corridor; L3 column length;
                           L4 a channel rather than a probe; L5 the family it must be blind to
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_survey import survey  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = "st-cross-9449945.out"
L1 = "L1 the two families against every reading of the same positions"
L2 = "L2 does the penalty need a corridor"
L3 = "L3 does one threshold survive column length"
L4 = "L4 the same reading under a channel rather than a probe"
L5 = "L5 the family a formation metric must be blind to"
# The four candidate readings of one set of positions, in the order the registration ranked them.
READS = (("Scalar", "station_err_mean"), ("Cross", "station_cross_mean"),
         ("Spread", "fleet_spread_mean"), ("FCross", "fleet_cross_mean"))


def _inversions(lv, suc, gated, pt=0):
    """Pairs the metric orders backwards, counted only over arms mission success separates.

    A metric cannot be blamed for ordering two arms that the mission itself cannot tell apart, so
    the count runs over gated-apart pairs only. This is the test the conjecture registered and it
    is the reason the registered answer lost: an ordering claim scored on every pair rewards a
    metric for agreeing about arms where there is nothing to agree about.
    """
    arms = sorted(lv)
    bad = 0
    for i, a in enumerate(arms):
        for b in arms[i + 1:]:
            if (a, b) not in gated:
                continue
            worse = a if suc[a][pt] < suc[b][pt] else b
            better = b if worse == a else a
            if lv[worse][pt] < lv[better][pt]:      # the mission's loser reads BETTER on the metric
                bad += 1
    return bad, sum(1 for i, a in enumerate(arms) for b in arms[i + 1:] if (a, b) in gated)


def _separates(lv, suc, live, pt=0):
    """The gap between the worst surviving arm and the best dying one, or None if they interleave."""
    hi = max(lv[a][pt] for a in live)
    lo = min(lv[a][pt] for a in lv if a not in live)
    return (hi, lo) if hi < lo else None


KLOG = "st-dispcol-9459110.out"
K1 = "K1 the recommended reading against column length"
K2 = "K2 the nuisance family against column length"
SPANS = ("4", "8", "12", "16")


def _owed_column_length() -> list[tuple[str, str]]:
    """The section CR-60 owed, and the one that changes the recommendation's wording.

    L3 swept column length but did not log `fleet_spread_mean`, which is the reading the conjecture
    ends up recommending, so the column-length check for it was recorded as owed rather than
    quietly skipped. This is that check. It also carries the nuisance family at every span, because
    a requirement written on a threshold measured at one column length is a fitted constant.
    """
    out: list[tuple[str, str]] = []
    suc = survey(KLOG, K1, "success", quiet=True)
    csuc = survey(KLOG, K1, "success", ref="base", quiet=True)
    reads = (("Scalar", "station_err_mean"), ("Cross", "station_cross_mean"),
             ("Spread", "fleet_spread_mean"), ("FCross", "fleet_cross_mean"))
    for tag, metric in reads:
        lv = survey(KLOG, K1, metric, quiet=True)
        held, ivs = 0, []
        for i, sp in enumerate(SPANS):
            dead = {a for a in suc if a != "base" and (a, sp) in csuc
                    and csuc[(a, sp)][4] == "GATE down"}
            live = set(suc) - dead
            if not dead or not live:
                continue
            s = _separates(lv, suc, live, pt=i)
            if s:
                held += 1
                ivs.append(s)
        out.append((f"Dk{tag}Held", f"{held}"))
        out.append((f"Dk{tag}Spans", f"{len(SPANS)}"))
        if held == len(SPANS):
            # The threshold that serves EVERY column length is the intersection of the per-span
            # admissible intervals, not the average of their midpoints. An average can sit outside
            # an interval it was averaged from, which is how a fitted constant gets written into a
            # requirement without anyone noticing.
            lo, hi = max(a for a, _ in ivs), min(b for _, b in ivs)
            if lo < hi:
                out += [(f"Dk{tag}Lo", f"{lo:.0f}"), (f"Dk{tag}Hi", f"{hi:.0f}"),
                        (f"Dk{tag}Thresh", f"{0.5 * (lo + hi):.0f}")]
            else:
                out.append((f"Dk{tag}Thresh", "disjoint"))
        else:
            out.append((f"Dk{tag}Thresh", "none"))

    # Does the threshold this paper published, measured at ONE column length, survive four of them?
    lv = survey(KLOG, K1, "fleet_spread_mean", quiet=True)
    joint = dict(out).get("DkSpreadLo")
    out.append(("DkWidestAlive", f"{max(lv['base'][3], lv['out320'][3]):.0f}"))
    out.append(("DkOldSurvives", "no" if joint and float(joint) > 189.0 else "yes"))

    # K2. The nuisance family at every column length. The question is not whether route bias moves
    # the reading but whether the DISPERSION PENALTY ITSELF survives the route, and at four assets
    # against sixteen it does not merely weaken, it reverses.
    s2 = survey(KLOG, K2, "success", quiet=True)
    l2 = survey(KLOG, K2, "fleet_spread_mean", quiet=True)
    c4 = survey(KLOG, K2, "success", ref="tight4", quiet=True)
    c16 = survey(KLOG, K2, "success", ref="tight16", quiet=True)
    out += [("DkTightFourHi", f"{max(l2['tight4']):.0f}"),
            ("DkWideFourLo", f"{min(l2['wide4']):.0f}"),
            ("DkTightSixHi", f"{max(l2['tight16']):.0f}"),
            ("DkWideSixLo", f"{min(l2['wide16']):.0f}"),
            ("DkTightFourFlat", f"{100 * s2['tight4'][0]:.1f}"),
            ("DkTightFourCover", f"{100 * s2['tight4'][4]:.1f}"),
            ("DkWideFourCover", f"{100 * s2['wide4'][4]:.1f}"),
            ("DkTightSixCover", f"{100 * s2['tight16'][4]:.1f}"),
            ("DkWideSixFlat", f"{100 * s2['wide16'][0]:.1f}"),
            ("DkWideSixCover", f"{100 * s2['wide16'][4]:.1f}")]
    for tag, c, key in (("Four", c4, ("wide4", "1.0")), ("Six", c16, ("wide16", "1.0"))):
        e, tt, ag, nb, v = c[key]
        out += [(f"DkCost{tag}", f"{e:+.4f}"),
                (f"DkCost{tag}T", "infinite" if tt != tt or abs(tt) == float("inf") else f"{tt:.1f}"),
                (f"DkCost{tag}Blocks", f"{ag}"),
                (f"DkCost{tag}V", v.replace("GATE ", "gates "))]
    out.append(("DkBlocks", f"{c4[('wide4', '1.0')][3]}"))
    return out


def main() -> None:
    out: list[tuple[str, str]] = []
    suc = survey(LOG, L1, "success", quiet=True)
    csuc = survey(LOG, L1, "success", ref="base", quiet=True)
    # Which arms the mission itself separates, and from that which pairs a metric may be scored on.
    dead = {a for a in suc if (a, "8") in csuc and csuc[(a, "8")][4] == "GATE down"}
    live = set(suc) - dead
    gated = {(a, b) for a in suc for b in suc if a < b
             and ((a in dead) != (b in dead))}
    out += [("DsLive", f"{len(live)}"), ("DsDead", f"{len(dead)}"),
            ("DsPairs", f"{len(gated)}")]

    for tag, metric in READS:
        lv = survey(LOG, L1, metric, quiet=True)
        bad, n = _inversions(lv, suc, gated)
        out += [(f"Ds{tag}Inv", f"{bad}"), (f"Ds{tag}Pairs", f"{n}")]
        sep = _separates(lv, suc, live)
        if sep:
            hi, lo = sep
            out += [(f"Ds{tag}Hi", f"{hi:.1f}"), (f"Ds{tag}Lo", f"{lo:.1f}"),
                    (f"Ds{tag}Thresh", f"{0.5 * (hi + lo):.0f}")]
        else:
            out.append((f"Ds{tag}Thresh", "none"))

    # The two arms that carry the falsification, named in the open: an offset the mission does not
    # notice reads worse on the scalar than a dispersion that kills it.
    sc, cr = survey(LOG, L1, "station_err_mean", quiet=True), survey(LOG, L1, "station_cross_mean", quiet=True)
    out += [("DsOutSc", f"{sc['out320'][0]:.0f}"), ("DsOutSuc", f"{100 * suc['out320'][0]:.1f}"),
            ("DsSpSc", f"{sc['sp300'][0]:.0f}"), ("DsSpSuc", f"{100 * suc['sp300'][0]:.1f}"),
            ("DsMidCross", f"{cr['sp120'][0]:.1f}"), ("DsMidSuc", f"{100 * suc['sp120'][0]:.1f}"),
            ("DsBaseSuc", f"{100 * suc['base'][0]:.1f}")]

    # L3. A threshold that only holds at one column length is not a requirement. Recomputed per span.
    s3 = survey(LOG, L3, "success", quiet=True)
    c3 = survey(LOG, L3, "success", ref="base", quiet=True)
    for tag, metric in (("Spread", "fleet_spread_mean"), ("FCross", "fleet_cross_mean"),
                        ("Cross", "station_cross_mean")):
        lv = survey(LOG, L3, metric, quiet=True)
        if not lv:
            # `fleet_spread_mean` was not logged in L3. Recorded rather than silently skipped,
            # because it is the reading the conjecture ends up recommending and the column-length
            # check for it is therefore owed.
            out.append((f"Dl{tag}Held", "unlogged"))
            continue
        held, ths = 0, []
        for i, sp in enumerate(("4", "8", "12", "16")):
            d = {a for a in s3 if (a, sp) in c3 and c3[(a, sp)][4] == "GATE down"}
            liv = set(s3) - d
            if not d or not liv:
                continue
            sep = _separates(lv, s3, liv, pt=i)
            if sep:
                held += 1
                ths.append(0.5 * (sep[0] + sep[1]))
        out += [(f"Dl{tag}Held", f"{held}"),
                (f"Dl{tag}Range", f"{min(ths):.0f} to {max(ths):.0f}" if ths else "none")]

    # L5. The family a formation metric must be BLIND to, and the test is not whether the reading
    # moves under route bias but whether it moves ACROSS ITS OWN THRESHOLD. A requirement is a line,
    # so the only failure that matters is a nuisance that carries a cell over the line. Every L5 cell
    # is scored against the threshold L1 fixed: `tight` should read safe everywhere and `sp300`,
    # whose success never exceeds 0.44 in this section, should read unsafe everywhere.
    thr = {t: v for t, v in out}
    for tag, metric in (("Spread", "fleet_spread_mean"), ("FCross", "fleet_cross_mean"),
                        ("Cross", "station_cross_mean")):
        lv = survey(LOG, L5, metric, quiet=True)
        if not lv or thr.get(f"Ds{tag}Thresh", "none") == "none":
            out.append((f"Db{tag}Miss", "no threshold"))
            continue
        line = float(thr[f"Ds{tag}Thresh"])
        miss = sum(1 for v in lv["tight"] if v >= line) + sum(1 for v in lv["sp300"] if v < line)
        out += [(f"Db{tag}Miss", f"{miss}"), (f"Db{tag}Cells", f"{len(lv['tight']) + len(lv['sp300'])}"),
                (f"Db{tag}TightHi", f"{max(lv['tight']):.1f}"),
                (f"Db{tag}WideLo", f"{min(lv['sp300']):.1f}")]
    out.append(("DbWideWorstSuc", f"{100 * max(survey(LOG, L5, 'success', quiet=True)['sp300']):.1f}"))

    # L2. The corridor. The registered mechanism was that a dispersed force is punished because the
    # terrain funnels it; on a map with no cover at all the penalty should be at most half. It is not.
    #
    # Both readings are emitted because they disagree about which map is kinder and the registered
    # falsifier is comfortably clear of either: absolute, the open map costs slightly MORE than the
    # banded one; relative to what there was to lose, it costs far more. The falsifier asked for at
    # most half.
    s2 = survey(LOG, L2, "success", quiet=True)
    for atag, arm in (("Wide", "sp600"), ("Mid", "sp300")):
        cost = {p: s2["base"][i] - s2[arm][i] for i, p in enumerate(("band", "chokepoint", "open"))}
        rel = {p: cost[p] / s2["base"][i] for i, p in enumerate(("band", "chokepoint", "open"))}
        out += [(f"Dc{atag}Band", f"{100 * cost['band']:.1f}"),
                (f"Dc{atag}Choke", f"{100 * cost['chokepoint']:.1f}"),
                (f"Dc{atag}Open", f"{100 * cost['open']:.1f}"),
                (f"Dc{atag}Ratio", f"{cost['open'] / cost['band']:.2f}"),
                (f"Dc{atag}RelBand", f"{100 * rel['band']:.1f}"),
                (f"Dc{atag}RelOpen", f"{100 * rel['open']:.1f}")]
    out.append(("DcNeeded", "0.50"))

    # L4. The same reading under a comms channel rather than a scripted probe, which is the check
    # that the dispersion penalty is not an artefact of how the dispersion was imposed.
    s4 = survey(LOG, L4, "success", ref="chan", quiet=True)
    for ctag, cl in (("Clean", "0"), ("Deg", "3")):
        r = s4.get(("chansp", cl))
        if r:
            out += [(f"Dh{ctag}", f"{r[0]:+.4f}"), (f"Dh{ctag}V", r[4].replace("GATE ", "gates "))]

    out += _owed_column_length()

    dst = ROOT / "report" / "gen" / "disp_numbers.tex"
    dst.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in out))
    print(f"wrote {dst} with {len(out)} macros")
    for k, v in out:
        print(f"  {k:16s} {v}")


if __name__ == "__main__":
    main()
