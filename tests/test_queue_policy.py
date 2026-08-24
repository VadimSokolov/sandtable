"""CR-10: operator admission control, and the request accounting that measures it.

The published model (`queue_policy="blind"`) has an operator that works every request it
receives, including requests whose answer will arrive after the requester has given up. The
service slot is spent either way, so at large span the queue can collapse under its own
offered load. `refund` frees the slot; `admit` frees the slot *and* tells the requester, so
the agent goes autonomous after one round trip instead of after `patience` steps.

`blind` is the default, so every number recorded before this landed is unchanged.
"""
from __future__ import annotations

import numpy as np
import pytest

from sandtable import sim
from conftest import same_run
from sandtable.scenario import Scenario, load_scenario

BASE = "scenarios/sc_span_control.json"


def _run(seed=0, **params):
    scn = load_scenario(BASE)
    p = dict(scn.params)
    p.update(params)
    return sim.run_mission(Scenario(**{**scn.__dict__, "params": p}), seed=seed)


def _mean(metric, n=8, seeds=range(6), **params):
    return float(np.mean([_run(seed=s, **params)[metric] for s in seeds]))


def test_blind_is_the_default_and_byte_identical():
    """Naming the default policy explicitly must not move a single metric."""
    for s in range(4):
        a = _run(seed=s, control_mode="direct", n_blue=8)
        b = _run(seed=s, control_mode="direct", n_blue=8, queue_policy="blind")
        assert same_run(a, b)


def test_unknown_policy_is_rejected():
    with pytest.raises(ValueError, match="queue_policy"):
        _run(control_mode="direct", queue_policy="whatever")


def test_request_accounting_partitions_every_request():
    """Serviced + abandoned-at-the-operator + dropped-by-the-link accounts for all of them."""
    for lvl in (0, 3, 5):
        m = _run(control_mode="direct", n_blue=8, comms_level=lvl)
        total = m["operator_goodput"] + m["abandon_queue_frac"] + m["abandon_link_frac"]
        assert total == pytest.approx(1.0)


def test_supervisory_makes_no_requests():
    m = _run(control_mode="supervisory", n_blue=8)
    assert m["operator_goodput"] == 0.0
    assert m["abandon_queue_frac"] == 0.0
    assert m["abandon_link_frac"] == 0.0


def test_link_abandonment_rises_with_jamming():
    """The drop channel is the only route into `abandon_link_frac`, so it tracks the ladder."""
    clean = _mean("abandon_link_frac", control_mode="direct", n_blue=8, comms_level=0)
    jammed = _mean("abandon_link_frac", control_mode="direct", n_blue=8, comms_level=5)
    assert clean == 0.0
    assert jammed > 0.5


def test_freeing_the_slot_raises_goodput_at_saturated_span():
    """Not spending the server on abandoned work is what lets the queue drain."""
    blind = _mean("operator_goodput", control_mode="direct", n_blue=8, comms_level=0,
                  queue_policy="blind")
    refund = _mean("operator_goodput", control_mode="direct", n_blue=8, comms_level=0,
                   queue_policy="refund")
    admit = _mean("operator_goodput", control_mode="direct", n_blue=8, comms_level=0,
                  queue_policy="admit")
    assert refund > blind
    assert admit == pytest.approx(refund, abs=0.15)   # same server-side effect


def test_admission_control_empties_the_waiting_room():
    """`admit` differs from `refund` on the agent side: refused agents stop waiting."""
    refund = _mean("queue_depth_mean", control_mode="direct", n_blue=8, comms_level=0,
                   queue_policy="refund")
    admit = _mean("queue_depth_mean", control_mode="direct", n_blue=8, comms_level=0,
                  queue_policy="admit")
    assert admit < refund


def test_policies_agree_when_the_operator_is_never_saturated():
    """One agent, fast server: nothing is ever abandoned, so the policy cannot bite."""
    kw = dict(control_mode="direct", n_blue=1, comms_level=0, service_rate=1.0)
    for s in range(4):
        a = _run(seed=s, **kw, queue_policy="blind")
        b = _run(seed=s, **kw, queue_policy="admit")
        assert a["operator_goodput"] == 1.0
        assert same_run(a, b)
