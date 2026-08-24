"""The graph reading of a formation, and the disagreement it exists to expose."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import same_run
from sandtable import formation_metrics as fm
from sandtable.scenario import load_scenario
from sandtable.sim import run_mission

SCN = load_scenario("scenarios/sc_span_control.json")
FORM = {"control_mode": "supervisory", "blue_behavior": "leader_follow", "follow_mode": "link",
        "follow_topology": "star", "comms_level": 0, "n_blue": 8}


def _line(n, gap=100.0):
    return np.arange(n, dtype=float) * gap, np.zeros(n)


def _ring(n, r=100.0):
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    return r * np.cos(a), r * np.sin(a)


def test_a_complete_graph_is_maximally_connected():
    for n in (3, 5, 8, 12):
        x, y = _ring(n)
        adj = fm.comms_graph(x, y, 1e6)
        assert fm.vertex_connectivity(adj) == n - 1
        assert fm.algebraic_connectivity(adj) == pytest.approx(float(n), abs=1e-9)
        assert fm.tolerated_faults(n - 1) == (n - 2) // 2


def test_the_path_graph_is_the_disagreement():
    """CR-8's registered counterexample and the reason both readings are carried. A column of
    vehicles in single file is one cut away from being severed however long it is, while the
    eigenvalue keeps reporting that it is getting steadily worse. Only one of those is a
    requirement."""
    fied = []
    for n in (3, 5, 8, 12, 16):
        x, y = _line(n)
        adj = fm.comms_graph(x, y, 150.0)
        assert fm.vertex_connectivity(adj) == 1, f"path of {n} is not 1-connected"
        assert fm.tolerated_faults(1) == 0
        fied.append(fm.algebraic_connectivity(adj))
    assert all(a > b for a, b in zip(fied, fied[1:])), "the eigenvalue did not fall with length"
    assert fied[0] > 20 * fied[-1]


def test_a_star_tolerates_nobody_however_large_it_is():
    """The topology this project's own leader-follower arm names. A hub is a cut vertex, so a star
    scores zero tolerated compromises at every size. The adjacency is built directly rather than
    from positions, because a disc graph on a circle cannot realise a star above five spokes: rim
    neighbours are closer to each other than to the hub, so the geometry closes the rim into a
    wheel whether the formation meant it to or not. That is worth knowing separately and is checked
    below; it is not what this test is about."""
    for n in (4, 8, 16):
        adj = np.zeros((n, n), dtype=np.int8)
        adj[0, 1:] = 1
        adj[1:, 0] = 1
        assert fm.vertex_connectivity(adj) == 1
        assert fm._vertex_connectivity_exact(adj) == 1
        assert fm.tolerated_faults(fm.vertex_connectivity(adj)) == 0


def test_a_disc_graph_cannot_realise_a_large_star():
    """Geometry constrains which topologies a formation can actually fly. Spokes on a circle at a
    range that reaches the hub necessarily reach each other once there are six or more of them, so
    a commanded star becomes a wheel and its vertex connectivity jumps from one to three. A
    formation requirement written on a topology has to be checkable against the geometry that
    produces it."""
    for spokes, expect in ((4, 1), (7, 3)):
        a = np.linspace(0.0, 2 * np.pi, spokes, endpoint=False)
        x = np.concatenate([[0.0], 100.0 * np.cos(a)])
        y = np.concatenate([[0.0], 100.0 * np.sin(a)])
        adj = fm.comms_graph(x, y, 110.0)
        assert fm.vertex_connectivity(adj) == expect


def test_a_severed_formation_reads_zero_on_both():
    x = np.array([0.0, 50.0, 5000.0, 5050.0])
    y = np.zeros(4)
    adj = fm.comms_graph(x, y, 100.0)
    assert fm.vertex_connectivity(adj) == 0
    assert fm.algebraic_connectivity(adj) == pytest.approx(0.0, abs=1e-9)
    assert fm.score(x, y, 100.0)["disconnected"] == 1.0


def test_the_fast_path_and_the_textbook_path_agree():
    """The fast path is a library call and the slow one is this project's own max flow. Neither is
    the guard on its own; the agreement is."""
    rng = np.random.default_rng(11)
    for _ in range(120):
        n = int(rng.integers(2, 13))
        x, y = rng.normal(0, 200, n), rng.normal(0, 200, n)
        adj = fm.comms_graph(x, y, float(rng.uniform(80.0, 500.0)))
        assert fm.vertex_connectivity(adj) == fm._vertex_connectivity_exact(adj)


def test_the_fault_count_follows_the_two_f_plus_one_rule():
    for kappa, f in ((0, 0), (1, 0), (2, 0), (3, 1), (4, 1), (5, 2), (7, 3), (15, 7)):
        assert fm.tolerated_faults(kappa) == f
        if f > 0:
            assert kappa >= 2 * f + 1            # the sufficiency direction
            assert 2 * (f + 1) + 1 > kappa       # and it is the largest such f


def test_the_graph_readings_are_off_by_default_and_cost_nothing():
    for s in range(3):
        a = run_mission(SCN.with_params({**SCN.params, **FORM}), seed=s)
        b = run_mission(SCN.with_params({**SCN.params, **FORM, "graph_range": 0.0}), seed=s)
        assert same_run(a, b)
        for k in ("fleet_fiedler_mean", "fleet_kappa_mean", "fleet_faults_mean",
                  "fleet_disconnected_frac"):
            assert a[k] == 0.0


def test_turning_them_on_moves_them_with_the_commanded_spread():
    """A dose-response check on the wiring, not on the metric. A formation commanded wider must read
    less connected at a fixed radio range, or the sampler is not seeing the formation."""
    def g(spread):
        return run_mission(SCN.with_params({**SCN.params, **FORM, "formation_spread": spread,
                                            "graph_range": 400.0}), seed=3)
    tight, wide = g(60), g(300)
    assert tight["fleet_kappa_mean"] > wide["fleet_kappa_mean"]
    assert tight["fleet_fiedler_mean"] > wide["fleet_fiedler_mean"]
    assert wide["fleet_disconnected_frac"] > tight["fleet_disconnected_frac"]
