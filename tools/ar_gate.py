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


def rate_floor(mpe: float = FULL_MPE, consoles: int = 1) -> float:
    """The absolute floor a rate effect must clear: a share of what the console can deliver."""
    return mpe * CAPACITY * consoles


class DenominatorUnchecked(RuntimeError):
    """Raised when an inflatable ratio is gated without its denominator contrast."""


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
