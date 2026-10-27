"""Mission scoring: measures of effectiveness / performance reduced to scalar KPIs.

Everything the optimizer sees comes out of here. `compute` returns a flat dict of scalars per run;
`sandtable.sim.evaluate` averages them across Monte-Carlo replications. The five TDD metric families map
onto these fields (TTP effectiveness -> success / time_to_objective / attrition; more families are
added as the C2, comms/EW, and air layers land).
"""
from __future__ import annotations

import math

import numpy as np

from scipy.special import ndtri as _ndtri

from sandtable.entities import AIR, BLUE, GROUND, RED, Entities
from sandtable.scenario import Scenario


def blue_at_goal(ent: Entities, scn: Scenario) -> np.ndarray:
    """Mask of living blue entities within the objective radius."""
    gx, gy = scn.objective.goal
    d = np.hypot(ent.x - gx, ent.y - gy)
    return ent.side_mask(BLUE) & (d <= scn.objective.goal_radius)



def _stratified_by_deadline(n_ans, patience, total_steps: int) -> dict:
    """Answers PER STEP, split by the requester's own deadline. Fable's Round 30 gate.

    `answer_rate_v` divides answers by ASKS, so a stratification in it is partly a statement about
    who asks more. The ask counts turn out to be flat across the deadline range, which bounds how
    much bookkeeping can contribute, but a bound is not a measurement. Answers per STEP has the
    same denominator for every vehicle by construction and cannot be inflated by re-asking, so it
    is the reading that decides whether the console is really giving the impatient vehicle less
    help or merely answering a larger number of its requests.

    The split is at the fleet's own median deadline, so it is a property of the fleet rather than a
    threshold anyone chose. A uniform fleet has no split and returns nothing.

    When the impatient half receives NOTHING the ratio is undefined, and this used to return the
    fleet size as a stand-in. That is a censoring flag wearing the costume of a measurement, which
    is the same failure as instrument defect 15: it averages, it gates, and nothing downstream can
    tell it apart from a ratio that was actually observed. It is now NaN, which poisons the cell it
    belongs to and forces the reading to be reported as censored rather than scored. The count of
    fully-excluded impatient halves is exposed separately as `answer_step_censored`, so the
    information is not lost, only refused as a ratio.
    """
    pat = np.asarray(patience, dtype=float)
    if pat.size < 2 or float(pat.max() - pat.min()) <= 0.0:
        return {}
    med = float(np.median(pat))
    lo, hi = pat <= med, pat > med
    if not lo.any() or not hi.any():
        return {}
    ans = np.asarray(n_ans, dtype=float) / max(int(total_steps), 1)
    a_lo, a_hi = float(ans[lo].mean()), float(ans[hi].mean())
    return {"answer_step_impatient": a_lo, "answer_step_patient": a_hi,
            "answer_step_censored": 0.0 if a_lo > 0.0 else 1.0,
            "answer_step_ratio": a_hi / a_lo if a_lo > 0.0 else float("nan"),
            # The same comparison the other way up, and the reading to prefer. The ratio is
            # undefined exactly where the harm is worst, which is the wrong place for an instrument
            # to go blind, and one censored replication in sixty-four takes a whole block with it.
            # Inverted it is a SHARE: one when the two halves of the fleet are served in proportion,
            # zero when the impatient half receives nothing at all, and above one when the impatient
            # half is favoured. It is bounded, it is defined wherever anybody is served, and it
            # orders the design space identically wherever the ratio is defined.
            #
            # It has one failure and it is severe enough to name here rather than in a note. Being a
            # ratio of two rates, it reads 1.0 when BOTH halves get almost nothing, which is equal
            # exclusion and not proportionate service. On a console with no admission rule, deadline
            # order scores a perfect 1.0000 while excluding 0.9531 of the fleet. **This metric is
            # meaningless without a level beside it** and must never appear in a table without
            # `starved_frac` or `answer_rate_v` in the next column.
            "answer_step_share": a_lo / a_hi if a_hi > 0.0 else 1.0}


