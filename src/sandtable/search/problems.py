"""The benchmark suite: mission-design search problems with independently established optima.

Each problem names a scenario, a set of design variables with their domains, a mission metric with
its direction, and the OPTIMUM that a separate, registered, full-tier study already found. The
answer key is the point of the suite. A search method is scored on whether it recovers that optimum
inside a budget, not on whether it improves its own objective, and the two are different questions:
a method can drive its objective a long way and land on the wrong design.

Provenance is carried on every problem as a string, and it is not decoration. A benchmark whose
answer key came from the same runs the methods are scored on would be circular, so each key names
the battery and job that produced it and none of those runs involved any search method at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Var:
    """One design variable. `values` for a discrete or categorical axis, `bounds` for continuous."""
    name: str
    values: tuple = ()
    bounds: tuple[float, float] | None = None
    kind: Literal["ordinal", "categorical", "continuous"] = "ordinal"

    def __post_init__(self):
        if not self.values and self.bounds is None:
            raise ValueError(f"{self.name}: needs values or bounds")
        if self.values and self.bounds is not None:
            raise ValueError(f"{self.name}: give values or bounds, not both")

    @property
    def size(self) -> int:
        return len(self.values) if self.values else 0


@dataclass(frozen=True)
class Problem:
    key: str
    scenario: str
    fixed: dict                       # held constant; defines the operating point
    variables: tuple[Var, ...]
    metric: str
    direction: Literal["max", "min"]
    optimum: dict                     # the answer key: variable -> value
    provenance: str
    note: str = ""
    tolerance: float = 0.0            # a design within this of the optimum's value counts as found

    @property
    def is_discrete(self) -> bool:
        return all(v.values for v in self.variables)

    @property
    def n_designs(self) -> int:
        if not self.is_discrete:
            return 0
        n = 1
        for v in self.variables:
            n *= v.size
        return n

    def designs(self) -> list[dict]:
        """Every design in a fully discrete space, in a fixed order."""
        if not self.is_discrete:
            raise ValueError(f"{self.key}: not a discrete space")
        out = [{}]
        for v in self.variables:
            out = [{**d, v.name: x} for d in out for x in v.values]
        return out

    def params(self, design: dict) -> dict:
        return {**self.fixed, **design}

    def is_optimum(self, design: dict) -> bool:
        # An empty key would make `all(...)` vacuously true and grade every method as perfect, so
        # a problem whose optimum is established by the truth table has to be asked through the
        # oracle rather than through this method.
        if not self.optimum:
            raise ValueError(f"{self.key}: no registered key; use oracle.best_design instead")
        return all(design.get(k) == v for k, v in self.optimum.items())


_BUFFER = {"control_mode": "direct", "queue_model": "buffer", "comms_level": 0}
_MIX = {"patience_spread": 12, "patience_shape": "twopoint"}

PROBLEMS: dict[str, Problem] = {}


def _add(p: Problem) -> None:
    PROBLEMS[p.key] = p


# ---------------------------------------------------------------------------------------------
# 1 and 2. Sizing the console's backlog. One integer, two fleets, two different answers. The
# smallest interesting problem in the suite and the one where a grid is genuinely competitive,
# which is why it is here: a benchmark on which the expensive method must not lose.
_add(Problem(
    key="qcap_uniform",
    scenario="scenarios/sc_span_control.json",
    fixed={**_BUFFER, "queue_policy": "blind", "n_blue": 16},
    variables=(Var("queue_capacity", values=(1, 2, 3, 4, 6, 8, 12)),),
    metric="served_per_step", direction="max",
    optimum={"queue_capacity": 2},
    provenance="ladder battery V4, job 9459669, full tier, 32 blocks x 64 reps",
    note="0.1461 0.1476 0.1299 0.0993 0.0314 0.0052 0.0029 over the seven capacities",
    tolerance=0.002,
))
_add(Problem(
    key="qcap_mixed",
    scenario="scenarios/sc_span_control.json",
    fixed={**_BUFFER, **_MIX, "queue_policy": "blind", "n_blue": 16},
    variables=(Var("queue_capacity", values=(1, 2, 3, 4, 6, 8, 12)),),
    metric="served_per_step", direction="max",
    optimum={"queue_capacity": 1},
    provenance="ladder battery V4, job 9459669, full tier, 32 blocks x 64 reps",
    note="0.0754 0.0623 0.0609 0.0619 0.0596 0.0369 0.0036; the optimum tightens on a mixed fleet",
    tolerance=0.002,
))

# ---------------------------------------------------------------------------------------------
# 3. The categorical axis. Seven queue disciplines, no ordering among them, which is where a GP on
# a one-hot encoding is at its weakest and a bandit is at its most natural.
_add(Problem(
    key="discipline",
    scenario="scenarios/sc_span_control.json",
    fixed={**_BUFFER, **_MIX, "queue_policy": "admit", "service_cv": 0.5,
           "admit_acuity": 1.0, "n_blue": 24},
    variables=(Var("queue_discipline",
                   values=("fcfs", "random", "hard_first", "easy_first", "edf",
                           "patient_first", "round_robin"),
                   kind="categorical"),),
    metric="served_per_step", direction="max",
    optimum={"queue_discipline": "edf"},
    provenance="roundrobin battery T1, job 9459574, full tier, 32 blocks x 64 reps",
    note="edf +0.0471 over fcfs, round_robin +0.0233, random -0.0082; edf leads on throughput",
    tolerance=0.005,
))

# ---------------------------------------------------------------------------------------------
# 4. The fleet-side lever, whose optimum depends on a console policy the search cannot see. Carried
# because a search method that reports one answer for a problem whose answer is conditional is
# making the mistake this suite exists to expose.
_add(Problem(
    key="reask_blind",
    scenario="scenarios/sc_span_control.json",
    fixed={**_BUFFER, "comms_level": 2, "queue_policy": "blind", "n_blue": 8},
    variables=(Var("reask_hold", values=(1.0, 2.0, 4.0, 8.0, 16.0)),),
    metric="blue_loss_frac", direction="min",
    optimum={"reask_hold": 2.0},
    provenance="fleet battery W3, job 9459816, full tier, 32 blocks x 64 reps",
    note="0.4576 0.4371 0.4553 0.4997 0.5328; an interior optimum on a console that cannot refuse",
    tolerance=0.01,
))
_add(Problem(
    key="reask_bound",
    scenario="scenarios/sc_span_control.json",
    fixed={**_BUFFER, "comms_level": 2, "queue_policy": "blind",
           "queue_capacity": 2, "n_blue": 8},
    variables=(Var("reask_hold", values=(1.0, 2.0, 4.0, 8.0, 16.0)),),
    metric="blue_loss_frac", direction="min",
    optimum={"reask_hold": 1.0},
    provenance="fleet battery W3, job 9459816, full tier, 32 blocks x 64 reps",
    note="0.4042 0.4192 0.4550 0.4894 0.5253; the same lever, the other answer, on a fixed console",
    tolerance=0.01,
))

# ---------------------------------------------------------------------------------------------
# 5. A two-dimensional mixed space: the requirements ladder crossed with the span it is sized for.
# The first problem in the suite where enumeration is expensive enough to be worth beating.
_add(Problem(
    key="ladder_span",
    scenario="scenarios/sc_span_control.json",
    fixed={**_BUFFER, **_MIX, "queue_policy": "blind"},
    variables=(Var("queue_capacity", values=(1, 2, 3, 4, 6, 8, 12)),
               Var("n_blue", values=(8, 12, 16, 24))),
    metric="served_per_step", direction="max",
    optimum={"queue_capacity": 1, "n_blue": 24},
    provenance="ladder battery V2 and V4, job 9459669, full tier",
    note="span is a design variable here rather than a sweep, so the optimum is the joint one",
    tolerance=0.004,
))


# ---------------------------------------------------------------------------------------------
# METRIC-PAIRED PROBLEMS, over the metric AND over the operating point.
#
# The first version of this block paired only on the metric, holding the operating point at the
# base problem's. Two things were wrong with that and both were caught before the sweep ran.
#
# The operating point was inherited rather than chosen, and at the inherited point `success` is
# pinned at its ceiling: measured over the qcap design set at sixteen assets the top two designs
# read 0.9900 and 0.9900, and on the discipline set at twenty-four they read 1.0000 and 1.0000
# with a per-mission standard deviation of exactly zero. A search method graded there is graded on
# noise. This is the first paper's censored-instrument defect, arriving inside the second paper's
# benchmark, and the fix is the first paper's own rule applied one level up: an axis is admissible
# only where it can actually rank the design set, and the operating point is CHOSEN so that every
# paired axis can.
#
# And pairing on the metric alone answers a smaller question than the one worth asking. The first
# measurement of replication cost read a spread of three orders of magnitude across metrics and was
# about to be reported as a property of the metrics. It is not. Measured at four operating points
# on one design set, the ordering of the axes CHANGES: the loss axis is the cheapest of the three
# at ten assets and by far the dearest at twelve. So the cost of estimating a mission metric is a
# property of the (metric, operating point) pair, not of the metric, and a benchmark that varies
# only one of the two cannot say so. The grid varies both.
#
# The keys here are established by the high-precision table rather than registered in advance,
# because no landed battery scored these axes at these points. `optimum={}` marks that, and
# `is_optimum` refuses rather than silently passing.
_COST_SPANS = (8, 10, 12, 16)
_COST_AXES = (("srv", "served_per_step", "max"),
              ("succ", "success", "max"),
              ("loss", "blue_loss_frac", "min"))

for _base, _tag in (("qcap_uniform", "qcap"), ("discipline", "disc")):
    _b = PROBLEMS[_base]
    for _span in _COST_SPANS:
        for _suffix, _metric, _dir in _COST_AXES:
            _add(Problem(
                key=f"{_tag}_s{_span}_{_suffix}",
                scenario=_b.scenario,
                fixed={**_b.fixed, "n_blue": _span},
                variables=_b.variables,
                metric=_metric, direction=_dir,
                optimum={},
                provenance=f"design set from {_base}; operating point chosen so that every paired "
                           f"axis can rank the set; key established by the high-precision table "
                           f"under common random numbers, and refused if the table cannot resolve "
                           f"its own top two",
                note=f"metric-paired twin of {_base} at n_blue={_span} on {_metric}",
                tolerance=_b.tolerance,
            ))


# ---------------------------------------------------------------------------------------------
# The prediction set, which is deliberately NOT part of the benchmark suite.
#
# CR-78 registers point predictions for an operating point nobody has simulated, made from a fit at
# an operating point somebody has. Those cells need to be addressable by key so the truth builder
# and the scorer can reach them, and they must not enter `PROBLEMS`, because the benchmark sweep
# enumerates `PROBLEMS` and a suite that grew between the launch of a run and the reading of it
# would not be the suite that was launched. So they live here and `get` falls through to them.
PREDICT: dict[str, Problem] = {}

for _base, _tag in (("qcap_uniform", "qcap"), ("discipline", "disc")):
    _b = PROBLEMS[_base]
    for _suffix, _metric, _dir in _COST_AXES:
        _p = Problem(
            key=f"{_tag}_s24_{_suffix}",
            scenario=_b.scenario,
            fixed={**_b.fixed, "n_blue": 24},
            variables=_b.variables,
            metric=_metric, direction=_dir,
            optimum={},
            provenance="CR-78 prediction set: values were written down before this table was "
                       "built, from a probit fit at n_blue=8 alone",
            note=f"CR-78 held-out operating point, {_metric}",
            tolerance=_b.tolerance,
        )
        PREDICT[_p.key] = _p


def get(key: str) -> Problem:
    if key in PROBLEMS:
        return PROBLEMS[key]
    if key in PREDICT:
        return PREDICT[key]
    raise KeyError(f"unknown problem {key!r}; have {sorted(PROBLEMS)}")
