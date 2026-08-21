#!/usr/bin/env python3
"""Mechanical harness for Workflow 7 (autoresearch) of the academic-paper skill.

An autoresearch run is an unattended loop: the agent proposes a change, measures a
metric, and keeps or discards. Three parts of that loop are exactly the parts an
unattended agent gets wrong, so they are implemented here rather than left to prose:

  1. The noise floor. A metric that moves by 0.01 between seeds cannot certify a
     0.004 "improvement". `noise` measures the floor before the loop starts.
  2. The keep/discard gate. `gate` runs a paired, seed-matched comparison and
     refuses wins that are inside noise, below the minimum practical effect, or
     driven by a single lucky seed.
  3. The tamper guard. Every documented autoresearch failure involves the agent
     quietly editing the thing that scores it. `guard` checksums the frozen files
     and the seed list, and fails loudly when they move.

State lives in .autoresearch/contract.json. The experiment ledger is results.tsv,
which stays untracked by git: git history is the record of kept changes, the TSV is
the record of everything attempted.

Usage:
    python3 tools/autoresearch.py init --tag aug21 --metric val_rmse --direction min \
        --seeds 1-8 --freeze evaluate.py,data/holdout.csv --mpe 0.002
    python3 tools/autoresearch.py guard
    python3 tools/autoresearch.py noise --values 0.512,0.508,0.517,0.505,0.514
    python3 tools/autoresearch.py gate --champion 0.512,0.508,0.517,0.505,0.514 \
        --candidate 0.491,0.488,0.495,0.487,0.493 --loc-delta +14
    python3 tools/autoresearch.py log --desc "swap to Huber loss" --verdict keep \
        --values 0.491,0.488,0.495,0.487,0.493 --tier proxy
    python3 tools/autoresearch.py status
    python3 tools/autoresearch.py report
    python3 tools/autoresearch.py promote --exp 17

Exit codes: 0 success / keep, 1 failure / discard. The loop can branch on them.
"""

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone

STATE_DIR = ".autoresearch"
CONTRACT = os.path.join(STATE_DIR, "contract.json")
LEDGER = "results.tsv"
LEDGER_COLS = [
    "exp", "utc", "commit", "tier", "metric", "mean", "sd", "n",
    "d_base", "t", "wins", "loc", "verdict", "description",
]

# One-sided t critical values at alpha = 0.05, indexed by degrees of freedom.
# Stdlib only on purpose: this script has to run on a login node with no scipy.
T_CRIT_05 = {
    1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895,
    8: 1.860, 9: 1.833, 10: 1.812, 11: 1.796, 12: 1.782, 13: 1.771, 14: 1.761,
    15: 1.753, 16: 1.746, 17: 1.740, 18: 1.734, 19: 1.729, 20: 1.725, 21: 1.721,
    22: 1.717, 23: 1.714, 24: 1.711, 25: 1.708, 26: 1.706, 27: 1.703, 28: 1.701,
    29: 1.699, 30: 1.697,
}


def t_crit(df):
    if df <= 0:
        return float("inf")
    return T_CRIT_05.get(df, 1.645)


def parse_values(text):
    """Accept '0.51,0.49' or a path to a file with one value per line."""
    if text is None:
        return []
    if os.path.exists(text):
        with open(text) as fh:
            raw = [ln.strip() for ln in fh if ln.strip()]
    else:
        raw = [tok for tok in text.replace("\n", ",").split(",") if tok.strip()]
    return [float(tok) for tok in raw]


def parse_seeds(spec):
    """Accept '1-8' or '1,2,3,7'."""
    out = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            lo, hi = chunk.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        elif chunk:
            out.append(int(chunk))
    return out


def sha256_path(path):
    h = hashlib.sha256()
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(root, name)
                h.update(os.path.relpath(full, path).encode())
                with open(full, "rb") as fh:
                    for block in iter(lambda: fh.read(65536), b""):
                        h.update(block)
    else:
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
    return h.hexdigest()


