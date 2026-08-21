"""Blue behavior layer: control modality as a *repertoire*, not a gain (CR-1, CR-2, CR-4).

Without this layer the modality axis changes only a scalar. `c2.py` resolves direct versus
supervisory control into `control_quality`, `motion.py` reads it as a speed multiplier, and
`planning.py` gives every blue ground vehicle the same script either way. The consequence is a
teleoperated vehicle that keeps driving at 54.5% speed while its operator link is severed
(`0.35 + 0.65 * q_stall`), which is not what a teleoperated vehicle does.

This layer gives each agent a mode drawn from the Army's fielded behaviour set (teleoperation,
waypoint, leader-follow, sentry: see `doc/scenario.md`) and lets modality select the mode. The
quality gain survives unchanged and now multiplies a behaviour instead of standing in for one.

Scope boundary, to be stated wherever the intervention count is reported: this models how a UGV is
*tasked and commanded*, not how an off-road stack *drives*. SandTable has no LiDAR, no vehicle
dynamics, and no perception stack, so `interventions` counts comms and operator-queue contention.
Terrain enters that count only through the `terrain_demand` coupling of CR-15, as a modeled scalar
on the call-for-help rate. It is not comparable to a field-measured takeover rate either way.

The layer also accumulates hold *durations*, not just hold counts. An intervention rate alone is
ambiguous under jamming: heavier jamming makes each hold longer, which lowers the number of holds
per hour even as the vehicle spends more of the mission stopped. The duration counters let
`metrics` report the occupied fraction and the Olsen-Goodrich fan-out alongside the rate.

Opt-in via ``params["blue_behavior"]``; ``None`` leaves the pre-existing path byte-identical.

No change to `motion.py` is needed. `motion.step` clamps speed with ``v = min(v, dist/dt)``, so an
entity whose target is its own position moves exactly zero. Every hold in this module is expressed
that way, in planning-target space.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.entities import BLUE, GROUND, Entities
from sandtable.scenario import Scenario

TELEOP, WAYPOINT, LEADER_FOLLOW, SENTRY = 0, 1, 2, 3

_NAMES = {"teleop": TELEOP, "waypoint": WAYPOINT,
          "leader_follow": LEADER_FOLLOW, "sentry": SENTRY}


@dataclass
class Behavior:
    mode: int                     # primary mode for blue ground this scenario
    follow_mode: str              # "link" | "behavior"  (CR-3)
    teleop_stop: bool             # False reproduces the pre-CR-2 54.5%-speed behaviour
    track_timeout: int            # steps before a dead-reckoned leader track is stale
    state: np.ndarray             # int8 per entity: current mode
    holding: np.ndarray           # bool per entity: held in place this tick
    was_holding: np.ndarray       # bool per entity: held on the previous tick (edge detection)
    interventions: np.ndarray     # int32 per entity: recovery-trigger transitions (CR-4)
    hold_steps: np.ndarray        # int32 per entity: ticks spent held        (interaction time)
    alive_steps: np.ndarray       # int32 per entity: ticks spent alive and driving-eligible
    trk_x: np.ndarray             # follower's on-platform leader track (CR-3)
    trk_y: np.ndarray
    trk_vx: np.ndarray
    trk_vy: np.ndarray
    trk_age: np.ndarray           # int32: steps since the track was last refreshed


def build_behavior(scn: Scenario, ent: Entities) -> Behavior | None:
    """Build the behaviour layer, or None when the scenario does not opt in."""
    spec = scn.params.get("blue_behavior")
    if spec is None:
        return None

    if spec == "auto":
        # Modality selects the repertoire. Direct control means the vehicle is driven over the
        # link; supervisory means it runs onboard and the operator is consulted by exception.
        mode = TELEOP if scn.params.get("control_mode") == "direct" else WAYPOINT
    elif spec in _NAMES:
        mode = _NAMES[spec]
    else:
        raise ValueError(f"blue_behavior must be None, 'auto', or one of {sorted(_NAMES)}; got {spec!r}")

    n = ent.n
    # Only blue ground carries a behaviour. Everything else (red, and the UAS overwatch, which has
    # its own station logic in planning) stays on WAYPOINT so no target of theirs is ever overridden.
    state = np.full(n, WAYPOINT, np.int8)
    blue_ground = (ent.side == BLUE) & (ent.domain == GROUND)
    if mode == LEADER_FOLLOW:
        # The lead vehicle navigates; only followers hold a station on it.
        state[blue_ground & (ent.role == 1)] = LEADER_FOLLOW
    else:
        state[blue_ground] = mode

    return Behavior(
        mode=mode,
        follow_mode=str(scn.params.get("follow_mode", "behavior")),
        teleop_stop=bool(scn.params.get("teleop_stop", True)),
        track_timeout=int(scn.params.get("track_timeout", 40)),
        state=state,
        holding=np.zeros(n, bool),
        was_holding=np.zeros(n, bool),
        interventions=np.zeros(n, np.int32),
        hold_steps=np.zeros(n, np.int32),
        alive_steps=np.zeros(n, np.int32),
        trk_x=ent.x.copy(), trk_y=ent.y.copy(),
        trk_vx=np.zeros(n), trk_vy=np.zeros(n),
        trk_age=np.zeros(n, np.int32),
    )


def step(ent: Entities, bhv: Behavior, op, comms, scn: Scenario, k: int,
         rng: np.random.Generator) -> None:
    """Advance behaviour state one tick. Runs after `c2.step`, before `planning.step`.

    Writes `bhv.state` and `bhv.holding`; `planning.step` reads both. Counts a recovery-trigger
    transition on the rising edge of a hold, which is the intervention metric of CR-4.
    """
    blue_ground = (ent.side == BLUE) & (ent.domain == GROUND) & ent.alive
    bhv.was_holding = bhv.holding.copy()
    hold = np.zeros(ent.n, bool)

    if bhv.mode == TELEOP:
        # WAIT_FOR_OPERATOR and STOP_ON_LINK_LOSS collapse to the same observable condition:
        # `c2.step` records both a pending request and a dropped one as `await_until >= 0`.
        # A teleoperated vehicle with no answer coming back does not drive.
        if bhv.teleop_stop:
            hold = blue_ground & (ent.await_until >= 0)
        bhv.state = np.where(blue_ground & (ent.await_until >= 0), TELEOP, bhv.state)
    elif bhv.mode == SENTRY:
        hold = blue_ground.copy()

    elif bhv.mode == LEADER_FOLLOW:
        _follow(ent, bhv, comms, scn, rng, blue_ground)

    bhv.holding = hold
    # Rising edge only, so a long hold counts as one intervention rather than one per tick.
    np.add.at(bhv.interventions, np.nonzero(hold & ~bhv.was_holding)[0], 1)
    # Durations, for the fan-out estimate in `metrics` (CR-11). Counts only, no RNG.
    bhv.hold_steps += hold
    bhv.alive_steps += blue_ground


def _follow(ent: Entities, bhv: Behavior, comms, scn: Scenario,
            rng: np.random.Generator, blue_ground: np.ndarray) -> None:
    """Refresh each follower's picture of its leader (CR-3).

    Both variants draw the same number of uniforms so the two are paired on a shared seed:

    - ``follow_mode="link"``   the follower needs the leader's live pose over the comms link. A
      dropped message leaves it on a stale station, which drifts as the leader moves.
    - ``follow_mode="behavior"`` the follower keeps an on-platform track and dead-reckons the
      leader forward, so it continues the column with no live message.
    """
    dt = scn.dt
    for i in np.nonzero(blue_ground & (ent.role == 1))[0]:
        ldr = int(ent.leader[i])
        got = comms.delivered(rng)          # drawn on BOTH paths: keeps the streams aligned
        if ldr < 0 or not ent.alive[ldr]:
            # HALT_ON_LEADER_LOSS: no leader to follow, so hold the route independently.
            bhv.state[i] = WAYPOINT
            continue
        if bhv.follow_mode == "behavior" or got:
            bhv.trk_x[i], bhv.trk_y[i] = ent.x[ldr], ent.y[ldr]
            bhv.trk_vx[i] = ent.speed[ldr] * np.cos(ent.heading[ldr])
            bhv.trk_vy[i] = ent.speed[ldr] * np.sin(ent.heading[ldr])
            bhv.trk_age[i] = 0
        else:
            bhv.trk_age[i] += 1
            if bhv.follow_mode == "behavior":
                bhv.trk_x[i] += bhv.trk_vx[i] * dt      # dead reckon forward
                bhv.trk_y[i] += bhv.trk_vy[i] * dt
        if bhv.trk_age[i] > bhv.track_timeout:
            bhv.state[i] = WAYPOINT                      # track too stale to follow
            bhv.interventions[i] += 1
