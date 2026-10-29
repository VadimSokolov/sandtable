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
from typing import Any

import numpy as np

from sandtable.convoy import ROLE_SECURITY
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
    topology: str                 # "star" | "chain": what a follower stations on
    sense_range: float            # metres a behaviour follower can see the vehicle ahead
    outage: int                   # forced refresh interval: track age sawtooths 0..outage
    trk_err_sum: np.ndarray       # float per entity: summed |track - truth| over followed steps
    trk_steps: np.ndarray         # int32 per entity: follower steps with a reference to hold
    trk_stale_steps: np.ndarray   # int32 per entity: follower steps running on a dead-reckoned track
    trk_lost_steps: np.ndarray    # int32 per entity: follower steps handed back to waypoint
    st_err_sum: np.ndarray        # float per entity: summed |position - commanded station|
    st_along_sum: np.ndarray      # float per entity: the same error resolved along the reference's
    st_cross_sum: np.ndarray      # heading, and onto its normal
    st_steps: np.ndarray          # int32 per entity: steps with a commanded station
    prev_heading: np.ndarray      # float per entity: heading at the previous tick
    turn_sum: np.ndarray          # float per entity: summed |heading change| (rad)
    turn_steps: np.ndarray        # int32 per entity: ticks the turn sum was taken over
    # Contact reaction (Issue #12). All None / zero unless `convoy.contact_reaction` is declared.
    contact: dict | None = None   # resolved reaction rule (see convoy.resolve_contact_reaction)
    fired_at: np.ndarray | None = None   # bool per entity: targeted by a shooter on the last engagement
    heads: np.ndarray | None = None      # int indices of the march-unit heads at build time
    heads_alive: np.ndarray | None = None
    in_contact: bool = False
    last_trigger_k: int = -1
    contact_count: int = 0        # rising edges of the contact state
    contact_steps: int = 0        # ticks spent in contact
    first_contact_step: int = -1
    halt_steps: int = 0           # vehicle-ticks held by the reaction
    # Autonomous march unit (Issue #14). "manned_only" never promotes an unmanned vehicle to head.
    succession: str = "any"
    headless_steps: int = 0       # follower-ticks with no living manned head (manned_only only)
    # Leader-loss policy (Issue #17). None unless `convoy.leader_loss_policy` is declared and not legacy.
    ll: dict | None = None        # resolved policy (see convoy.resolve_leader_loss)
    ll_head: np.ndarray | None = None      # int per march unit: current head entity, -1 when headless
    ll_left: np.ndarray | None = None      # int per march unit: handoff steps remaining, -1 = none pending
    ll_halted: np.ndarray | None = None    # bool per march unit: held by the halt policy
    ll_hold: np.ndarray | None = None      # int per march unit: steps held
    ll_clear: np.ndarray | None = None     # int per march unit: consecutive steps with no shooter in range
    ll_done: np.ndarray | None = None      # bool per march unit: no head will be chosen again
    leaderless_steps: int = 0     # unit-steps with a living vehicle and no living head
    ll_halt_steps: int = 0        # vehicle-steps held by the policy
    ll_handoffs: int = 0          # completed promotions or absorptions
    first_leader_loss_step: int = -1


