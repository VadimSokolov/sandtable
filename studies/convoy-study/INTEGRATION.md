# Convoy learning environment

This directory contains the complete study code and explanatory documents developed for issues #9–#19, including the experimental Herringbone, console-transfer adapters, natural Red priority comparison, curved-route diagnostics, viewer controls and illustration generator.

The import is based on the issue #19 checkpoint (`a799771`). It does not claim that issue #19, the production Herringbone feature, or all issue #18 requirements are complete. Experimental adapters remain separate from `src/sandtable`.

From the repository root, with NumPy/SciPy installed:

```bash
python tools/convoy_study.py run-all
python tools/convoy_study.py serve --port 8766
```

Open `http://127.0.0.1:8766/convoy_study.html`. If generated datasets are already available, `build` rebuilds the viewer without rerunning experiments. The displayed runs use seed 0; some comparisons also save 20- or 40-seed summaries. See each `START_HERE.md` for assumptions.

All Python and Markdown study files are versioned. Generated HTML, replay traces, result datasets and UI screenshots are retained locally but ignored by Git; regenerate them with `run-all`. The top-level PNG study illustrations and their original data-source inventory are retained as historical learning artifacts. `build_visuals.py` additionally needs Pillow and the historical report inputs; it is not required to run the viewer.

The two source files under `red_priority_18/branch_sources/` are preserved copies from the existing local issue #18 branch, with provenance in `provenance.json`. Runtime does not require that branch to exist. No complete #18 merge, lane blocking, ambush fire-control template or halt-exploitation cost is implied.

Validation scripts:

```bash
python studies/convoy-study/leader_12_17/check_motion.py
python studies/convoy-study/route_13/check_route.py
```

The sibling working checkout's uncommitted edits, deleted documents and generated outputs were not included or modified during this import. The original study folder is also retained.
