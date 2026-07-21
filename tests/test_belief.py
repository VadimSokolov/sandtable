"""Tests for the optional belief/track layer (sandtable.belief).

Covers (1) opt-in gating, so the baseline path and its numbers are untouched; (2) determinism of a
belief-on run; (3) the track staleness mechanic (age, confidence decay, drop); and (4) that decoys
and jamming are first-order effects (they change mission outcomes), which is the whole point of
carrying a belief state rather than a probability-of-kill modifier.
"""
import numpy as np
import pytest

from sandtable import belief
from sandtable.entities import RED
from sandtable.scenario import build_entities, load_scenario
from sandtable.seeding import make_rng
from sandtable.sim import run_mission

UC3 = "scenarios/uc3_route_defilade.json"


def _belief(**kw):
    cfg = {"model": "tracks"}
    cfg.update(kw)
    return {"belief": cfg}


def test_optin_none_by_default():
    scn = load_scenario(UC3)
    ent = build_entities(scn, make_rng(0, scn.id))
    assert belief.build_tracks(scn, ent) is None                    # no belief param -> no tracks
    assert belief.build_tracks(scn.with_params(_belief()), ent) is not None


def test_baseline_deterministic():
    # With no belief param the run takes the baseline engagement path; identical across calls.
    assert run_mission(load_scenario(UC3), seed=7) == run_mission(load_scenario(UC3), seed=7)


def test_belief_on_deterministic():
    p = _belief(decoys=4, decoy_rate=0.6)
    assert run_mission(load_scenario(UC3), seed=5, params=p) == \
        run_mission(load_scenario(UC3), seed=5, params=p)


def test_track_ages_and_drops():
    scn = load_scenario(UC3).with_params(_belief(max_age=3, conf_decay=0.5))
    rng = make_rng(0, scn.id)
    ent = build_entities(scn, rng)
    tracks = belief.build_tracks(scn, ent)
    r = int(np.nonzero(ent.side == RED)[0][0])

    ent.seen[:] = False
    ent.seen[r] = True
    belief.update(ent, tracks, None, rng)                           # fresh detection -> live
    assert tracks.live[r] and tracks.age[r] == 0 and tracks.conf[r] == 1.0

    ent.seen[:] = False                                             # detection lapses
    belief.update(ent, tracks, None, rng)
    assert tracks.age[r] == 1 and tracks.conf[r] == pytest.approx(0.5)   # ages, confidence decays
    for _ in range(tracks.max_age):                                # exceed max_age -> drop
        belief.update(ent, tracks, None, rng)
    assert not tracks.live[r]


def _mean(params, key, seeds=range(10)):
    return float(np.mean([run_mission(load_scenario(UC3), seed=s, params=params)[key] for s in seeds]))


def test_decoys_are_first_order():
    # Decoys draw fire away from real targets: a shooter wastes shots on spoofed tracks, so the
    # opposing force takes fewer losses. A pure Pk modifier cannot produce this; it needs a belief
    # state that deception can corrupt.
    base = _mean(_belief(decoys=0), "blue_losses")
    spoofed = _mean(_belief(decoys=6, decoy_rate=0.95), "blue_losses")
    assert spoofed < base


def test_jamming_degrades_belief():
    # In UC3 the comms level touches nothing but the belief layer (no air relay, no operator), so
    # worse jamming can only act through track staleness: stale tracks miss, so the jammed side
    # inflicts fewer losses.
    clear = _mean(_belief(), "blue_losses")
    jammed = _mean({**_belief(), "comms_level": 5}, "blue_losses")
    assert jammed < clear