def build_behavior(scn: Scenario, ent: Entities) -> Behavior | None:
    """Build the behaviour layer, or None when the scenario does not opt in."""
    spec = scn.params.get("blue_behavior")
    from sandtable.convoy import resolve_contact_reaction, resolve_convoy_spec, resolve_leader_loss
    cspec = resolve_convoy_spec(scn.params)
    reaction = resolve_contact_reaction(cspec)
    ll = resolve_leader_loss(cspec)
    arm = (cspec or {}).get("autonomy_arm")
    if spec is None and arm == "autonomous_march_unit":
        spec = "leader_follow"  # the unmanned trucks station on their control vehicle
    elif spec is None and arm == "manned":
        spec = "leader_follow"  # manned vehicles hold station with human perception
    elif spec is None and ll is not None:
        spec = "leader_follow"  # a leader-loss policy needs followers that station on a head
    elif spec is None and reaction is not None:
        spec = "waypoint"       # the reaction holds vehicles through the behaviour layer
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

    default_follow_mode = "human" if arm == "manned" else "behavior"
    follow_mode = str(scn.params.get("follow_mode", default_follow_mode))

    return Behavior(
        mode=mode,
        follow_mode=follow_mode,
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
        # The topology DEFAULTS TO THE CHANNEL rather than to a value, because the channel is what
        # decides which vehicle can be followed at all: a broadcast pose is the column leader's, a
        # sensor return is the vehicle immediately ahead. Setting it explicitly breaks that tie and
        # is how the 2x2 that separates channel from geometry is run.
        topology=str(scn.params.get(
            "follow_topology",
            "star" if follow_mode == "link" else "chain")),
        sense_range=float(scn.params.get("follow_sense_range", 250.0)),
        # The disturbance measured in its own coordinate (CR-57). A channel produces outages of a
        # DISTRIBUTION; a specification is written about a LENGTH. With `follow_outage = a` the
        # refresh arrives once every a+1 steps whatever the channel is doing, so the track age is a
        # sawtooth from 0 to a with mean a/2, exactly and by construction. Zero leaves the channel
        # in charge and is bit-identical to the path measured before this existed.
        outage=int(scn.params.get("follow_outage", 0)),
        trk_err_sum=np.zeros(n), trk_steps=np.zeros(n, np.int32),
        trk_stale_steps=np.zeros(n, np.int32), trk_lost_steps=np.zeros(n, np.int32),
        st_err_sum=np.zeros(n), st_along_sum=np.zeros(n), st_cross_sum=np.zeros(n),
        st_steps=np.zeros(n, np.int32),
        # How hard the thing being tracked is to extrapolate. A dead-reckoned track is a constant
        # velocity assumption, so its error is a function of how much the reference TURNS, and a
        # follow-channel result that does not report the turn rate is not reporting its own
        # covariate. Radians per tick, over blue ground.
        prev_heading=ent.heading.copy(), turn_sum=np.zeros(n), turn_steps=np.zeros(n, np.int32),
        **_contact_fields(ent, reaction),
        **_leader_loss_fields(ent, ll),
        succession=str((cspec or {}).get("succession")
                       or ("manned_only" if arm == "autonomous_march_unit" else "any")),
    )


def _contact_fields(ent: Entities, reaction: dict | None) -> dict:
    """Constructor arguments for the contact reaction; empty when it is not declared."""
    if reaction is None:
        return {}
    blue_ground = (ent.side == BLUE) & (ent.domain == GROUND)
    heads = np.nonzero(blue_ground & (ent.march_unit >= 0) & (ent.leader == -1))[0]
    return dict(contact=reaction, fired_at=np.zeros(ent.n, bool), heads=heads,
                heads_alive=ent.alive[heads].copy())


def _leader_loss_fields(ent: Entities, ll: dict | None) -> dict:
    """Constructor arguments for the leader-loss policy; empty when it is not declared."""
    if ll is None:
        return {}
    nu = int(ent.march_unit.max()) + 1 if (ent.march_unit >= 0).any() else 0
    head = np.full(nu, -1, np.int64)
    blue_ground = (ent.side == BLUE) & (ent.domain == GROUND)
    for mu in range(nu):
        idx = np.nonzero(blue_ground & (ent.march_unit == mu) & (ent.leader == -1))[0]
        if idx.size:
            head[mu] = idx[0]
    return dict(ll=ll, ll_head=head, ll_left=np.full(nu, -1, np.int64), ll_halted=np.zeros(nu, bool),
                ll_hold=np.zeros(nu, np.int64), ll_clear=np.zeros(nu, np.int64), ll_done=np.zeros(nu, bool))


def _eligible(ent: Entities, bhv: Behavior, living: np.ndarray) -> np.ndarray:
    """Living vehicles that may take over as head (crewed only under `manned_only`)."""
    return living[ent.crew[living] > 0] if bhv.succession == "manned_only" else living