def _distribution_of_answers(n_ans, n_ask) -> dict:
    """Who got answered, not just how many answers there were.

    `starved_frac` counts TOTAL exclusion. It is the statistic a sponsor asks for first and the
    one that is hardest to move: over the run lengths we simulate no vehicle is ever excluded
    outright, so it reads 0.0 at every arm and every span and is blind to the policy. The min and
    the mean-to-min gap are computed from the same vector and do vary, so they are what a
    distributional claim has to be read off.
    """
    rate = np.asarray(n_ans) / np.maximum(np.asarray(n_ask), 1)
    lo, hi = (float(x) for x in np.percentile(rate, [25.0, 75.0]))
    return {"starved_frac": float((np.asarray(n_ans) == 0).mean()),
            "answer_rate_v": float(rate.mean()),
            "answer_rate_min": float(rate.min()),
            "answer_rate_gap": float(rate.mean() - rate.min()),
            # The min is one order statistic out of a fleet of sixteen and it moves for reasons
            # that have nothing to do with the policy. The quartiles are what a distributional
            # claim should be read off; their spread is the stratification the console imposes on
            # the fleet, and it is a different quantity from the mean in exactly the cases that
            # matter.
            "answer_rate_p25": lo,
            "answer_rate_p75": hi,
            "answer_rate_iqr": hi - lo}


def compute(scn: Scenario, init_counts: dict, ent: Entities,
            t_reached: float | None, t_elapsed: float, assault0: int | None = None,
            air0: int = 0, bhv=None, op=None) -> dict:
    # The settings the run ACTUALLY used, carried out with its own numbers. Defect 8 was a battery
    # whose arms named one console and ran the other, and it survived a whole job because nothing in
    # the output said which console had run. These are RESOLVED settings rather than a digest of the
    # parameter dict: this codebase's opt-in contract is that many spellings name the same run, and
    # twenty tests assert exactly that, so a digest of the spelling would be a guard that fires on
    # the discipline it is meant to protect. Three booleans, each one a knob that has already been
    # in silent disagreement with a registration.
    out_cfg = {
        "queue_buffer": 1.0 if scn.params.get("queue_model", "reserve") == "buffer" else 0.0,
        "policy_admit": 1.0 if scn.params.get("queue_policy", "blind") == "admit" else 0.0,
        "channel_bursty": 1.0 if scn.params.get("channel", "bernoulli") == "gilbert_elliot" else 0.0,
    }
    blue0 = max(init_counts[BLUE], 1)
    red0 = max(init_counts[RED], 1)
    blue_alive = int(ent.side_mask(BLUE).sum())
    red_alive = int(ent.side_mask(RED).sum())
    arrived = int(blue_at_goal(ent, scn).sum())
    blue_losses = init_counts[BLUE] - blue_alive
    red_losses = init_counts[RED] - red_alive
    # Success is judged over the assault force (ground blue when air recon is present); defaults to
    # the whole blue force so the ground-core scenarios are unchanged.
    assault = assault0 if assault0 is not None else init_counts[BLUE]
    success = 1.0 if arrived >= scn.objective.survive_fraction * max(assault, 1) else 0.0
    tto = float(t_reached) if t_reached is not None else float(scn.duration)

    # Cost-weighted exchange (Increment 6 KPI). Split blue losses by domain so an asymmetric cost of
    # loss can be attached: a shot-down recon drone is cheap, a lost assault vehicle is not. The unit
    # costs are stipulated scenario params defaulting to 1, so with defaults `cost_exchange` reduces
    # EXACTLY to `loss_exchange` and every prior scenario's number is unchanged.
    blue_air_alive = int((ent.side_mask(BLUE) & (ent.domain == AIR)).sum())
    blue_air_losses = max(0, air0 - blue_air_alive)
    blue_ground_losses = blue_losses - blue_air_losses
    cost_uas = float(scn.params.get("cost_uas", 1.0))         # per shot-down recon drone (air blue)
    cost_ugv = float(scn.params.get("cost_ugv", 1.0))         # per lost assault vehicle (ground blue)
    cost_red = float(scn.params.get("cost_red", 1.0))         # value of a destroyed red element
    blue_cost_lost = blue_air_losses * cost_uas + blue_ground_losses * cost_ugv
    red_cost_lost = red_losses * cost_red

    out_extra = _teaming_metrics(scn, ent, bhv, op, t_elapsed)
    out_convoy = _convoy_doctrine_metrics(scn, ent)

    return {
        **out_cfg,
        **out_extra,
        **out_convoy,
        "success": success,                                   # MOE: mission accomplished
        "time_to_objective": tto,                             # MOE: tempo (s)
        "blue_losses": float(blue_losses),                    # MOE: attrition
        "red_losses": float(red_losses),
        "blue_survivors": float(blue_alive),
        "arrived": float(arrived),
        # The continuous companion to `success`, which is a one-bit readout of this same
        # quantity against `survive_fraction`. Any sweep that moves the assault force size
        # moves the threshold too, so a shift in `success` can be a shift in the fraction or
        # a shift across the cut, and only reporting both separates them.
        "arrived_frac": arrived / max(assault, 1),
        "blue_loss_frac": blue_losses / blue0,
        "red_loss_frac": red_losses / red0,
        "loss_exchange": red_losses / max(blue_losses, 1),    # MOP: exchange ratio (count-based)
        "blue_air_losses": float(blue_air_losses),            # recon drones shot down
        "blue_ground_losses": float(blue_ground_losses),      # assault vehicles lost
        "blue_cost_lost": float(blue_cost_lost),              # cost-weighted blue attrition
        "cost_exchange": red_cost_lost / max(blue_cost_lost, 1.0),  # MOP: cost-weighted exchange
        "mission_time": float(t_elapsed),
    }