def load_contract():
    if not os.path.exists(CONTRACT):
        sys.exit(f"FAIL: no {CONTRACT}. Run `autoresearch.py init` first.")
    with open(CONTRACT) as fh:
        return json.load(fh)


def save_contract(c):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(CONTRACT, "w") as fh:
        json.dump(c, fh, indent=2)


def git(*args):
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        ).stdout.strip()
    except FileNotFoundError:
        return ""


def read_ledger():
    if not os.path.exists(LEDGER):
        return []
    rows = []
    with open(LEDGER) as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    for ln in lines[1:]:
        rows.append(dict(zip(header, ln.split("\t"))))
    return rows


def better(a, b, direction):
    """True when a beats b under the contract's direction."""
    return a < b if direction == "min" else a > b


# ---------------------------------------------------------------- subcommands

def cmd_init(args):
    if os.path.exists(CONTRACT) and not args.force:
        sys.exit(f"FAIL: {CONTRACT} exists. Use --force to overwrite (this abandons the run).")
    frozen = {}
    for path in [p.strip() for p in args.freeze.split(",") if p.strip()]:
        if not os.path.exists(path):
            sys.exit(f"FAIL: cannot freeze missing path: {path}")
        frozen[path] = sha256_path(path)
    seeds = parse_seeds(args.seeds)
    if len(seeds) < 3:
        sys.exit(f"FAIL: {len(seeds)} seeds is too few to estimate a noise floor. Use 5 or more.")
    contract = {
        "tag": args.tag,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "metric": args.metric,
        "direction": args.direction,
        "seeds": seeds,
        "mpe": args.mpe,
        "min_win_frac": args.min_win_frac,
        "frozen": frozen,
        "champion": None,
        "baseline": None,
        "holdout_touched": False,
    }
    save_contract(contract)
    if not os.path.exists(LEDGER):
        with open(LEDGER, "w") as fh:
            fh.write("\t".join(LEDGER_COLS) + "\n")
    print(f"OK   contract written to {CONTRACT}")
    print(f"     tag={args.tag} branch={contract['branch']} metric={args.metric} ({args.direction})")
    print(f"     seeds={seeds} (n={len(seeds)})  minimum practical effect={args.mpe}")
    print(f"     frozen: {', '.join(frozen) if frozen else 'NOTHING (dangerous, freeze the evaluator)'}")
    print(f"     ledger: {LEDGER} (keep this untracked by git)")
    return 0


def cmd_guard(args):
    c = load_contract()
    failures = []
    for path, digest in c["frozen"].items():
        if not os.path.exists(path):
            failures.append(f"{path}: DELETED")
            continue
        now = sha256_path(path)
        if now != digest:
            failures.append(f"{path}: MODIFIED (expected {digest[:12]}, found {now[:12]})")
    if failures:
        print("FAIL tamper guard: the frozen scoring surface moved.")
        for f in failures:
            print(f"     {f}")
        print("     Revert these paths, then re-run. A metric measured by a modified")
        print("     evaluator is not comparable to anything already in the ledger.")
        return 1
    print(f"OK   tamper guard: {len(c['frozen'])} frozen path(s) unchanged, "
          f"{len(c['seeds'])} seeds fixed at {c['seeds']}")
    return 0


def _summary(values):
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    se = sd / (n ** 0.5) if n > 1 else 0.0
    return n, mean, sd, se