def _go_independent(ent: Entities, bhv: Behavior, members: np.ndarray) -> None:
    """Every survivor drives the route on its own (the `continue` behaviour)."""
    ent.role[members] = 0
    ent.leader[members] = -1
    bhv.state[members] = WAYPOINT


def _promote(ent: Entities, bhv: Behavior, mu: int, living: np.ndarray) -> bool:
    """Make the earliest eligible survivor the head. False when nobody is eligible."""
    pool = _eligible(ent, bhv, living)
    if pool.size == 0:
        return False
    new_head = int(pool[0])
    old = int(np.nonzero(ent.march_unit == mu)[0][0])
    ent.role[new_head] = 0
    ent.leader[new_head] = -1
    bhv.state[new_head] = WAYPOINT
    if ent.speed_cap[old] < np.inf:
        ent.speed_cap[new_head] = ent.speed_cap[old]
    for foll in living[living != new_head]:
        ent.role[foll] = 1
        ent.leader[foll] = new_head
    bhv.ll_head[mu] = new_head
    bhv.ll_handoffs += 1
    return True


def _absorb(ent: Entities, bhv: Behavior, mu: int, living: np.ndarray) -> bool:
    """Attach the survivors to the tail of the nearest living unit in the same serial."""
    ser = ent.serial[living[0]]
    best, best_d = -1, np.inf
    for other in range(len(bhv.ll_head)):
        h = int(bhv.ll_head[other])
        if other == mu or h < 0 or not ent.alive[h] or ent.serial[h] != ser:
            continue
        if bhv.succession == "manned_only" and ent.crew[h] <= 0:
            continue                # an unmanned head cannot take over another unit's followers
        d = float(np.hypot(ent.x[h] - ent.x[living[0]], ent.y[h] - ent.y[living[0]]))
        if d < best_d:
            best, best_d = h, d
    if best < 0:
        return False
    target_mu = int(ent.march_unit[best])
    ent.march_unit[living] = target_mu
    ent.role[living] = 1
    ent.leader[living] = best
    bhv.state[living] = LEADER_FOLLOW
    bhv.ll_head[mu] = best          # the survivors are led again, so they are not counted leaderless
    bhv.ll_handoffs += 1
    return True


def _shooter_in_range(ent: Entities, members: np.ndarray) -> bool:
    shooters = np.nonzero(ent.alive & (ent.side != BLUE) & (ent.weapon_range > 0) & (ent.pk_base > 0))[0]
    if shooters.size == 0 or members.size == 0:
        return False
    d = np.hypot(ent.x[members][:, None] - ent.x[shooters][None, :],
                 ent.y[members][:, None] - ent.y[shooters][None, :])
    return bool((d <= ent.weapon_range[shooters][None, :]).any())


def _finish_loss(ent: Entities, bhv: Behavior, mu: int, living: np.ndarray, how: str) -> None:
    """Complete the handoff of unit `mu`; falls back to `continue` when it cannot be done."""
    ok = _absorb(ent, bhv, mu, living) if how == "absorb" else _promote(ent, bhv, mu, living)
    if not ok:
        _go_independent(ent, bhv, living)
        bhv.ll_done[mu] = True


