"""One console per march unit (Issue #19): dedicated consoles, a per-console attention term, per-console metrics.

Opt-in with ``params["console_per_march_unit"]``. Absent, `c2.py` runs exactly as before.

DEFINITIONS (they are different things and the code keeps them apart)
  march unit   a group of vehicles under one head (`ent.march_unit`).
  console      one service station: its own queue (`crew_free_at[c]`), its own service rate, its own quality.
               There is one console per march unit, hosted by that unit's control vehicle.
  operator     the human at a console. In this model the unit's commander on the control vehicle; not a
               separate entity and not shared with another unit.
  service slot a console serves one request at a time (`service_rate` decisions per step). There is no
               second slot: a second operator would be a second console.
  supervised agent   a living vehicle of the unit with NO assigned crew (`ent.crew == 0`), other than the
               host. Only supervised agents file requests. Crewed vehicles (the control vehicle, crewed
               escorts or recovery vehicles) and vehicles outside any march unit (for example UAS) do not
               file requests and are left at the neutral control quality 1.0. This is a modelling choice.

ATTENTION. The existing term (`c2.build_c2`) is  attention = min(1, span_capacity / n_span)  with
n_span = ALL Blue entities, computed once at build, with `n_operators` ignored. Per console it becomes

    attention_c = min(1, span_capacity / n_c)        (1 when n_c = 0)

where n_c counts the supervised agents assigned to console c: the vehicles assigned at build
(`attention_basis="assigned"`, the default, as the issue states) or the living ones now
(`"living"`). The serviced-decision quality keeps the existing form

    q_c = q_auto + (q_operator - q_auto) * attention_c

so `attention_c` multiplies only the quality gain over `q_auto`. It does not change service time, latency,
or loss. Communications act only through latency, delivery and drops (`comms_ew`); queueing only through
`crew_free_at[c]`; no impairment is applied through two mechanisms.

CONSOLE LOSS. A console is alive while its host (the unit's control vehicle) is alive. When the host is
destroyed the console's service rate is zero: requests from its agents are not served, wait out their
patience and fall back to `q_fallback` (counted as `abandon_console`). Followers' movement then follows the
leader-loss policy of Issue #17. Assignments are fixed at build: after `promote`, `absorb`, `halt` or
`continue` a vehicle stays with its ORIGINAL console (an absorbed vehicle is not re-assigned), there is no
reassignment delay, and a promoted successor does not take over the console.

EXCEPTIONS. With ``exceptions: true`` a supervised agent whose behavior layer has just logged a new
intervention (a LEADER_FOLLOW track timeout) files a request at once, to its own console, in addition to its
periodic decision events.

MEASURES. Per console, in steps: interaction time IT = mean service time of serviced requests; wait time WT =
mean queue wait of serviced requests (start of service minus arrival at the console); neglect time NT = mean
interval from the arrival of a vehicle's last answer to its next request. `nt_margin` = NT - (s - 1)(IT + WT)
with s the mean supervised count; the condition NT >= (s - 1)(IT + WT) is the specification of the issue.
Communications delay (`comms_up`, `comms_down`), queue wait, service time, link failures and
quality are reported separately. Console utilization is a busy fraction of a server, NOT a measured cognitive
workload.

The module draws no random numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sandtable.entities import BLUE, GROUND, Entities

_KEYS = {"attention_basis", "exceptions"}
BASES = ("assigned", "living")


def resolve_unit_consoles(params: dict | None) -> dict | None:
    """Normalise and validate `params["console_per_march_unit"]`; None when absent (feature off)."""
    if not params:
        return None
    raw = params.get("console_per_march_unit")
    if raw is None or raw is False or raw == "none":
        return None
    if raw is True:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"console_per_march_unit must be None, true or a dict, got {raw!r}")
    extra = set(raw) - _KEYS
    if extra:
        raise ValueError(f"unknown console_per_march_unit keys {sorted(extra)}; allowed {sorted(_KEYS)}")
    basis = raw.get("attention_basis", "assigned")
    if basis not in BASES:
        raise ValueError(f"console_per_march_unit attention_basis must be one of {list(BASES)}, got {basis!r}")
    exc = raw.get("exceptions", False)
    if not isinstance(exc, bool):
        raise ValueError(f"console_per_march_unit exceptions must be a bool, got {exc!r}")
    if params.get("control_mode") != "direct":
        raise ValueError("console_per_march_unit needs control_mode 'direct' (requests are what the console serves)")
    if int(params.get("n_operators", 1)) != 1:
        raise ValueError("console_per_march_unit sets the console count from the march units; n_operators must stay 1")
    if str(params.get("queue_model", "reserve")) != "reserve":
        raise ValueError("console_per_march_unit supports queue_model 'reserve' only")
    if float(params.get("q_droop", 0.0)) != 0.0:
        raise ValueError("console_per_march_unit does not support q_droop (it reads a single running utilization)")
    return {"attention_basis": basis, "exceptions": exc}


@dataclass
class UnitConsoles:
    cfg: dict
    unit_ids: np.ndarray          # march unit id per console
    host: np.ndarray              # entity index of the hosting control vehicle per console
    console_of: np.ndarray        # per entity: its console, -1 when not a supervised agent
    n_assigned0: np.ndarray       # supervised agents assigned at build, per console
    span_capacity: float
    q_operator: float
    q_auto: float
    host_alive: np.ndarray        # bool per console
    n_living: np.ndarray          # living supervised agents per console, this tick
    attention: np.ndarray         # attention per console, this tick
    q_eff: np.ndarray             # serviced-decision quality per console, this tick
    lost_at: np.ndarray           # step at which the host was seen dead, -1 if alive
    prev_interventions: np.ndarray | None = None
    ans_at: np.ndarray = None     # per entity: arrival step of its last answer, -1 if none to measure from
    # per-console accumulators
    active_steps: np.ndarray = None
    supervised_sum: np.ndarray = None
    attention_sum: np.ndarray = None
    busy_steps: np.ndarray = None
    requests: np.ndarray = None
    exception_requests: np.ndarray = None
    serviced: np.ndarray = None
    abandon_link: np.ndarray = None
    abandon_queue: np.ndarray = None
    abandon_console: np.ndarray = None
    svc_sum: np.ndarray = None
    qwait_sum: np.ndarray = None
    up_sum: np.ndarray = None
    down_sum: np.ndarray = None
    quality_sum: np.ndarray = None
    nt_sum: np.ndarray = None
    nt_n: np.ndarray = None


def build_unit_consoles(scn, ent: Entities, cfg: dict, q_operator: float, q_auto: float,
                        span_capacity: float) -> UnitConsoles:
    from sandtable.convoy import ROLE_CONTROL, resolve_convoy_spec, resolve_crew_table
    spec = resolve_convoy_spec(scn.params)
    if not spec:
        raise ValueError("console_per_march_unit needs a convoy (march units)")
    if resolve_crew_table(spec) is None:
        raise ValueError("console_per_march_unit needs crew declared (autonomy_arm, crew or crew_metrics): "
                         "only vehicles without assigned crew are supervised agents")
    if not span_capacity > 0:
        raise ValueError(f"span_capacity must be positive, got {span_capacity}")
    ground = (ent.side == BLUE) & (ent.domain == GROUND) & (ent.march_unit >= 0)
    units = np.unique(ent.march_unit[ground])
    host = np.full(units.size, -1, np.int64)
    console_of = np.full(ent.n, -1, np.int64)
    n0 = np.zeros(units.size, np.int64)
    for c, mu in enumerate(units):
        members = np.nonzero(ground & (ent.march_unit == mu))[0]
        hosts = members[ent.convoy_role[members] == ROLE_CONTROL]
        if hosts.size == 0:
            raise ValueError(f"march unit {int(mu)} has no control vehicle to host its console")
        host[c] = int(hosts[0])
        agents = members[(ent.crew[members] == 0) & (members != host[c])]
        console_of[agents] = c
        n0[c] = agents.size
    nc = units.size
    z = lambda dt=float: np.zeros(nc, dt)   # noqa: E731
    return UnitConsoles(
        cfg=cfg, unit_ids=units.astype(np.int64), host=host, console_of=console_of, n_assigned0=n0,
        span_capacity=span_capacity, q_operator=q_operator, q_auto=q_auto,
        host_alive=np.ones(nc, bool), n_living=n0.copy(), attention=np.ones(nc), q_eff=np.full(nc, q_operator),
        lost_at=np.full(nc, -1, np.int64), ans_at=np.full(ent.n, -1, np.int64),
        active_steps=z(np.int64), supervised_sum=z(), attention_sum=z(), busy_steps=z(), requests=z(np.int64),
        exception_requests=z(np.int64), serviced=z(np.int64), abandon_link=z(np.int64), abandon_queue=z(np.int64),
        abandon_console=z(np.int64), svc_sum=z(), qwait_sum=z(), up_sum=z(), down_sum=z(), quality_sum=z(),
        nt_sum=z(), nt_n=z(np.int64))


def assigned_living(ent: Entities, u: UnitConsoles, blue: np.ndarray) -> np.ndarray:
    """The living supervised agents among `blue`, in their original order."""
    return blue[u.console_of[blue] >= 0]


def begin_step(ent: Entities, u: UnitConsoles, op_crew_free_at: np.ndarray, k: int, bhv) -> float:
    """Update host status, supervised counts, attention and quality; take this tick's samples; fire exceptions.

    Returns the pooled busy fraction over ACTIVE consoles (alive and with at least one living supervised
    agent), which the legacy `busy_steps` accumulator uses so that lost and empty consoles do not dilute it.
    """
    nc = u.host.size
    now_alive = ent.alive[u.host]
    for c in np.nonzero(u.host_alive & ~now_alive)[0]:
        u.lost_at[c] = k
    u.host_alive = now_alive.copy()
    living = np.bincount(u.console_of[(u.console_of >= 0) & ent.alive], minlength=nc).astype(np.int64)
    u.n_living = living
    n_basis = u.n_assigned0 if u.cfg["attention_basis"] == "assigned" else living
    u.attention = np.where(n_basis > 0, np.minimum(1.0, u.span_capacity / np.maximum(n_basis, 1)), 1.0)
    u.q_eff = u.q_auto + (u.q_operator - u.q_auto) * u.attention
    active = u.host_alive & (living > 0)
    u.active_steps += active
    u.supervised_sum += np.where(active, living, 0)
    u.attention_sum += np.where(active, u.attention, 0.0)
    busy = (op_crew_free_at > k) & active
    u.busy_steps += busy
    if u.cfg["exceptions"] and bhv is not None:
        if u.prev_interventions is None:
            u.prev_interventions = bhv.interventions.copy()
        new = np.nonzero((bhv.interventions > u.prev_interventions) & (u.console_of >= 0) & ent.alive
                         & (ent.await_until < 0))[0]
        u.prev_interventions = bhv.interventions.copy()
        for i in new:
            ent.decision_cooldown[i] = 0                  # the exception files a request on this tick
            u.exception_requests[u.console_of[i]] += 1
    return float(busy.sum() / max(int(active.sum()), 1)) if active.any() else 0.0


def note_request(u: UnitConsoles, console: int, i: int, k: int) -> None:
    u.requests[console] += 1
    if u.ans_at[i] >= 0:                                   # neglect time: last answer arrival -> this request
        u.nt_sum[console] += k - u.ans_at[i]
        u.nt_n[console] += 1
        u.ans_at[i] = -1


def note_serviced(u: UnitConsoles, console: int, i: int, svc: float, qwait: float, up: float, down: float,
                  quality: float, reply: float) -> None:
    u.serviced[console] += 1
    u.svc_sum[console] += svc
    u.qwait_sum[console] += qwait
    u.up_sum[console] += up
    u.down_sum[console] += down
    u.quality_sum[console] += quality
    u.ans_at[i] = int(np.ceil(reply))


def _ratio(num: float, den: float) -> float:
    return float(num / den) if den > 0 else 0.0


def metrics(u: UnitConsoles, dt: float = 1.0) -> dict:
    """Per-console results (`c2u_c<j>_*`, console j = j-th march unit in id order) and pooled aggregates.

    Aggregates are ratios of sums over the consoles that were ACTIVE (alive with at least one living supervised
    agent) on each step, so inactive or lost consoles do not dilute them. Times are in steps; multiply by `dt` for
    seconds. `c2u_c<j>_nt_margin` = NT - (s - 1)(IT + WT) with s the mean supervised count, computed from the
    reported averages (NaN without samples). A negative value means the configured inequality is violated under
    these estimates; it is not proof that measured demand exceeds what the console can supply, and a pooled or
    average margin says nothing about individual consoles, vehicles or moments.
    """
    nc = u.host.size
    out = {"c2u_consoles_assigned": float(nc),
           "c2u_consoles_active_end": float((u.host_alive & (u.n_living > 0)).sum()),
           "c2u_consoles_lost": float((~u.host_alive).sum()),
           "c2u_agents_assigned": float(u.n_assigned0.sum()),
           "c2u_agents_per_console_assigned": _ratio(float(u.n_assigned0.sum()), nc)}
    for c in range(nc):
        s = _ratio(u.supervised_sum[c], u.active_steps[c])
        it, wt = _ratio(u.svc_sum[c], u.serviced[c]), _ratio(u.qwait_sum[c], u.serviced[c])
        nt = _ratio(u.nt_sum[c], u.nt_n[c])
        p = f"c2u_c{c}_"
        out.update({
            p + "unit": float(u.unit_ids[c]), p + "assigned": float(u.n_assigned0[c]),
            p + "supervised_mean": s, p + "attention_mean": _ratio(u.attention_sum[c], u.active_steps[c]),
            p + "active_steps": float(u.active_steps[c]), p + "lost_at": float(u.lost_at[c]),
            p + "requests": float(u.requests[c]), p + "exception_requests": float(u.exception_requests[c]),
            p + "serviced": float(u.serviced[c]), p + "abandon_link": float(u.abandon_link[c]),
            p + "abandon_queue": float(u.abandon_queue[c]), p + "abandon_console": float(u.abandon_console[c]),
            p + "utilization": _ratio(u.busy_steps[c], u.active_steps[c]),
            p + "it": it, p + "wt": wt, p + "nt": nt,
            p + "comms_up": _ratio(u.up_sum[c], u.serviced[c]), p + "comms_down": _ratio(u.down_sum[c], u.serviced[c]),
            p + "quality_mean": _ratio(u.quality_sum[c], u.serviced[c]),
            p + "nt_margin": (nt - (s - 1.0) * (it + wt)) if (u.nt_n[c] > 0 and u.serviced[c] > 0) else float("nan"),
        })
    act = float(u.active_steps.sum())
    ser = float(u.serviced.sum())
    out.update({
        "c2u_active_console_steps": act,
        "c2u_supervised_mean": _ratio(float(u.supervised_sum.sum()), act),
        "c2u_attention_mean": _ratio(float(u.attention_sum.sum()), act),
        "c2u_utilization": _ratio(float(u.busy_steps.sum()), act),
        "c2u_requests": float(u.requests.sum()), "c2u_exception_requests": float(u.exception_requests.sum()),
        "c2u_serviced": ser, "c2u_abandon_link": float(u.abandon_link.sum()),
        "c2u_abandon_queue": float(u.abandon_queue.sum()), "c2u_abandon_console": float(u.abandon_console.sum()),
        "c2u_it": _ratio(float(u.svc_sum.sum()), ser), "c2u_wt": _ratio(float(u.qwait_sum.sum()), ser),
        "c2u_nt": _ratio(float(u.nt_sum.sum()), float(u.nt_n.sum())),
        "c2u_comms_up": _ratio(float(u.up_sum.sum()), ser), "c2u_comms_down": _ratio(float(u.down_sum.sum()), ser),
        "c2u_quality_mean": _ratio(float(u.quality_sum.sum()), ser),
        "c2u_serviced_frac": _ratio(ser, float(u.requests.sum())),
    })
    return out
