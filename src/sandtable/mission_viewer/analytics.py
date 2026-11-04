"""Statistical summaries and mechanism diagnostics; no execution or storage."""

import math, statistics
from scipy.stats import t as student_t
from .studies import METRICS


def sample_summary(xs):
    if not xs:
        return dict(n=0, mean=None, sd=None, se=None, ci95=None)
    mean = statistics.mean(xs)
    sd = statistics.stdev(xs) if len(xs) > 1 else None
    se = sd / math.sqrt(len(xs)) if sd is not None else None
    h = float(student_t.ppf(0.975, len(xs) - 1)) * se if se is not None else None
    return dict(
        n=len(xs), mean=mean, sd=sd, se=se, ci95=None if h is None else [mean - h, mean + h]
    )


def diagnostics(artifact):
    o = artifact["outcome"]
    events = artifact["events"]
    con = artifact["frames"][-1]["consoles"]
    first = o.get("first_leader_loss_step")
    return dict(
        v3_console_transfers=sum((e["event"] == "EXPERIMENTAL_CONSOLE_TRANSFER" for e in events)),
        v3_console_services=sum(con["serviced"]) if con else 0,
        v3_head_loss_occurred=int(first is not None and first >= 0),
        v3_contact_occurred=int((o.get("convoy_contact_count") or 0) > 0),
    )


def summarize(rows, d):
    by = {(r["arm"], r["seed"]): r["outcome"] for r in rows}
    out = []
    for arm in d["scenarios"]:
        rs = [r for r in rows if r["arm"] == arm["id"]]
        if not rs:
            continue
        stats = {
            k: sample_summary(
                [r["outcome"][k] for r in rs if isinstance(r["outcome"].get(k), (int, float))]
            )
            for k in METRICS
        }
        out.append(
            dict(
                arm=arm["id"],
                factors=arm["factors"],
                metrics=stats,
                time_to_full_delivery=sample_summary(
                    [r["outcome"]["mission_time"] for r in rs if r["outcome"]["cargo_success"] == 1]
                ),
            )
        )
    interactions = []
    for core in [5, 7]:

        def aid(resp, c):
            return next(
                (
                    a["id"]
                    for a in d["scenarios"]
                    if a["factors"] == dict(core=core, response=resp, comms=c)
                )
            )

        for response in ["halt", "herringbone"]:
            ids = [aid(response, 3), aid("continue", 3), aid(response, 0), aid("continue", 0)]
            common = [seed for seed in d["seeds"] if all(((a, seed) in by for a in ids))]
            metrics = {
                k: sample_summary(
                    [
                        by[ids[0], s][k] - by[ids[1], s][k] - by[ids[2], s][k] + by[ids[3], s][k]
                        for s in common
                    ]
                )
                for k in ["cargo_delivered", "crew_steps_at_risk", "blue_losses"]
            }
            interactions.append(
                dict(
                    core=core,
                    response=response,
                    formula=f"({ids[0]} − {ids[1]}) − ({ids[2]} − {ids[3]})",
                    metrics=metrics,
                )
            )
    return dict(scenarios=out, interactions=interactions)


def statistics_report(rows, design):
    keys = [
        "cargo_delivered",
        "delivered_frac",
        "cargo_lost",
        "cargo_in_transit",
        "crew_steps_at_risk",
        "crew_lost",
        "blue_losses",
        "mission_time",
        "cargo_success",
    ]
    out = []
    base = {r["seed"]: r for r in rows if r["arm"] == "baseline"}
    for arm in design["arms"]:
        name = arm["name"]
        rs = [r for r in rows if r["arm"] == name]
        stats = {}
        for key in keys:
            ys = [r["outcome"][key] for r in rs]
            mean = statistics.mean(ys)
            sd = statistics.stdev(ys) if len(ys) > 1 else None
            se = sd / math.sqrt(len(ys)) if sd is not None else None
            ds = [r["outcome"][key] - base[r["seed"]]["outcome"][key] for r in rs]
            dm = statistics.mean(ds)
            dse = statistics.stdev(ds) / math.sqrt(len(ds)) if len(ds) > 1 else None
            half = float(student_t.ppf(0.975, len(ds) - 1)) * dse if dse is not None else None
            stats[key] = dict(
                n=len(ys),
                mean=mean,
                sd=sd,
                se=se,
                paired_difference=dm,
                paired_ci95=None if half is None else [dm - half, dm + half],
            )
        out.append(dict(arm=name, summary=arm["compiled"]["summary"], metrics=stats))
    return out