def _convoy_doctrine_metrics(scn: Scenario, ent: Entities) -> dict:
    """Doctrinal movement-control metrics from ATP 4-16 (Issue #11).

    Returned only when `scn.params.get('convoy')` is configured, so non-convoy scenarios
    remain 100% byte-identical.
    """
    convoy_spec = scn.params.get("convoy")
    if not convoy_spec:
        return {}

    from sandtable import convoy_metrics

    # Route distance from blue spawn centroid to objective goal
    blue_ground = [f for f in scn.forces if f.side == BLUE and scn.platform_types[f.ptype].domain == GROUND]
    if blue_ground:
        sx, sy = blue_ground[0].spawn
        gx, gy = scn.objective.goal
        route_dist = float(np.hypot(gx - sx, gy - sy))
        platform_len = scn.platform_types[blue_ground[0].ptype].length
        spacing = blue_ground[0].spacing if blue_ground[0].spacing is not None else float(scn.params.get("formation_spread", 30.0))
    else:
        gx, gy = scn.objective.goal
        route_dist = float(np.hypot(gx, gy))
        platform_len = 6.0
        spacing = float(scn.params.get("formation_spread", 30.0))

    summary = convoy_metrics.doctrinal_convoy_summary(
        convoy_spec,
        route_distance=route_dist,
        platform_length=platform_len,
        default_spacing=spacing,
    )

    blue_mask = ent.side_mask(BLUE) & (ent.domain == GROUND)
    if blue_mask.any():
        meas_cl = convoy_metrics.measured_column_length(ent.x, ent.y, ent.length, mask=blue_mask)
    else:
        meas_cl = 0.0

    return {
        "convoy_column_length": summary["column_length"],
        "convoy_road_space": summary["road_space"],
        "convoy_pass_time": summary["pass_time"],
        "convoy_time_distance": summary["time_distance"],
        "convoy_road_clearance_time": summary["road_clearance_time"],
        "convoy_rate_of_march": summary["rate_of_march"],
        "convoy_measured_column_length": meas_cl,
    }


