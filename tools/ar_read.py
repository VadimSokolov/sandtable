"""Read any battery log's sections as gated paired contrasts, from the command line.

Every evaluation in this project has been a variant of the same three lines: load a section, pair
two arms blockwise, apply the tier's gate. Writing them out again per battery is how the `agree()`
defect got copied into three generators. This is the one implementation, and it applies the
denominator rule of `ar_gate` rather than leaving it to the reader.

    python3 tools/ar_read.py LOG SECTION METRIC ARM_HI ARM_LO [--denom METRIC]
    python3 tools/ar_read.py LOG --sections
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ar_gate import INFLATABLE, gate  # noqa: E402
from make_queue_numbers import ROOT, paired  # noqa: E402


def find(logname: str) -> pathlib.Path:
    p = ROOT / "report" / "data" / "queue" / logname
    return p if p.exists() else pathlib.Path(logname)


def load(path: pathlib.Path, sec: str, metric: str) -> dict:
    out, cur = {}, False
    for line in path.read_text().splitlines():
        if line.startswith("### "):
            cur = line.startswith(f"### {sec}") and line.rstrip().endswith(f"({metric})")
        elif cur and line.startswith("AR_ROW"):
            f = dict(p.split("=", 1) for p in line.split()[1:])
            key = next((v for k, v in f.items() if k not in ("arm", "mean", "vals")), "-")
            out[(f["arm"], key)] = [float(v) for v in f["vals"].split(",")]
    return out


def main() -> None:
    a = sys.argv[1:]
    path = find(a[0])
    if len(a) > 1 and a[1] == "--sections":
        for line in path.read_text().splitlines():
            if line.startswith("### "):
                print(line)
        return
    sec, metric, hi, lo = a[1], a[2], a[3], a[4]
    dmetric = a[a.index("--denom") + 1] if "--denom" in a else INFLATABLE.get(metric)
    d = load(path, sec, metric)
    dd = load(path, sec, dmetric) if dmetric else {}
    if not d:
        print(f"no rows for section {sec!r} metric {metric!r}")
        return
    print(f"--- {sec} {metric}: {hi} - {lo} ---")
    for n in sorted({k for arm, k in d if arm == hi}, key=lambda v: float(v) if v.replace(".", "").isdigit() else 0):
        if (lo, n) not in d:
            continue
        e, t, w, N = paired({"vals": d[(hi, n)]}, {"vals": d[(lo, n)]})
        base = sum(d[(lo, n)]) / len(d[(lo, n)])
        denom = None
        if dmetric and (hi, n) in dd and (lo, n) in dd:
            de = paired({"vals": dd[(hi, n)]}, {"vals": dd[(lo, n)]})[0]
            denom = (de, sum(dd[(lo, n)]) / len(dd[(lo, n)]))
        try:
            ok = gate(metric, e, t, w, N, base, denom=denom)
            mark = "GATED" if ok else "null"
        except Exception as exc:                       # noqa: BLE001
            mark = f"UNREADABLE ({type(exc).__name__})"
        pct = f"{100 * e / base:+.1f}%" if base else "n/a"
        extra = f"  denom={denom[0]:+.4f}" if denom else ""
        print(f"  {n:>6s}  base={base:9.4f}  d={e:+9.4f} ({pct:>9s})  t={t:9.2f}  {w}/{N}  {mark}{extra}")


if __name__ == "__main__":
    main()