def cmd_noise(args):
    c = load_contract() if os.path.exists(CONTRACT) else {"mpe": args.mpe or 0.0}
    values = parse_values(args.values)
    if len(values) < 3:
        sys.exit("FAIL: need at least 3 baseline replicates to estimate a noise floor.")
    n, mean, sd, se = _summary(values)
    mde = t_crit(n - 1) * se * (2 ** 0.5)
    print(f"OK   baseline over n={n} seeds")
    print(f"     mean = {mean:.6g}")
    print(f"     sd   = {sd:.6g}   (seed-to-seed spread)")
    print(f"     se   = {se:.6g}")
    print(f"     minimum detectable effect at n={n}: about {mde:.6g}")
    print("     Any candidate whose delta is smaller than that is not distinguishable")
    print("     from noise at this replicate count. Either raise the seed count or")
    print("     stop chasing effects that size.")
    mpe = c.get("mpe", 0.0) or 0.0
    if mpe and mpe < mde:
        print(f"WARN your minimum practical effect ({mpe:.6g}) is below the minimum")
        print(f"     detectable effect ({mde:.6g}). The gate will reject wins you claim")
        print(f"     to care about. Raise the seed count or raise --mpe.")
    if os.path.exists(CONTRACT):
        c["baseline"] = {"values": values, "mean": mean, "sd": sd, "n": n}
        if c.get("champion") is None:
            c["champion"] = {"values": values, "mean": mean, "sd": sd, "n": n,
                             "commit": git("rev-parse", "--short", "HEAD"),
                             "description": "baseline"}
        save_contract(c)
        print(f"     recorded as baseline and champion in {CONTRACT}")
    return 0


def cmd_gate(args):
    c = load_contract()
    direction = c["direction"]
    mpe = args.mpe if args.mpe is not None else c.get("mpe", 0.0)
    min_win_frac = c.get("min_win_frac", 0.6)

    champ = parse_values(args.champion) if args.champion else (
        (c.get("champion") or {}).get("values", []))
    cand = parse_values(args.candidate)
    if not champ:
        sys.exit("FAIL: no champion values. Run `noise` on the baseline first, "
                 "or pass --champion explicitly.")
    if len(cand) != len(champ):
        sys.exit(f"FAIL: {len(cand)} candidate values vs {len(champ)} champion values. "
                 "The comparison must be seed-matched and paired. Rerun the candidate "
                 "on exactly the contract seeds.")

    # Paired differences, oriented so that positive always means improvement.
    diffs = [(ch - ca) if direction == "min" else (ca - ch)
             for ch, ca in zip(champ, cand)]
    n, mean_d, sd_d, se_d = _summary(diffs)
    wins = sum(1 for d in diffs if d > 0)
    win_frac = wins / n
    t_stat = (mean_d / se_d) if se_d > 0 else (float("inf") if mean_d > 0 else 0.0)
    crit = t_crit(n - 1)

    _, champ_mean, _, _ = _summary(champ)
    _, cand_mean, _, _ = _summary(cand)
    raw_delta = cand_mean - champ_mean

    reasons = []
    significant = t_stat >= crit
    practical = abs(mean_d) >= mpe
    consistent = win_frac >= min_win_frac
    simplification = args.loc_delta is not None and args.loc_delta < 0

    if not significant:
        reasons.append(f"inside noise (t={t_stat:.2f} < {crit:.2f} at df={n-1})")
    if not practical:
        reasons.append(f"below minimum practical effect ({abs(mean_d):.6g} < {mpe:.6g})")
    if not consistent:
        reasons.append(f"driven by too few seeds ({wins}/{n} wins < {min_win_frac:.0%})")

    verdict = "keep" if not reasons else "discard"

    # The simplicity criterion: deleting code and holding the metric flat is a win.
    # It is the one case where a non-significant result should still be kept.
    if verdict == "discard" and simplification and significant is False and mean_d >= -mpe:
        verdict = "keep"
        reasons = [f"simplification: {args.loc_delta} lines and metric held within {mpe:.6g}"]

    print(f"{'KEEP' if verdict == 'keep' else 'DISCARD':8s} {c['metric']}  "
          f"champion {champ_mean:.6g} -> candidate {cand_mean:.6g}  "
          f"(raw delta {raw_delta:+.6g})")
    print(f"     paired improvement = {mean_d:+.6g} +/- {se_d:.6g} (se), "
          f"t = {t_stat:.2f} vs crit {crit:.2f}, wins {wins}/{n}")
    if args.loc_delta is not None:
        print(f"     complexity: {args.loc_delta:+d} lines")
    for r in reasons:
        print(f"     {'why kept' if verdict == 'keep' else 'rejected'}: {r}")

    if args.json:
        print(json.dumps({
            "verdict": verdict, "mean_improvement": mean_d, "se": se_d,
            "t": t_stat, "t_crit": crit, "wins": wins, "n": n,
            "champion_mean": champ_mean, "candidate_mean": cand_mean,
            "reasons": reasons,
        }))

    if verdict == "keep" and args.promote_champion:
        c["champion"] = {
            "values": cand, "mean": cand_mean, "sd": _summary(cand)[2], "n": n,
            "commit": git("rev-parse", "--short", "HEAD"),
            "description": args.desc or "",
        }
        save_contract(c)
        print(f"     champion updated in {CONTRACT}")

    return 0 if verdict == "keep" else 1


