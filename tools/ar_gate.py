"""The keep/discard gate, with the denominator rule made mechanical rather than remembered.

Every generator in this repository applies the same three-part gate: a paired t above the tier's
threshold, a majority of blocks agreeing with the effect's own sign, and an effect above the minimum
practical effect. Those three were written out separately in six generators, which is how a defect
in one of them survived in the others.

The fourth part is the one this module exists for. `operator_goodput` is `n_serviced / n_request`,
and every queue policy worth recommending moves the denominator: explicit admission control returns
a refused vehicle to autonomy after one round trip instead of after its full patience, so it asks
more often; a client-side rate rule suppresses requests by construction and so asks less. A contrast
between two arms whose request rates differ cannot be read on a ratio whose denominator is the
request count, in either direction. That rule cost this paper a headline, and it is the kind of rule
that is obeyed for a month and then forgotten, so it is enforced here instead: a metric in
`INFLATABLE` cannot be gated at all unless the caller supplies the paired contrast on its own
denominator and that contrast is itself below the minimum practical effect.

The failure mode is a raised exception, not a silently discarded result. A generator that reports a
goodput claim without checking the request rate is a bug in the generator, and a bug should stop the
build rather than produce a number nobody knows to doubt.
"""
from __future__ import annotations

# metric -> the metric whose paired contrast must be null for a claim on it to be readable.
INFLATABLE = {
    "operator_goodput": "requests_per_step",
    "serviced_frac": "requests_per_step",
    "wasted_frac": "requests_per_step",
}

# Full tier. Proxy tier runs at 2.10 on 16 blocks; a result read at one tier is never quoted at the
# other, so the tier is an argument rather than a default that can drift.
FULL_T, FULL_FRAC, FULL_MPE = 1.70, 0.60, 0.06

# A minimum practical effect stated as a share of the REFERENCE ARM's own level does no work in the
# regime this paper is about. At sixteen assets the blind console serves 0.0023 per step, so a
# +0.148 improvement reads as +6299% and every effect is material by construction: the floor is
# vacuous exactly where the console has collapsed, which is where the paper's claims live.
#
# For a rate the invariant is not the reference arm, which goes to zero, but the console's own
# capacity, which does not. `service_rate` decisions per step is what one console can deliver, so a
# rate effect is material at six percent of capacity and the floor scales with staffing rather than
# with whichever arm happened to be picked as the baseline. This does not apply to `success` or any
# other quantity bounded in [0, 1], where six percent already has a scale meaning.
CAPACITY = 0.15                      # operator service rate, decisions per step, per console
RATE_METRICS = {"served_per_step", "requests_per_step", "abandoned_per_step"}

# The null registry, and the rule it enforces.
#
# Four separate defects in this project have had one shape: a LEVEL compared against a reference
# treated as a constant when the reference is a function. Goodput's denominator moves with the
# treatment. The Fano estimator's power depends on the window. The arrival-excess floor depends on
# the channel dwell AND on the delivered rate. The tempo budget's reference speed depends on the
# hold fraction it was supposed to predict. Each was caught by a bench, and each bench was built
# only after someone demanded it.
#
# The rule, from adversarial review: a level may be gated only against a COMPUTED null, and the
# null is admissible only if every argument of the null function was logged in the same run.
# Otherwise the claim ships as a difference of two arms sharing the nuisance parameter, or as
# ungated description. A difference needs no registry entry, because pairing cancels the null.
#
# `None` means the metric is difference-only: it has no admissible level reading at all.
NULL_ARGS: dict[str, tuple[str, ...] | None] = {
    # A gated source's excess is neither one nor constant; tools/bench_gate.py computes it from
    # the dwell and the delivered rate, so both have to be in the same log.
    # Four arguments, not two. The bench moves 46 percent with the duty cycle, which the rung's
    # stationary drop rate sets, and the window is the axis the whole Fano episode turned on. A
    # constant shared by every arm in a battery is exactly where this genus hides: it looks like a
    # setting rather than an argument until one battery varies it.
    "arrival_excess": ("ge_burst_len", "arrival_rate", "comms_p_drop", "mult_window"),
    "arrival_multiplicity": ("ge_burst_len", "arrival_rate", "comms_p_drop", "mult_window"),
    "arrival_fano": ("ge_burst_len", "arrival_rate", "comms_p_drop", "fano_window"),
    # Serviced over requested has no admissible level: the denominator is a treatment effect.
    "operator_goodput": None,
}


