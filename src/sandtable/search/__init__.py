"""Design-space search over a fast stochastic mission simulator.

The question this package is built to answer is not "what is the best mission design" but "which
family of search methods finds it, on what kind of space, under a fixed budget of mission
replications". Three families are compared on equal terms:

  * enumeration      -- grid, random, Latin hypercube. The baselines that are usually skipped and
                        that surprisingly often win.
  * Bayesian         -- a Gaussian-process surrogate with an acquisition function, the standard
                        answer, run through `polarisopt` and `botorch`.
  * bandit           -- successive halving, Thompson sampling, UCB. Mission design over a small
                        mixed space with heavy replication noise is a best-arm identification
                        problem before it is an optimization problem, and this package exists partly
                        to test whether treating it as one does better.

What makes the comparison worth running here rather than on synthetic test functions is the answer
key. Every problem in `problems.py` has an optimum established independently, at a fixed statistical
tier, by a registered study that had no view of these searches, so "did the method find it" is a
question with a real answer rather than a self-reported one.
"""
from __future__ import annotations

from .problems import PROBLEMS, Problem, get                    # noqa: F401