def cmd_log(args):
    c = load_contract()
    rows = read_ledger()
    exp_id = len(rows) + 1
    values = parse_values(args.values) if args.values else []
    if values:
        n, mean, sd, _ = _summary(values)
    else:
        n, mean, sd = 0, float("nan"), float("nan")
    # Anchored to the baseline, not the champion: the champion moves during a run,
    # so a champion-relative delta would depend on whether gate ran before log.
    base_mean = (c.get("baseline") or {}).get("mean")
    delta = (mean - base_mean) if (base_mean is not None and values) else float("nan")

    def fmt(x):
        return "" if x != x else f"{x:.6g}"  # x != x catches nan

    row = {
        "exp": str(exp_id),
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "commit": git("rev-parse", "--short", "HEAD") or "",
        "tier": args.tier,
        "metric": c["metric"],
        "mean": fmt(mean),
        "sd": fmt(sd),
        "n": str(n),
        "d_base": fmt(delta),
        "t": args.t or "",
        "wins": args.wins or "",
        "loc": (f"{args.loc_delta:+d}" if args.loc_delta is not None else ""),
        "verdict": args.verdict,
        # Tabs and newlines would corrupt the TSV, so they are stripped, not escaped.
        "description": " ".join(args.desc.split()),
    }
    if not os.path.exists(LEDGER):
        with open(LEDGER, "w") as fh:
            fh.write("\t".join(LEDGER_COLS) + "\n")
    with open(LEDGER, "a") as fh:
        fh.write("\t".join(row[col] for col in LEDGER_COLS) + "\n")
    print(f"OK   logged exp {exp_id}: {args.verdict}  {row['mean']}  {row['description']}")
    return 0


def cmd_status(args):
    c = load_contract()
    rows = read_ledger()
    champ = c.get("champion") or {}
    base = c.get("baseline") or {}
    print(f"run tag        {c['tag']}   branch {c['branch']}")
    print(f"metric         {c['metric']} ({c['direction']}), seeds {c['seeds']}")
    if base:
        print(f"baseline       {base['mean']:.6g} +/- {base['sd']:.6g} (n={base['n']})")
    if champ:
        gain = ""
        if base and base.get("mean") is not None:
            d = champ["mean"] - base["mean"]
            pct = 100 * d / base["mean"] if base["mean"] else 0.0
            gain = f"   [{d:+.6g}, {pct:+.2f}% vs baseline]"
        print(f"champion       {champ['mean']:.6g}  @{champ.get('commit','')}  "
              f"{champ.get('description','')}{gain}")
    keeps = [r for r in rows if r.get("verdict") == "keep"]
    crashes = [r for r in rows if r.get("verdict") == "crash"]
    print(f"experiments    {len(rows)} run, {len(keeps)} kept, {len(crashes)} crashed")

    # The streak is the stopping signal: a long dry run means the idea family is
    # exhausted, not that the agent should try harder in the same direction.
    streak = 0
    for r in reversed(rows):
        if r.get("verdict") == "keep":
            break
        streak += 1
    print(f"dry streak     {streak} experiment(s) since the last keep")
    if streak >= args.streak_warn:
        print(f"               -> {streak} is past the warn threshold ({args.streak_warn}). "
              "Change the family of ideas, do not shrink the step size.")
    if rows:
        print("\nlast 10:")
        print(f"  {'exp':>3}  {'verdict':8s} {'mean':>10s} {'vs base':>10s}  description")
        for r in rows[-10:]:
            print(f"  {r.get('exp',''):>3}  {r.get('verdict',''):8s} "
                  f"{r.get('mean',''):>10s} {r.get('d_base',''):>10s}  {r.get('description','')}")
    return 0


