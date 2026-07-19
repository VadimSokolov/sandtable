"""Engagement: probability-of-kill attrition modulated by cover."""
from __future__ import annotations

import numpy as np

from sandtable.entities import BLUE, RED, Entities
from sandtable import engagement


def _duel(target_hp=1.0, cover_seen=True):
    """Blue shooter vs one red target 50 m away. Red is disarmed (pk 0) so it cannot return fire."""
    e = Entities.allocate(2)
    e.side[:] = [BLUE, RED]
    e.x[:] = [0.0, 50.0]
    e.y[:] = [0.0, 0.0]
    e.weapon_range[:] = [500.0, 0.0]
    e.pk_base[:] = [1.0, 0.0]
    e.hp[:] = [1.0, target_hp]
    e.seen[:] = [False, cover_seen]   # only the red target is on the SA picture
    return e


def test_shooter_reduces_seen_enemy_hp_over_steps(make_world):
    w = make_world(cover=0.0)
    e = _duel(target_hp=3.0)
    rng = np.random.default_rng(0)
    hps = [float(e.hp[1])]
    for _ in range(3):
        engagement.step(e, w, dt=1.0, rng=rng)
        hps.append(float(e.hp[1]))
    assert hps == [3.0, 2.0, 1.0, 0.0]      # pk == 1, cover == 0 -> one hit per step
    assert not bool(e.alive[1])             # target destroyed
    assert bool(e.alive[0]) and e.hp[0] == 1.0   # the unseen shooter took no fire


def test_unseen_enemy_is_not_engaged(make_world):
    w = make_world(cover=0.0)
    e = _duel(target_hp=1.0, cover_seen=False)   # red present and in range, but not detected
    engagement.step(e, w, dt=1.0, rng=np.random.default_rng(0))
    assert e.hp[1] == 1.0   # you may only fire on detected enemies


def test_cover_lowers_effective_pk(make_world):
    """Over many independent duels, cover at the target sharply reduces kills."""
    k = 600

    def kills(cover):
        w = make_world(width=k * 2000.0, cover=cover)
        e = Entities.allocate(2 * k)
        e.side[:k] = BLUE
        e.side[k:] = RED
        xs = np.arange(k) * 2000.0            # duels spaced 2 km apart so they never cross-engage
        e.x[:k] = xs
        e.x[k:] = xs + 50.0
        e.y[:] = 0.0
        e.weapon_range[:k] = 100.0            # each blue only ranges its own paired red
        e.weapon_range[k:] = 0.0
        e.pk_base[:k] = 0.5
        e.pk_base[k:] = 0.0
        e.seen[k:] = True
        e.hp[:] = 1.0
        engagement.step(e, w, dt=1.0, rng=np.random.default_rng(1))
        return int((~e.alive[k:]).sum())

    k_open = kills(0.0)     # pk = 0.5 -> ~300 kills
    k_cover = kills(0.9)    # pk = 0.05 -> ~30 kills
    assert k_open > 200
    assert k_cover < 100
    assert k_open > 2 * k_cover   # cover clearly protects


def test_dead_shooter_does_not_fire(make_world):
    w = make_world(cover=0.0)
    e = _duel(target_hp=1.0)
    e.alive[0] = False   # shooter is dead
    engagement.step(e, w, dt=1.0, rng=np.random.default_rng(0))
    assert e.hp[1] == 1.0   # a dead shooter deals no damage


def test_dead_target_is_not_shot(make_world):
    w = make_world(cover=0.0)
    e = _duel(target_hp=0.0)
    e.alive[1] = False   # target already dead
    engagement.step(e, w, dt=1.0, rng=np.random.default_rng(0))   # must not raise
    assert e.hp[1] == 0.0 and not bool(e.alive[1])
