"""The documents that the next session reads must not lie to it.

An index written on day one and carried forward after it stopped being true is the same defect this
project catalogues in code, and it is more dangerous in a doc: the next autoresearch turn reads the
index and re-opens work that is already closed.
"""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The cluster copy carries code and results but not the manuscripts or the doc tree, because
# neither ever runs there. These checks read those files, so they skip rather than fail where the
# tree they check was deliberately not synced.
needs_docs = pytest.mark.skipif(not (ROOT / "doc").is_dir(), reason="doc tree not present")
needs_paper = pytest.mark.skipif(not (ROOT / "paper-search" / "main.tex").is_file(),
                                 reason="paper two not present")


@needs_docs
def test_conjecture_scoreboard_matches_the_sections():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_conjecture_index.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


@needs_docs
def test_rebuilding_the_scoreboard_once_is_enough():
    """One rebuild must leave the index current, not merely closer to current.

    The table prints the line number of each section and sits above every section it points at, so
    a table whose height changes moves its own targets. A single splice therefore writes line
    numbers that were true of the document as it stood BEFORE the splice, and `--check` fails on a
    file that was just regenerated. That is not a stale doc, it is a generator that is an input to
    itself, and the fix is a fixed point rather than a second pass. This starts from a document
    with no table at all, which is the worst case for height change, and it fails on the one-pass
    version of the generator.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import make_conjecture_index as gen

    stripped = gen.DOC.read_text()
    a, b = stripped.index(gen.BEGIN), stripped.index(gen.END) + len(gen.END)
    stripped = stripped[:a] + stripped[b:]

    settled = gen.settle(stripped)
    assert gen.splice(settled) == settled, "a rebuild of the rebuilt index still moves it"


def test_no_conjecture_claims_a_verdict_from_a_run_that_has_not_landed():
    """A generator that guesses a verdict from prose once reported CR-75 as holding while its
    batteries were still queued. Verdicts are read from an explicit line; this pins that."""
    src = (ROOT / "tools" / "make_conjecture_index.py").read_text()
    assert "VERDICTS = [" not in src, "keyword sniffing is back; a verdict must be read, not guessed"
    assert 'UNREAD = "see section"' in src


@needs_docs
def test_todo_does_not_call_landed_work_unstarted():
    t = (ROOT / "doc" / "sandtable-todo.md").read_text()
    for cr, mod in (("CR-1", "behavior.py"), ("CR-4", "metrics.py")):
        i = t.index(f"## {cr} ")
        head = t[i:i + 400]
        assert "not started" not in head, f"{cr} is implemented in src/sandtable/{mod}"


@needs_paper
def test_no_number_in_paper_two_is_typed_rather_than_generated():
    """Every value in the manuscript must come from a macro, so regenerating the sweep updates it.

    This is not style. Twice in one session a number typed into the prose survived the sweep that
    superseded it: a top-rung effect of 0.018 stayed after the effect became -0.0097, and a claim
    that seven success spans were "comparable" to 0.156 stayed after they turned out to run down to
    0.003. A typed number cannot be regenerated and so cannot be found stale by any check but a
    reader's memory.
    """
    import re
    tex = (ROOT / "paper-search" / "main.tex").read_text()
    body = "\n".join(ln for ln in tex.split("\n") if not ln.lstrip().startswith("%"))
    # A decimal or a multi-digit integer that is not part of a macro name, a label, or a length.
    bad = [m.group(0) for m in re.finditer(r"(?<![\w.\\{[])\d+\.\d+(?![\w}\]])", body)]
    assert not bad, f"typed numbers in paper two: {bad}"


def test_the_benchmark_inventory_comes_from_the_registry_not_the_filesystem():
    """A truth table saved next to the others must not join the published benchmark.

    The predict grid writes its tables into the same directory. Globbing it grew the reported
    problem count from thirty to thirty-two, and two of the added cells sit at the success ceiling
    with a top-two gap and standard error of exactly zero, so they would also have taken a ratio to
    a denominator with no bound.
    """
    src = (ROOT / "tools" / "make_bench_numbers.py").read_text()
    assert "if f.stem not in PROBLEMS:" in src, "the truth glob is not scoped to the registry"


@needs_paper
def test_the_superseded_sweep_is_rescored_rather_than_remembered():
    """The paper reports a verdict that changed when the replicate count rose. The earlier number
    is regenerated from the archived sweep through the same gate, not carried in the prose."""
    src = (ROOT / "tools" / "make_results_numbers.py").read_text()
    assert "RsPrevCrossTopEff" in src and "--prev" in src
    assert "RsOldLadderShort" in src and "short_of_separation" in src
    tex = (ROOT / "paper-search" / "main.tex").read_text()
    assert r"\RsPrevCrossTopEff{}" in tex, "the superseded effect is not read from its macro"