def cmd_report(args):
    """The wake-up report. This is what the human reads first thing in the morning."""
    c = load_contract()
    rows = read_ledger()
    champ = c.get("champion") or {}
    base = c.get("baseline") or {}
    keeps = [r for r in rows if r.get("verdict") == "keep"]
    crashes = [r for r in rows if r.get("verdict") == "crash"]

    out = []
    out.append(f"# Autoresearch report: {c['tag']}")
    out.append("")
    out.append(f"- Branch: `{c['branch']}`")
    out.append(f"- Metric: `{c['metric']}` ({'lower' if c['direction']=='min' else 'higher'} is better)")
    out.append(f"- Seeds: {c['seeds']} (frozen)")
    out.append(f"- Experiments: {len(rows)} run, {len(keeps)} kept, {len(crashes)} crashed")
    if base and champ:
        d = champ["mean"] - base["mean"]
        pct = 100 * d / base["mean"] if base["mean"] else 0.0
        out.append(f"- Baseline {base['mean']:.6g} -> champion {champ['mean']:.6g} "
                   f"({d:+.6g}, {pct:+.2f}%)")
    out.append("")
    out.append("## Kept changes, in order")
    out.append("")
    if keeps:
        out.append("| exp | commit | mean | vs baseline | tier | description |")
        out.append("|---|---|---|---|---|---|")
        for r in keeps:
            out.append(f"| {r.get('exp','')} | `{r.get('commit','')}` | {r.get('mean','')} "
                       f"| {r.get('d_base','')} | {r.get('tier','')} | {r.get('description','')} |")
    else:
        out.append("None. The baseline survived every challenge.")
    out.append("")
    out.append("## What to check before trusting any of this")
    out.append("")
    unconfirmed = [r for r in keeps if r.get("tier") == "proxy"]
    if unconfirmed:
        out.append(f"- {len(unconfirmed)} kept change(s) were only measured on the proxy tier. "
                   "They are not paper-grade until confirmed at full scale.")
        out.append("  Unconfirmed: " + ", ".join(f"exp {r.get('exp')}" for r in unconfirmed))
    else:
        out.append("- Every kept change carries a full-scale confirmation.")
    out.append(f"- Held-out set touched during the run: {c.get('holdout_touched', False)}. "
               "It should be False. Evaluate on it once, now, and only now.")
    out.append("- Stacked-change risk: kept changes were accepted sequentially against a "
               "moving champion. Ablate the earliest kept changes against the final "
               "champion before claiming each one matters.")
    if crashes:
        out.append(f"- {len(crashes)} crash(es) were skipped. Confirm none of them were the "
                   "interesting idea failing for a boring reason.")
    out.append("")
    out.append("## Next step")
    out.append("")
    out.append("Promote confirmed wins into `empirical.md` with "
               "`python3 tools/autoresearch.py promote --exp N`, then run the ablation "
               "sweep. Nothing enters the manuscript straight from `results.tsv`.")
    text = "\n".join(out)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"OK   report written to {args.out}")
    else:
        print(text)
    return 0