def _update_leader_loss(ent: Entities, bhv: Behavior, k: int, hold: np.ndarray) -> None:
    """Leader-loss policy for every march unit (Issue #17). Draws no random numbers.

    A loss is a head that was alive at the last check and is dead now, so it has the same one-tick
    latency as the `lead_lost` contact trigger. `halt` writes the unit's survivors into `hold`.
    """
    ll = bhv.ll
    pol = ll["policy"]
    blue = (ent.side == BLUE) & (ent.domain == GROUND) & ent.alive
    for mu in range(len(bhv.ll_head)):
        living = np.nonzero(blue & (ent.march_unit == mu))[0]
        if living.size == 0 or bhv.ll_done[mu]:
            if bhv.ll_done[mu] and living.size:
                bhv.leaderless_steps += 1
            continue
        head = int(bhv.ll_head[mu])
        if head >= 0 and not ent.alive[head]:
            bhv.ll_head[mu] = head = -1
            if bhv.first_leader_loss_step < 0:
                bhv.first_leader_loss_step = k
            if pol == "continue":
                _go_independent(ent, bhv, living)
                bhv.ll_done[mu] = True
            elif pol == "halt":
                bhv.ll_halted[mu], bhv.ll_hold[mu], bhv.ll_clear[mu] = True, 0, 0
            elif ll["handoff_steps"] == 0:
                _finish_loss(ent, bhv, mu, living, pol)
            else:
                bhv.ll_left[mu] = ll["handoff_steps"]
        elif head < 0 and bhv.ll_left[mu] > 0:
            bhv.ll_left[mu] -= 1
            if bhv.ll_left[mu] == 0:
                bhv.ll_left[mu] = -1
                _finish_loss(ent, bhv, mu, living, pol)
        if bhv.ll_halted[mu]:
            bhv.ll_hold[mu] += 1
            bhv.ll_clear[mu] = 0 if _shooter_in_range(ent, living) else bhv.ll_clear[mu] + 1
            n, t = ll["clear_steps"], ll["max_hold_steps"]
            if (n is not None and bhv.ll_clear[mu] >= n) or (t is not None and bhv.ll_hold[mu] >= t):
                bhv.ll_halted[mu] = False
                _finish_loss(ent, bhv, mu, living, "promote")
            else:
                hold[living] = True
                bhv.ll_halt_steps += int(living.size)
        if bhv.ll_head[mu] < 0:
            bhv.leaderless_steps += 1


def _update_contact(ent: Entities, bhv: Behavior, scn: Scenario, k: int, world: Any,
                    hold: np.ndarray) -> None:
    """Trigger, hold and release for the convoy contact reaction. Draws no random numbers.

    One rule for the whole convoy: contact is declared by any vehicle, and is instantaneous across
    the column (comms effects on the alert are out of scope here). `receive_fire` reads the previous
    engagement's target set, so it has one tick of latency.
    """
    rx = bhv.contact
    veh = (ent.side == BLUE) & (ent.domain == GROUND) & ent.alive & (ent.convoy_role >= 0)
    trig = False
    if "receive_fire" in rx["triggers"]:
        trig = trig or bool((bhv.fired_at & veh).any())
    if "lead_lost" in rx["triggers"] and bhv.heads.size:
        now = ent.alive[bhv.heads]
        trig = trig or bool((bhv.heads_alive & ~now).any())
    bhv.heads_alive = ent.alive[bhv.heads].copy() if bhv.heads.size else bhv.heads_alive
    if not trig and "detect_range" in rx["triggers"] and veh.any():
        red = (ent.side != BLUE) & ent.alive & (ent.domain == GROUND) & ent.seen
        if red.any():
            vi, ri = np.nonzero(veh)[0], np.nonzero(red)[0]
            near = np.hypot(ent.x[vi][:, None] - ent.x[ri][None, :],
                            ent.y[vi][:, None] - ent.y[ri][None, :]) <= rx["range_m"]
            if near.any() and world is not None and getattr(world, "buildings", None) is not None:
                near = near & world.los(ent.x[vi][:, None], ent.y[vi][:, None],
                                        ent.x[ri][None, :], ent.y[ri][None, :])
            trig = bool(near.any())

    if trig:
        bhv.last_trigger_k = k
    was = bhv.in_contact
    if rx["release_rule"] == "leader_policy" and bhv.ll_halted is not None:
        bhv.in_contact = trig or (was and bool(bhv.ll_halted.any()))
    else:
        bhv.in_contact = trig or (was and (k - bhv.last_trigger_k) * scn.dt < rx["clear_s"])
    if bhv.in_contact:
        bhv.contact_steps += 1
        if not was:
            bhv.contact_count += 1
            if bhv.first_contact_step < 0:
                bhv.first_contact_step = k
        if rx["action"] == "halt":
            held = veh if rx["halt_scope"] == "all" else veh & (ent.convoy_role != ROLE_SECURITY)
            hold |= held
            bhv.halt_steps += int(held.sum())