def _teaming_metrics(scn: Scenario, ent: Entities, bhv, op, t_elapsed: float) -> dict:
    """Adaptability and operator-load families (CR-4, CR-7).

    Every key is exactly 0.0 when its layer is absent, so ground-core scenarios and every number
    recorded before these landed are unchanged.

    Two qualifiers are mandatory wherever these are reported.

    `intervention_rate` counts comms and operator-queue contention. Whether terrain contributes
    depends on `terrain_demand` (CR-15): with it off, terrain enters SandTable only as a speed
    raster and a cover tradeoff, never as autonomy difficulty that forces a takeover, so the rate
    is not comparable to a field-measured soldier takeover rate at all. With it on, difficult
    ground raises the call-for-help rate, which is closer to what a field takeover rate measures,
    but the coupling is a modeled scalar rather than a perception stack meeting real terrain, so
    the comparison is qualitative in either case.

    `intervention_rate` is a rate of *events*, and jamming lengthens each event, so it can fall
    while the burden rises. Always read it next to `hold_fraction`, the share of live vehicle-steps
    spent stopped waiting on the operator. `fan_out` is the Olsen and Goodrich estimate
    ``1 + neglect_steps / interaction_steps``: the number of vehicles this interaction pattern
    could sustain. It is a capacity prediction from the observed duty cycle, so comparing it with
    the span at which measured performance actually peaks is a check on the model, not a metric to
    optimize.

    `operator_goodput` is the share of direct-control decision requests that came back with an
    operator decision inside the requester's patience. Its complement splits into
    `abandon_queue_frac` (reached the operator, could not be served in time) and
    `abandon_link_frac` (the link dropped it). All three are 0.0 under supervisory control, where
    no request is ever made.

    `operator_utilization` is a workload *surrogate* in the sense of Donmez, Nehme and Cummings.
    Computational workload models explain roughly 61 to 77 percent of variance (Sarno and Wickens),
    so it is a ranking instrument and an overload flag, not a NASA-TLX-comparable score. Do not
    label it "workload".
    """
    from sandtable.entities import GROUND

    out = {"interventions": 0.0, "intervention_rate": 0.0,
           "operator_utilization": 0.0, "mean_wait": 0.0,
           "wait_p95": 0.0, "queue_depth_mean": 0.0,
           "operator_goodput": 0.0, "operator_goodput_late": 0.0,
           "abandon_queue_frac": 0.0, "abandon_link_frac": 0.0,
           "trust_dprime": 0.0, "trust_hit_rate": 0.0, "trust_fa_rate": 0.0,
           "check_frac": 0.0, "shipped_bad_per_step": 0.0, "answer_correct_frac": 1.0,
           "station_along_mean": 0.0, "station_cross_mean": 0.0,
           "abandoned_per_step": 0.0, "wasted_frac": 0.0,
           "served_per_step": 0.0, "requests_per_step": 0.0,
           "arrival_fano": 0.0, "arrival_multiplicity": 0.0, "arrival_peak": 0.0,
           "arrival_rate": 0.0, "arrival_excess": 0.0,
           "arrival_distinct": 0.0, "arrival_repeat": 0.0, "arrival_repeat_frac": 0.0,
           "arrival_ge2": 0.0, "arrival_ge3": 0.0, "arrival_ge4": 0.0,
           "patience_mean": 0.0, "patience_sd": 0.0, "patience_min": 0.0,
           "stale_frac": 0.0, "stale_per_step": 0.0, "worked_lost_per_step": 0.0,
           "stale_dropped_frac": 0.0, "stale_dropped_per_step": 0.0,
           "worked_late_per_step": 0.0, "worked_per_step": 0.0,
           "died_feasible_per_step": 0.0, "died_feasible_frac": 0.0,
           "entered_feasible_frac": 0.0,
           "busy_serviced": 0.0, "busy_stale": 0.0, "busy_lost": 0.0, "busy_late": 0.0,
           "busy_dead": 0.0, "booked_per_step": 0.0,
           "busy_total": 0.0, "svc_serviced_mean": 0.0, "svc_worked_mean": 0.0,
           "starved_frac": 0.0, "answer_rate_v": 0.0, "answer_rate_min": 0.0,
           "answer_rate_gap": 0.0, "answer_rate_p25": 0.0, "answer_rate_p75": 0.0,
           "answer_rate_iqr": 0.0, "answer_step_impatient": 0.0, "answer_step_patient": 0.0,
           "answer_step_ratio": 0.0, "answer_step_censored": 0.0,
           "answer_step_share": 0.0,
           "backlog_mean": 0.0, "dropped_frac": 0.0,
           "supervised_mean": 0.0, "supervised_frac": 0.0, "demand_norm_goodput": 0.0,
           "hold_fraction": 0.0, "interaction_steps": 0.0, "neglect_steps": 0.0, "fan_out": 0.0,
           "track_err_mean": 0.0, "station_err_mean": 0.0,
           "track_stale_frac": 0.0, "follow_lost_frac": 0.0, "turn_rate_mean": 0.0}

    if bhv is not None:
        n_ground = max(int(((ent.side == BLUE) & (ent.domain == GROUND)).sum()), 1)
        hours = max(t_elapsed, 1e-9) / 3600.0
        out["interventions"] = float(bhv.interventions.sum())
        # Following, in the two units the question is asked in. `track_err_mean` is the estimator's
        # error against the pose it is estimating, which is what Cheung, Rawashdeh and Mohammadi
        # 2022 report as path error and the only quantity comparable to that literature.
        # `station_err_mean` is how far the vehicle ends up from where the formation wanted it,
        # which is the mission-level quantity and the one this simulator exists to reach. The two
        # need not move together: a follower can hold a perfect track and still be out of position
        # behind a leader it cannot keep up with.
        trk_n = float(bhv.trk_steps.sum())
        if trk_n > 0.0:
            out["track_err_mean"] = float(bhv.trk_err_sum.sum()) / trk_n
            out["track_stale_frac"] = float(bhv.trk_stale_steps.sum()) / trk_n
            out["follow_lost_frac"] = float(bhv.trk_lost_steps.sum()) / trk_n
        turn_n = float(bhv.turn_steps.sum())
        if turn_n > 0.0:
            out["turn_rate_mean"] = float(bhv.turn_sum.sum()) / turn_n
        st_n = float(bhv.st_steps.sum())
        if st_n > 0.0:
            out["station_err_mean"] = float(bhv.st_err_sum.sum()) / st_n
            out["station_along_mean"] = float(bhv.st_along_sum.sum()) / st_n
            out["station_cross_mean"] = float(bhv.st_cross_sum.sum()) / st_n
        out["intervention_rate"] = out["interventions"] / (n_ground * hours)
        held = float(bhv.hold_steps.sum())
        live = float(bhv.alive_steps.sum())
        if live > 0.0:
            out["hold_fraction"] = held / live
        if out["interventions"] > 0.0 and held > 0.0:
            # Olsen and Goodrich's fan-out: how many vehicles one operator could hold if each
            # needed `interaction_steps` of attention and then ran free for `neglect_steps`.
            out["interaction_steps"] = held / out["interventions"]
            out["neglect_steps"] = (live - held) / out["interventions"]
            out["fan_out"] = 1.0 + out["neglect_steps"] / out["interaction_steps"]

    if op is not None and op.total_steps > 0:
        out["operator_utilization"] = op.busy_steps / op.total_steps
        if op.n_request > 0:
            # Only `queue_model = "buffer"` can produce these. A request is STALE when the console
            # works it after its requester's patience ran out and the requester asked again: the
            # slot is spent on an answer nobody is holding. The reservation model cannot represent
            # it, because there a request's fate is settled at arrival and a vehicle can never have
            # two outstanding.
            out["stale_frac"] = op.n_stale / op.n_request
            out["stale_dropped_frac"] = op.n_stale_dropped / op.n_request
            out["dropped_frac"] = op.n_dropped / op.n_request
        out["backlog_mean"] = op.backlog_sum / op.total_steps
        if op.patience_v is not None:
            # The dispersion arm prints its own assumption. A `patience_spread` sweep is a pure
            # second-moment manipulation only if the first moment holds, and the way that stops
            # being an argument is to log both and read them off the run (CR-46).
            pv = op.patience_v[ent.side == BLUE].astype(float)
            out["patience_mean"] = float(pv.mean()) if pv.size else 0.0
            out["patience_sd"] = float(pv.std()) if pv.size else 0.0
            # The floor matters on its own: a vehicle whose patience is below the
            # round trip plus one service time cannot be served on ANY link, and a
            # deadline rule that puts it first is prioritizing doomed work.
            out["patience_min"] = float(pv.min()) if pv.size else 0.0
        out["queue_depth_mean"] = op.queue_depth_sum / op.total_steps
        # The demand the goodput was earned against. `operator_goodput` is endogenous to attrition:
        # a mission that destroys half the force halves the offered load and the console looks
        # better for it. Reading the two together is what stops a staffing number taken from a
        # costly trial being applied to a cheap one.
        out["supervised_mean"] = op.supervised_sum / op.total_steps
        out["supervised_frac"] = out["supervised_mean"] / max(op.supervised_n0, 1)
        if op.mult_window > 0 and op._mult_busy > 0:
            # E[k | k >= 1]: given that a service window saw any request, how many did it see.
            # 1.0 is a perfectly scattered stream; above 1.0 counts the forced waits a cohort
            # imposes on itself. Conditioned on a busy window so that lowering the RATE cannot
            # be mistaken for lowering the clustering, which is the confound that makes the
            # unconditioned mean useless for comparing arms at different offered loads.
            out["arrival_multiplicity"] = op._mult_sum / op._mult_busy
            out["arrival_peak"] = op._mult_peak
            out["arrival_rate"] = op._mult_sum / op.total_steps
            # E[k | k >= 1] rises with rate for ANY process, so a channel that delivers more
            # round-trips looks more clustered even with identical phase structure. The
            # Poisson value at this arm's own delivered rate is the scatter-only control:
            # `lw / (1 - exp(-lw))`. The ratio is clustering net of rate, and it is the only
            # form of this statistic comparable ACROSS channels.
            lw = out["arrival_rate"] * op.mult_window
            pois = lw / (1.0 - math.exp(-lw)) if lw > 0 else 1.0
            out["arrival_excess"] = out["arrival_multiplicity"] / pois
            # A multiplicity of three can be three vehicles colliding or one vehicle asking three
            # times, and only the first is the cohort this paper's recommendation addresses. The
            # distinct-sender count separates them: `arrival_repeat` is the part of the crowding
            # a single vehicle inflicts on itself, which a jittered hold cannot fix because there
            # is nothing to desynchronize from. Reporting it is what keeps the mechanism claim
            # from resting on a statistic that cannot tell the two apart.
            out["arrival_distinct"] = op._mult_dsum / op._mult_busy
            out["arrival_repeat"] = out["arrival_multiplicity"] - out["arrival_distinct"]
            out["arrival_repeat_frac"] = out["arrival_repeat"] / out["arrival_multiplicity"]
            # The tail, which is what the console actually prices. It serves one request and can
            # hold `floor((patience - 2 * latency) / service)` more before the requester gives up,
            # so crowding inside that depth is free and crowding past it is not. Reporting the
            # whole distribution rather than one over-depth flag keeps the statistic usable at any
            # rung, since the depth is 3, 2, 2, 1, 0 across rungs 0 to 4 and the arms differ in rung.
            out["arrival_ge2"] = op._mult_ge2 / op._mult_busy
            out["arrival_ge3"] = op._mult_ge3 / op._mult_busy
            out["arrival_ge4"] = op._mult_ge4 / op._mult_busy
        if op.fano_window > 0 and op._fano_n > 1 and op._fano_sum > 0.0:
            mean = op._fano_sum / op._fano_n
            var = op._fano_sumsq / op._fano_n - mean * mean
            out["arrival_fano"] = var / mean
        if op.waits:
            w = np.asarray(op.waits, float)
            out["mean_wait"] = float(w.mean())
            out["wait_p95"] = float(np.percentile(w, 95))
        if op.n_request > 0:
            out["operator_goodput"] = op.n_serviced / op.n_request
            out["abandon_queue_frac"] = op.n_abandon_queue / op.n_request
            # D7, which `doc/lit-ideas.md` records as absent from the literature: a discrimination
            # score for the operator's trust decision against the agent's ground-truth correctness.
            # The four cells are counted in the operator's own decision units, so the score is a
            # property of the operator and does not move when the scenario changes how much work
            # arrives. The log-linear correction is the standard one for empty cells; without it a
            # perfect operator scores infinity and the metric cannot be averaged over replications.
            hit, fa = op.n_check_hit, op.n_check_fa
            miss, cr = op.n_check_miss, op.n_check_cr
            npos, nneg = hit + miss, fa + cr
            # An operator who checks everything sits at the top-right corner of the ROC and one
            # who checks nothing sits at the bottom-left. Discrimination is not estimable at either
            # corner, and the log-linear correction returns a small signed number there rather than
            # refusing, which would read as a discrimination score that is not one. Both corners
            # report zero, which is the truth: no decision was discriminated.
            if npos > 0 and nneg > 0 and (hit + fa) > 0 and (miss + cr) > 0:
                hr = min(max((hit + 0.5) / (npos + 1.0), 1e-6), 1 - 1e-6)
                far = min(max((fa + 0.5) / (nneg + 1.0), 1e-6), 1 - 1e-6)
                out["trust_dprime"] = float(_ndtri(hr) - _ndtri(far))
                out["trust_hit_rate"] = hit / npos
                out["trust_fa_rate"] = fa / nneg
            out["check_frac"] = (hit + fa) / max(hit + fa + miss + cr, 1)
            out["shipped_bad_per_step"] = op.n_shipped_bad / op.total_steps
            out["answer_correct_frac"] = 1.0 - op.n_shipped_bad / max(op.n_serviced +
                                                                      op.n_shipped_bad, 1)
            out["abandon_link_frac"] = op.n_abandon_link / op.n_request
            # Goodput discounted by the demand that survived to offer it, so a share earned in a
            # costly mission is not read as capacity available in a cheap one.
            out["demand_norm_goodput"] = out["operator_goodput"] * out["supervised_frac"]
        # Absolute service RATES, which a treatment that changes the request cadence cannot
        # inflate. `operator_goodput` is serviced over requested, and a retry manufactures
        # requests: the failure cycle falls from `P + tau + 1` to `P + rho + 1`, so a short backoff
        # nearly doubles the denominator on its own. Any contrast between arms whose request rates
        # differ has to be read here as well, or congestion and denominator inflation are mixed.
        out["served_per_step"] = op.n_serviced / op.total_steps
        out["requests_per_step"] = op.n_request / op.total_steps
        # The four bins a CLAIMED slot exits through, as rates, so that they are commensurable with
        # each other and with the capacity they partition. `served` is the only one that reaches a
        # requester still waiting; the other three are the console's time spent and nothing
        # delivered, by three different routes. `n_abandon_queue` and `n_abandon_link` cannot stand
        # in for the last two, because each of them also counts paths where no slot was claimed at
        # all (a head-of-line refusal, an uplink loss), which is why the counters are separate.
        out["stale_per_step"] = op.n_stale / op.total_steps
        out["stale_dropped_per_step"] = op.n_stale_dropped / op.total_steps
        out["worked_lost_per_step"] = op.n_worked_lost / op.total_steps
        out["worked_late_per_step"] = op.n_worked_late / op.total_steps
        out["worked_per_step"] = (op.n_serviced + op.n_stale + op.n_worked_lost
                                  + op.n_worked_late) / op.total_steps
        # The scheduling problem's own size, which no other metric here reports. A request is
        # FEASIBLE at entry when an idle console could have answered it inside its deadline; one
        # that was feasible at entry and then died at a deadline was killed by the order the console
        # chose rather than by its capacity or its link. When this reads zero the queue never
        # presented a binding choice, so two disciplines scoring the same is a statement about the
        # ceiling and not about the information they read.
        out["died_feasible_per_step"] = op.n_died_feasible / op.total_steps
        # NaN and not zero when nothing entered the backlog, because the `reserve` console has no
        # backlog at all: a request is committed to a slot the instant it arrives and there is
        # nothing to order. Zero there would read as "this console loses no servable requests to its
        # ordering", which is instrument defect 13's exact shape, and eleven batteries in this paper
        # run that console. NaN is refused loudly by `tools/ar_survey.py`.
        out["died_feasible_frac"] = (op.n_died_feasible / op.n_entered_feasible
                                     if op.n_entered_feasible else float("nan"))
        out["entered_feasible_frac"] = (op.n_entered_feasible / op.n_request
                                        if op.n_request else 0.0)
        # The same partition weighted by the console-steps each fate CONSUMED rather than by the
        # jobs it finished. These are the bins the invariance claim belongs in: `worked_per_step`
        # is conserved only when service is a metronome, because a console that admits on a
        # deadline test selects short jobs and can finish more of them per busy step. Time cannot
        # be selected. `busy_total` is therefore the console's utilization, reached by summing the
        # four fates, and it is the quantity to compare against `operator_utilization`, which
        # reaches the same number by counting busy steps and so rounds each service up.
        #
        # That reading holds on the BUFFER console and only there, which is instrument defect 18.
        # The buffer console refuses to start a service while it is still busy, so the service time
        # it accumulates is bounded by the clock and dividing by `total_steps` gives a fraction. The
        # published RESERVE console commits a request to a slot the moment the request arrives, and
        # books forward without bound: at thirty-two assets it holds a book 4.74 times longer than
        # the mission, so the same division returns 4.74 and a reader who was promised a fraction of
        # the console's time gets an offered-load ratio instead. Every battery that measures these
        # runs on `buffer`, so no result moves, but the trap is live for the next one that does not.
        # The six fractions are therefore NaN off the buffer console, and the ratio that IS defined
        # on both is emitted under its own name below. NaN is refused loudly by `tools/ar_survey.py`.
        _den = op.total_steps if op.queue_model == "buffer" else float("nan")
        out["busy_serviced"] = op.t_serviced / _den
        out["busy_stale"] = op.t_stale / _den
        out["busy_lost"] = op.t_worked_lost / _den
        out["busy_late"] = op.t_worked_late / _den
        # The console clock that produced no answer, by whatever route. It is reported beside
        # `busy_stale` because a repair can move dead time between the three buckets without
        # removing any of it, and a reader shown only the bucket that fell would read that as a
        # recovery. This sum is what has to fall for a repair to be one.
        out["busy_dead"] = (op.t_stale + op.t_worked_lost + op.t_worked_late) / _den
        out["busy_total"] = (op.t_serviced + op.t_stale + op.t_worked_lost
                             + op.t_worked_late) / _den
        # Service time the console has COMMITTED to, per step of mission. On the buffer console it
        # equals `busy_total` because the book never runs past the clock; on the reserve console it
        # is the offered-load ratio rho, and a value above one is the honest statement that the
        # console has accepted more work than the mission is long. Defined on BOTH, so it is the
        # quantity to quote when the console model is not held fixed across the arms.
        out["booked_per_step"] = (op.t_serviced + op.t_stale + op.t_worked_lost
                                  + op.t_worked_late) / op.total_steps
        # Length selection, the mechanism a variable console's admission test acts through. At
        # `service_cv = 0` this is exactly `1 / service_rate`; below it, the console is choosing.
        if op.n_serviced > 0:
            out["svc_serviced_mean"] = op.t_serviced / op.n_serviced
        worked_jobs = op.n_serviced + op.n_stale + op.n_worked_lost + op.n_worked_late
        if worked_jobs > 0:
            out["svc_worked_mean"] = (op.t_serviced + op.t_stale + op.t_worked_lost
                                      + op.t_worked_late) / worked_jobs
        # Starvation in the unit the harm is in. Mean backlog counts requests that never leave,
        # which is a memory statistic and can be large for a policy that is doing well; whether a
        # VEHICLE ever gets an answer is the statistic a sponsor is entitled to. Under newest-first
        # the two need not agree, because a starved requester re-asks and its new request lands on
        # top of the pile it was buried under.
        if op.n_ask_v is not None:
            asked = (op.n_ask_v > 0) & (ent.side == BLUE)
            if asked.any():
                out.update(_distribution_of_answers(op.n_ans_v[asked], op.n_ask_v[asked]))
                if op.patience_v is not None:
                    out.update(_stratified_by_deadline(
                        op.n_ans_v[asked], op.patience_v[asked], op.total_steps))
                # Instrument defect 13. `starved_frac` counts TOTAL exclusion, and over a run of
                # this length no vehicle is ever excluded outright, so it sits on its floor at
                # every arm and every span and a null read from it is a property of the run length
                # rather than of the policy. The distribution has to be measured where it actually
                # varies: the worst-served vehicle, and the gap between it and the mean.

        # Absolute abandonment, for the same reason. `abandon_queue_frac` divides by
        # `n_request`, so a treatment that suppresses requests can lower the FRACTION while
        # abandoning exactly as often, or raise it while abandoning less. The rate cannot be
        # moved that way, and it is the quantity that says whether work a policy forgoes was
        # work that would have been wasted.
        out["abandoned_per_step"] = op.n_abandon_queue / op.total_steps
        # The share of everything the console was asked that ended in a queue abandonment,
        # expressed against requests SERVED rather than requests made: how much doomed work
        # the console carries per unit of work it completes.
        if op.n_serviced > 0:
            out["wasted_frac"] = op.n_abandon_queue / op.n_serviced
        if op.n_request_late > 0:
            # Final quarter only: whether the team ENDED the mission serving requests, which is a
            # different question from how many it served on average (CR-17).
            out["operator_goodput_late"] = op.n_serviced_late / op.n_request_late
    return out