def rate_floor(mpe: float = FULL_MPE, consoles: int = 1) -> float:
    """The absolute floor a rate effect must clear: a share of what the console can deliver."""
    return mpe * CAPACITY * consoles


class DenominatorUnchecked(RuntimeError):
    """Raised when an inflatable ratio is gated without its denominator contrast."""


class NullUnavailable(RuntimeError):
    """Raised when a LEVEL is gated against a null whose arguments were not logged."""


def check_level(metric: str, logged: set[str] | None) -> None:
    """Refuse a level reading whose null cannot be computed from what the run recorded.

    `logged` is the set of metric and sweep names present in the same battery section. Pass None
    only for a contrast that is a difference of two arms, where the null cancels by pairing.
    """
    if metric not in NULL_ARGS:
        return
    args = NULL_ARGS[metric]
    if args is None:
        raise NullUnavailable(
            f"{metric} has no admissible level reading: its reference is a treatment effect. "
            f"Report a difference of two arms, or use an absolute rate.")
    missing = sorted(set(args) - (logged or set()))
    if missing:
        raise NullUnavailable(
            f"{metric} is a level whose null depends on {', '.join(args)}, and this run did not "
            f"log {', '.join(missing)}. Log them, or report a paired difference instead, where "
            f"the null cancels.")


def gate(metric: str, eff: float, t: float, won: int, n: int, base: float,
         *, denom: tuple[float, float] | None = None, consoles: int = 1,
         t_min: float = FULL_T, frac: float = FULL_FRAC, mpe: float = FULL_MPE) -> bool:
    """True when the contrast survives the tier's gate.

    `eff`, `t`, `won`, `n` are `paired()`'s four returns. `base` is the reference arm's own level,
    which is what the minimum practical effect is relative to. `denom` is the (effect, base) pair
    of the denominator metric's own paired contrast, required for anything in `INFLATABLE`.
    """
    if metric in INFLATABLE:
        if denom is None:
            raise DenominatorUnchecked(
                f"{metric} is serviced-over-requested and every queue policy moves the denominator; "
                f"pass denom=(effect, base) for {INFLATABLE[metric]} or read the claim on an "
                f"absolute rate instead")
        d_eff, d_base = denom
        # A denominator that itself moved by more than the materiality floor makes the ratio
        # unreadable, whichever way the ratio went. Not a weaker claim: no claim.
        #
        # This test stays RELATIVE even though `requests_per_step` is a rate and rates are otherwise
        # floored against capacity below. The two floors answer different questions. What biases a
        # ratio is the denominator's PROPORTIONAL movement: a denominator that moves six percent
        # moves the ratio about six percent whatever the absolute rate is. Swapping this to the
        # capacity floor would let a proportionally large move through whenever the absolute rate
        # is small, which is precisely the collapsed regime where the ratio is least trustworthy.
        if d_base and abs(d_eff) > mpe * abs(d_base):
            return False
    if not (abs(t) > t_min and won >= frac * n):
        return False
    if metric in RATE_METRICS:
        # Anchored to capacity, not to a baseline that collapses. See RATE_METRICS above.
        return abs(eff) > rate_floor(mpe, consoles)
    return abs(eff) > mpe * abs(base)


def verdict(metric: str, eff: float, t: float, won: int, n: int, base: float, **kw) -> str:
    """The gate's answer as a word, for tables and logs."""
    if not gate(metric, eff, t, won, n, base, **kw):
        return "null"
    return "up" if eff > 0 else "down"