def step(ent: Entities, bhv: Behavior, op, comms, scn: Scenario, k: int,
         rng: np.random.Generator, world: Any = None) -> None:
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
        _follow(ent, bhv, comms, scn, k, rng, blue_ground, world=world)

    if bhv.ll is not None:
        _update_leader_loss(ent, bhv, k, hold)

    if bhv.contact is not None:
        _update_contact(ent, bhv, scn, k, world, hold)

    d = np.abs(ent.heading - bhv.prev_heading)
    d = np.minimum(d, 2 * np.pi - d)          # wrapped, so a heading crossing pi is not a half turn
    bhv.turn_sum += np.where(blue_ground, d, 0.0)
    bhv.turn_steps += blue_ground
    bhv.prev_heading = ent.heading.copy()

    bhv.holding = hold
    # Rising edge only, so a long hold counts as one intervention rather than one per tick.
    np.add.at(bhv.interventions, np.nonzero(hold & ~bhv.was_holding)[0], 1)
    # Durations, for the fan-out estimate in `metrics` (CR-11). Counts only, no RNG.
    bhv.hold_steps += hold
    bhv.alive_steps += blue_ground


def _predecessor(ent: Entities, bhv: Behavior, i: int) -> int:
    """The vehicle entity `i` stations on, given the topology.

    Star hands back the column leader, which is what a broadcast pose names. Chain hands back the
    nearest LIVING vehicle ahead in the column, which is what a sensor can see: a chain that loses
    its third vehicle closes up on its second rather than stopping, and that closing-up is a
    manoeuvre a star follower never has to perform because its reference never changes.
    """
    ldr = int(ent.leader[i])
    if bhv.topology == "star" or ldr < 0:
        return ldr
    for j in range(i - 1, ldr - 1, -1):
        if ent.alive[j]:
            return j
    return ldr



def _update_convoy_succession(ent: Entities, bhv: Behavior) -> None:
    """When a march unit head is lost, promote the earliest living vehicle in that march unit."""
    if ent.march_unit is None or (ent.march_unit < 0).all():
        return

    mus = np.unique(ent.march_unit[ent.march_unit >= 0])
    for mu in mus:
        mask = (ent.march_unit == mu)
        living = np.nonzero(mask & ent.alive)[0]
        if len(living) == 0:
            continue
        pool = living
        if bhv.succession == "manned_only":
            # An unmanned truck cannot command a march unit. With no manned survivor the unit stays
            # headless and its followers take the fallback in `_follow` (policy is Issue #17).
            pool = living[ent.crew[living] > 0]
            if pool.size == 0:
                continue
        new_head = int(pool[0])
        # If head vehicle was lost, promote the earliest eligible living vehicle to head
        if ent.leader[new_head] != -1 or ent.role[new_head] != 0:
            ent.role[new_head] = 0
            ent.leader[new_head] = -1
            bhv.state[new_head] = WAYPOINT
            orig_head = int(np.nonzero(mask)[0][0])
            if ent.speed_cap is not None and ent.speed_cap[orig_head] < np.inf:
                ent.speed_cap[new_head] = ent.speed_cap[orig_head]

        # Update remaining living vehicles in the march unit to follow the new head
        for foll in living[living != new_head]:
            ent.role[foll] = 1
            ent.leader[foll] = new_head


