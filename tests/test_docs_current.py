"""The documents that the next session reads must not lie to it.

An index written on day one and carried forward after it stopped being true is the same defect this
project catalogues in code, and it is more dangerous in a doc: the next autoresearch turn reads the
index and re-opens work that is already closed.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_conjecture_scoreboard_matches_the_sections():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_conjecture_index.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_conjecture_claims_a_verdict_from_a_run_that_has_not_landed():
    """A generator that guesses a verdict from prose once reported CR-75 as holding while its
    batteries were still queued. Verdicts are read from an explicit line; this pins that."""
    src = (ROOT / "tools" / "make_conjecture_index.py").read_text()
    assert "VERDICTS = [" not in src, "keyword sniffing is back; a verdict must be read, not guessed"
    assert 'UNREAD = "see section"' in src


def test_todo_does_not_call_landed_work_unstarted():
    t = (ROOT / "doc" / "sandtable-todo.md").read_text()
    for cr, mod in (("CR-1", "behavior.py"), ("CR-4", "metrics.py")):
        i = t.index(f"## {cr} ")
        head = t[i:i + 400]
        assert "not started" not in head, f"{cr} is implemented in src/sandtable/{mod}"
