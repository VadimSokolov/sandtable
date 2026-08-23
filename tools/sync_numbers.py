"""Rebuild the generated half of `report/results/numbers.txt` from `report/gen/*.tex`.

Non-negotiable 3 of the paper skill says every value in the manuscript traces to a line in
`results/numbers.txt`. That held while the numbers were appended by hand after each battery, and
stopped holding the moment there were sixteen generators: an audit found 165 macros used in the
manuscript with no line in the ledger, all of them from generators whose output had been appended
selectively rather than whole.

This does it mechanically, and only for the GENERATED half. Everything above the marker is
hand-written and is left alone; everything below is rewritten from `gen/` on each run, one block per
generated file, each headed by the tool that writes it so a number can be regenerated from its own
line. Run it after any `make_*_numbers.py`.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "=== GENERATED MACROS: rebuilt by tools/sync_numbers.py, do not edit below this line ==="


def source_of(stem: str) -> str:
    """Which tool writes gen/<stem>.tex. Read off the tools rather than kept in a table here, so a
    renamed generator cannot leave a stale attribution behind."""
    for t in sorted((ROOT / "tools").glob("*.py")):
        if f'"{stem}.tex"' in t.read_text():
            return f"tools/{t.name}"
    return "unknown"


def main() -> None:
    dst = ROOT / "report" / "results" / "numbers.txt"
    head = dst.read_text().split(MARK)[0].rstrip() + "\n"
    out = [head, "\n" + MARK + "\n"]
    total = 0
    for g in sorted((ROOT / "report" / "gen").glob("*.tex")):
        pairs = re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*?)\}\n", g.read_text())
        if not pairs:
            continue
        total += len(pairs)
        out.append(f"\n--- gen/{g.name}  ({len(pairs)} macros, source: {source_of(g.stem)}) ---\n")
        out += [f"  {k} = {v}\n" for k, v in sorted(pairs)]
    dst.write_text("".join(out))
    print(f"rebuilt {dst}: {total} generated macros from {len(list((ROOT / 'report' / 'gen').glob('*.tex')))} files")


if __name__ == "__main__":
    main()