def _follow(ent: Entities, bhv: Behavior, comms, scn: Scenario, k: int,
            rng: np.random.Generator, blue_ground: np.ndarray, world: Any = None) -> None:
    """Refresh each follower's picture of the vehicle it stations on (CR-3, instrument defect 10).

    Both variants run the SAME estimator: refresh the track when the channel delivers, dead reckon
    it forward when the channel does not, and hand back to waypoint navigation once the track is
    older than `track_timeout`. Only the CHANNEL differs, and that is the whole of the comparison:

    - ``follow_mode="link"``     the leader's pose arrives over the comms link, so the refresh test
      is exactly `comms.delivered`. Jamming ages the track.
    - ``follow_mode="behavior"`` the follower sees the vehicle ahead with its own sensors, so the
      refresh test is a range test and no message is involved. Distance ages the track.

    The first version of this function had no estimator at all. Its behaviour branch read
    ``if follow_mode == "behavior" or got``, which refreshed from ground truth on every step, so the
    dead-reckoning lines beneath it were unreachable, `trk_age` was identically zero, and
    `track_timeout` could never fire. That arm was not on-platform following, it was omniscience,
    and running it against a lossy link would have measured the value of telepathy. Instrument
    defect 10, and the same genus as 7 and 8: a convention that was right for its first use (a
    placeholder while the link path was written) carried silently into a second where it was the
    entire treatment.

    Both paths draw the same uniform whatever the mode, so the two are paired on a shared seed.
    """
    dt = scn.dt
    if bhv.ll is None:
        _update_convoy_succession(ent, bhv)
    for i in np.nonzero(blue_ground & (ent.role == 1))[0]:
        ref = _predecessor(ent, bhv, int(i))
        got_link = comms.delivered(rng)     # drawn on BOTH paths: keeps the streams aligned
        if ref < 0 or not ent.alive[ref]:
            # LEADER_LOSS (Issue #17, `legacy`): nothing to follow, so hold the route independently.
            # The other policies are in `_update_leader_loss`.
            bhv.state[i] = WAYPOINT
            if bhv.succession == "manned_only":
                bhv.headless_steps += 1
            continue
        bhv.trk_steps[i] += 1
        if bhv.outage > 0:
            got = (k % (bhv.outage + 1)) == 0
        elif bhv.follow_mode == "human":
            # Human perception (Issue #14): driver observes predecessor directly; immune to comms link drops
            in_range = float(np.hypot(ent.x[ref] - ent.x[i],
                                     ent.y[ref] - ent.y[i])) <= bhv.sense_range
            if in_range and world is not None and getattr(world, "buildings", None) is not None:
                got = bool(world.los(ent.x[i], ent.y[i], ent.x[ref], ent.y[ref]))
            else:
                got = in_range
        elif bhv.follow_mode == "link":
            got = got_link
        else:
            in_range = float(np.hypot(ent.x[ref] - ent.x[i],
                                     ent.y[ref] - ent.y[i])) <= bhv.sense_range
            if in_range and world is not None and getattr(world, "buildings", None) is not None:
                got = bool(world.los(ent.x[i], ent.y[i], ent.x[ref], ent.y[ref]))
            else:
                got = in_range
        if got:
            bhv.trk_x[i], bhv.trk_y[i] = ent.x[ref], ent.y[ref]
            bhv.trk_vx[i] = ent.speed[ref] * np.cos(ent.heading[ref])
            bhv.trk_vy[i] = ent.speed[ref] * np.sin(ent.heading[ref])
            bhv.trk_age[i] = 0
            if bhv.state[i] == WAYPOINT:
                bhv.state[i] = LEADER_FOLLOW     # re-acquired, so following resumes
        else:
            bhv.trk_age[i] += 1
            bhv.trk_stale_steps[i] += 1
            bhv.trk_x[i] += bhv.trk_vx[i] * dt   # dead reckon forward
            bhv.trk_y[i] += bhv.trk_vy[i] * dt
        # Estimator error against the truth it is estimating, which is the quantity Cheung et al.
        # 2022 report as path error. Accumulated whether or not the track is being used, so it is a
        # property of the channel and not of what the planner did with it.
        bhv.trk_err_sum[i] += float(np.hypot(bhv.trk_x[i] - ent.x[ref],
                                             bhv.trk_y[i] - ent.y[ref]))
        if bhv.trk_age[i] > bhv.track_timeout:
            if bhv.state[i] != WAYPOINT:
                bhv.state[i] = WAYPOINT          # track too stale to station on
                bhv.interventions[i] += 1        # rising edge only
            bhv.trk_lost_steps[i] += 1
