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
        # The topology DEFAULTS TO THE CHANNEL rather than to a value, because the channel is what
        # decides which vehicle can be followed at all: a broadcast pose is the column leader's, a
        # sensor return is the vehicle immediately ahead. Setting it explicitly breaks that tie and
        # is how the 2x2 that separates channel from geometry is run.
        topology=str(scn.params.get(
            "follow_topology",
            "star" if str(scn.params.get("follow_mode", "behavior")) == "link" else "chain")),
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
        _follow(ent, bhv, comms, scn, k, rng, blue_ground)

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


def _follow(ent: Entities, bhv: Behavior, comms, scn: Scenario, k: int,
            rng: np.random.Generator, blue_ground: np.ndarray) -> None:
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
    for i in np.nonzero(blue_ground & (ent.role == 1))[0]:
        ref = _predecessor(ent, bhv, int(i))
        got_link = comms.delivered(rng)     # drawn on BOTH paths: keeps the streams aligned
        if ref < 0 or not ent.alive[ref]:
            # HALT_ON_LEADER_LOSS: nothing to follow, so hold the route independently.
            bhv.state[i] = WAYPOINT
            continue
        bhv.trk_steps[i] += 1
        if bhv.outage > 0:
            got = (k % (bhv.outage + 1)) == 0
        elif bhv.follow_mode == "link":
            got = got_link
        else:
            got = float(np.hypot(ent.x[ref] - ent.x[i],
                                 ent.y[ref] - ent.y[i])) <= bhv.sense_range
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