def cmd_promote(args):
    """Emit an empirical.md entry for a confirmed win. The ledger is a search trace;
    empirical.md is the curated record the manuscript cites. They are not the same
    artifact and the promotion should be deliberate."""
    c = load_contract()
    rows = read_ledger()
    match = [r for r in rows if r.get("exp") == str(args.exp)]
    if not match:
        sys.exit(f"FAIL: no experiment {args.exp} in {LEDGER}")
    r = match[0]
    if r.get("verdict") != "keep":
        print(f"WARN experiment {args.exp} has verdict '{r.get('verdict')}', not 'keep'.")
    if r.get("tier") == "proxy":
        print("WARN this experiment was measured on the proxy tier only. Confirm it at "
              "full scale before it backs a manuscript number.")
    diff = git("show", "--stat", "--oneline", r.get("commit", "HEAD"))
    print(f"""
#### Exp A.{args.exp}: {r.get('description','')} (autoresearch {c['tag']}, PAPER REF: TBD)
- **Script**: TBD
- **Commit**: `{r.get('commit','')}` on branch `{c['branch']}`
- **Hopper job**: TBD
- **Data**: TBD, seeds {c['seeds']} (frozen for the whole run)
- **Hyperparams**: see the commit diff
- **Results**: {c['metric']} = {r.get('mean','')} +/- {r.get('sd','')} over n={r.get('n','')} seeds
  (paired t = {r.get('t','')} vs the champion it displaced, wins {r.get('wins','')})
- **Qualitative**: accepted by the autoresearch gate at tier '{r.get('tier','')}';
  complexity change {r.get('loc','n/a')} lines
- **Result files**: results.tsv exp {args.exp}

Commit stat:
{diff}

Fill in the TBD fields, paste into empirical.md, and append the reported values to
results/numbers.txt before citing them.
""".strip())
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="write the run contract and freeze the scoring surface")
    i.add_argument("--tag", required=True)
    i.add_argument("--metric", required=True)
    i.add_argument("--direction", choices=["min", "max"], required=True)
    i.add_argument("--seeds", required=True, help="'1-8' or '1,2,3,7'")
    i.add_argument("--freeze", default="", help="comma-separated files/dirs the agent may not edit")
    i.add_argument("--mpe", type=float, default=0.0, help="minimum practical effect")
    i.add_argument("--min-win-frac", type=float, default=0.6)
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    g = sub.add_parser("guard", help="verify the frozen scoring surface has not moved")
    g.set_defaults(func=cmd_guard)

    n = sub.add_parser("noise", help="measure the seed-to-seed noise floor from baseline replicates")
    n.add_argument("--values", required=True, help="comma-separated values or a file path")
    n.add_argument("--mpe", type=float, default=None)
    n.set_defaults(func=cmd_noise)

    ga = sub.add_parser("gate", help="paired keep/discard decision; exit 0 = keep, 1 = discard")
    ga.add_argument("--candidate", required=True)
    ga.add_argument("--champion", default=None, help="defaults to the contract champion")
    ga.add_argument("--mpe", type=float, default=None)
    ga.add_argument("--loc-delta", type=int, default=None, help="net lines added (negative = simpler)")
    ga.add_argument("--desc", default=None)
    ga.add_argument("--promote-champion", action="store_true")
    ga.add_argument("--json", action="store_true")
    ga.set_defaults(func=cmd_gate)

    lo = sub.add_parser("log", help="append one experiment to results.tsv")
    lo.add_argument("--desc", required=True)
    lo.add_argument("--verdict", required=True, choices=["keep", "discard", "crash", "confirm", "ablate", "refuted", "proved", "open"])
    lo.add_argument("--values", default=None)
    lo.add_argument("--tier", default="proxy", choices=["proxy", "full", "holdout", "proof"])
    lo.add_argument("--t", default=None)
    lo.add_argument("--wins", default=None)
    lo.add_argument("--loc-delta", type=int, default=None)
    lo.set_defaults(func=cmd_log)

    st = sub.add_parser("status", help="champion, counts, dry streak, last 10 experiments")
    st.add_argument("--streak-warn", type=int, default=15)
    st.set_defaults(func=cmd_status)

    rp = sub.add_parser("report", help="markdown wake-up report")
    rp.add_argument("--out", default=None)
    rp.set_defaults(func=cmd_report)

    pr = sub.add_parser("promote", help="emit an empirical.md entry for a kept experiment")
    pr.add_argument("--exp", type=int, required=True)
    pr.set_defaults(func=cmd_promote)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
