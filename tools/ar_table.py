"""Turn `ar_eval.py`'s AR_ROW stream into a table, and gate every cell against a reference arm.

The evaluator emits one line per (arm, sweep value) with the block means attached, which is the
right format for a machine and the wrong one for a person. This reads a run log and prints an
arm-by-sweep grid, optionally with a paired significance marker against a named reference arm so
that a reader can see at a glance which differences the contract would actually accept.

Reads a log file, never acts on its contents: the parser only recognizes the AR_ROW and AR_META
lines it wrote itself and ignores everything else, which is the discipline an unattended loop
needs when the thing producing the log is the thing being modified.

Usage:
  python3 tools/ar_table.py RUN.log [--section MATCH] [--ref ARM] [--fmt md|tex] [--prec 3]
"""
from __future__ import annotations

import argparse
import math
import re

ROW = re.compile(r"^AR_ROW arm=(\S+) (?:(\S+?)=(\S+) )?mean=([-\d.eE+]+)(?: vals=(\S+))?")
META = re.compile(r"^AR_META (.*)$")


def parse(path: str, section: str | None = None) -> list[dict]:
    """Split a log into sections (a `###` or `@@@` banner starts one) and read their rows."""
    out, cur = [], {"title": "", "rows": [], "meta": ""}
    for line in open(path, errors="replace"):
        if line.startswith(("###", "@@@", "## ")):
            if cur["rows"]:
                out.append(cur)
            cur = {"title": line.strip().lstrip("#@ ").strip(), "rows": [], "meta": ""}
            continue
        m = ROW.match(line)
        if m:
            arm, key, val, mean, vals = m.groups()
            cur["rows"].append({
                "arm": arm, "key": key or "", "val": val or "",
                "mean": float(mean),
                "vals": [float(v) for v in vals.split(",")] if vals else [],
            })
            continue
        m = META.match(line)
        if m:
            cur["meta"] = m.group(1).strip()
    if cur["rows"]:
        out.append(cur)
    return [s for s in out if section is None or section.lower() in s["title"].lower()]


def paired(cand: list[float], ref: list[float], mpe: float, min_win: float = 0.6) -> str:
    """The contract's three-part test, rendered as one short marker."""
    if not cand or not ref or len(cand) != len(ref):
        return ""
    d = [c - r for c, r in zip(cand, ref)]
    n = len(d)
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n) if var > 0 else 0.0
    t = mean / se if se > 0 else (math.inf if mean else 0.0)
    wins = sum(1 for x in d if x > 0) / n
    sig = abs(t) > 1.70                       # one-sided alpha 0.05, n around 16 to 32
    if sig and abs(mean) >= mpe and (wins >= min_win or (1 - wins) >= min_win):
        return "**" if mean > 0 else "--"     # passes all three, up or down
    return "~"                                 # inside noise or inside the MPE


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log")
    ap.add_argument("--section")
    ap.add_argument("--ref", help="arm to gate every other arm against, per cell")
    ap.add_argument("--mpe", type=float, default=0.03)
    ap.add_argument("--fmt", choices=["md", "tex"], default="md")
    ap.add_argument("--prec", type=int, default=3)
    a = ap.parse_args()

    for sec in parse(a.log, a.section):
        arms, cols = [], []
        for r in sec["rows"]:
            if r["arm"] not in arms:
                arms.append(r["arm"])
            if r["val"] not in cols:
                cols.append(r["val"])
        cell = {(r["arm"], r["val"]): r for r in sec["rows"]}
        key = sec["rows"][0]["key"] or "arm"

        print(f"\n**{sec['title']}**" if a.fmt == "md" else f"% {sec['title']}")
        if sec["meta"]:
            print(f"`{sec['meta']}`" if a.fmt == "md" else f"% {sec['meta']}")
        sep = " | " if a.fmt == "md" else " & "
        end = "" if a.fmt == "md" else r" \\"
        head = sep.join([key] + cols)
        print(f"| {head} |{end}" if a.fmt == "md" else head + end)
        if a.fmt == "md":
            print("| " + " | ".join(["---"] * (len(cols) + 1)) + " |")
        for arm in arms:
            vals = []
            for c in cols:
                r = cell.get((arm, c))
                if r is None:
                    vals.append("")
                    continue
                txt = f"{r['mean']:.{a.prec}f}"
                if a.ref and arm != a.ref:
                    ref = cell.get((a.ref, c))
                    if ref is not None:
                        mark = paired(r["vals"], ref["vals"], a.mpe)
                        txt += f" {mark}" if mark != "~" else ""
                vals.append(txt)
            row = sep.join([arm] + vals)
            print(f"| {row} |{end}" if a.fmt == "md" else row + end)
        if a.ref:
            print(f"\n(gated against `{a.ref}`: `**` better, `--` worse, blank inside "
                  f"the MPE of {a.mpe} or inside noise)" if a.fmt == "md" else "")


if __name__ == "__main__":
    main()
