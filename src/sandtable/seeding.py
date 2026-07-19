"""Reproducible RNG harness.

One `numpy.random.Generator` per mission run, seeded by identity (seed + a sub-stream id) so a
given (seed, sub) always reproduces the same run. This is what makes the simulator a clean,
deterministic function for the optimizer, and enables Common Random Numbers across candidate
designs (reuse the same seeds so paired comparisons have correlated noise). See
`references/palette` note in the plan: never use the global `np.random`, never `root + id`.
"""
from __future__ import annotations

import numpy as np


def make_rng(seed: int, sub: int = 0) -> np.random.Generator:
    """Return an independent Generator for run identity (seed, sub).

    `sub` distinguishes independent sub-streams (e.g. a Monte-Carlo replication index or a
    scenario id) without the bias of adding it to the seed. Uses SeedSequence list-seeding.
    """
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(sub)]))


def spawn_streams(seed: int, n: int) -> list[np.random.Generator]:
    """Return `n` independent Generators from one root seed (for replication ensembles)."""
    return [np.random.default_rng(s) for s in np.random.SeedSequence(int(seed)).spawn(n)]
