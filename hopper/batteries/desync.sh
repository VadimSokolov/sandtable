# CR-27. THE PUMP AND THE VALVE, WITH THE CONFOUND FABLE FOUND CONTROLLED.
#
# Four registered mechanisms have now died on this one contrast and the survivor is not a threshold
# story. What is left is arrival SYNCHRONIZATION: a retry on a channel with long outages keeps
# re-offering during the outage, everything floods through at the channel's recovery edge, and the
# console gets a cluster it cannot absorb; the back of the cluster waits past P and abandons; and
# under `blind` the operator serves it anyway. Two clauses, and each needs its own manipulation.
#
# THE VALVE clause already has a gated one. `st-policyburst-9445271`: the burst penalty on goodput
# does not shrink under `refund`, it REVERSES, +0.253 at eight vehicles, t = 73.8. And on an
# exogenous arrival process with the feedback cut (`queue_theory.bench_sim`, added today), refund
# closes 39 to 61% of the cost of clustering at matched rate.
#
# THE PUMP clause is what this battery is for, and Fable found the confound that would have
# manufactured a false confirmation. `retry_spread = s` does NOT hold the mean: the hold is floored
# at one step, so at rho = 4 a spread of 30, 60 or 120 delivers a MEAN of 10.4, 18.2 or 33.9. A
# jitter arm would beat a fixed rho = 4 control through the mean alone whether or not anything
# desynchronized. That defect is now a hard error in `build_c2` rather than a caution in a comment:
# a spread wider than `rho + tau` cannot be requested, because past that width the floor at one
# step is guaranteed to move the mean.
#
# The pairs below are therefore built so the floor NEVER bites, which holds the mean by
# construction rather than by matching two different distributions. A spread of `rho - 1` puts the
# support on [1, 2*rho - 1] with mean exactly `rho`, so each pair varies width alone and the three
# pairs give P3 a monotonicity test across widths of 6, 18 and 34 steps against a channel dwell of
# 120. Verified by value over the full cooldown support: (4, 3) and (10, 9) and (18, 17) return
# means of 4.00, 10.00 and 18.00 against their fixed controls' 4, 10 and 18.
#
# Fable's Round 9 cut: the rho = 34 tier is dropped. Its effective cycle sits past the standing
# consultation interval, so the arm spends most of the mission indistinguishable from not retrying
# at all and is the lowest-information rung on the ladder. The run it costs is spent on D4 instead.
#
# And the intermediate variable is read INSIDE the battery rather than inferred. `fano_window=120`
# turns on the arrival-burstiness instrument added today, the Fano factor of the delivered uplink
# stream in windows the size of the channel dwell. Calibration, n=5 rung 3, against the offline
# probe: bern_off 1.76, ge_off 2.86, bern_retry 2.54, ge_retry 5.77. The instrument's floor is 1.76
# and not 1.00, because a memoryless channel still has a within-mission demand trend from
# attrition, so only DIFFERENCES against a matched control mean anything here.
#
# REGISTERED.
#   P1. Within each mean-matched pair the JITTERED arm has a LOWER arrival Fano than its fixed
#       control. FALSIFIER: no pair shows a gated Fano reduction, in which case the retry phase is
#       not the synchronizer and the account fails at its first step.
#   P2. Within each mean-matched pair the jittered arm has HIGHER goodput. FALSIFIER: a gated Fano
#       reduction with no goodput gain, in which case clustering is a description and not a cause,
#       and after four refutations I stop and report the regularity unexplained.
#   P3. The goodput gain is monotone in the Fano reduction across the three pairs.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120,"fano_window":120'
C='"control_mode":"direct","comms_level":3'
P='"retry_prob":1.0'

for M in arrival_fano operator_goodput success; do
echo "### D1 jitter against its mean-matched fixed control ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "noretry={$C,$G}" \
  --arm "fix04={$C,$G,$P,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "jit04={$C,$G,$P,\"retry_backoff\":4,\"retry_spread\":3}" \
  --arm "fix10={$C,$G,$P,\"retry_backoff\":10,\"retry_spread\":0}" \
  --arm "jit10={$C,$G,$P,\"retry_backoff\":10,\"retry_spread\":9}" \
  --arm "fix18={$C,$G,$P,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,$G,$P,\"retry_backoff\":18,\"retry_spread\":17}" \
  --arm "adapt={$C,$G,$P,\"retry_backoff\":4,\"retry_spread\":0,\"retry_mode\":\"double\"}"
done

# The same instrument on the memoryless channel, where there is no dwell to synchronize to and the
# jitter should therefore buy nothing. If it buys the same there, the story is about the retry and
# not about the channel, and P1 is measuring the wrong thing.
for M in arrival_fano operator_goodput; do
echo "### D2 the null control: no dwell to synchronize to ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "noretry={$C,\"fano_window\":120}" \
  --arm "fix04={$C,\"fano_window\":120,$P,\"retry_backoff\":4,\"retry_spread\":0}" \
  --arm "fix18={$C,\"fano_window\":120,$P,\"retry_backoff\":18,\"retry_spread\":0}" \
  --arm "jit18={$C,\"fano_window\":120,$P,\"retry_backoff\":18,\"retry_spread\":17}"
done

# D3. The manuscript's OWN band-floor sweep, remeasured with deterministic holds.
#
# `hysteresis.sh` H4 swept `retry_backoff = 4,8,12,16,20` at the default `retry_spread`, so the
# published claim that the initial-condition gap gates at four and twelve and not at sixteen and
# twenty was measured on holds smeared by plus or minus fifty percent: the rho=12 arm ran holds on
# [6,18], which straddles the predicted floor of 15.33, and the rho=16 arm ran [8,24]. The rescale
# preserves the MEAN, so a smooth monotone response is barely affected, but the location of a
# transition is not something a smeared instrument can place. This is the manuscript's own number
# and it is remeasured here rather than defended.
#
# REGISTERED, and it is a check rather than a conjecture: the deterministic sweep reproduces the
# published pattern, a gated gap at rho = 4 and 12 and none at 16 and 20, so the predicted floor of
# 15.33 still lies inside the measured interval. FALSIFIER: the transition moves outside [12, 16],
# in which case the paper's floor sentence is measured wrong and must be restated with the new
# interval whatever it is.
echo "### D3 the band floor with deterministic holds (queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'retry_backoff=4,8,12,14,16,18,20' \
  --arm "burst={$D,\"n_blue\":5,\"retry_prob\":1.0,\"retry_spread\":0}" \
  --arm "stag={$D,\"n_blue\":5,\"retry_prob\":1.0,\"retry_spread\":0,\"stagger_decisions\":true}"

# D4. THE ONE CELL IN THIS PROJECT WHERE SUSTAINED LOAD IS OFF BY CONSTRUCTION.
#
# CR-23's unplanned result: at n = 4 and rho = 21, GE-120 gates at -0.052 while Bernoulli sits at
# -0.024 ungated, and no drop probability `d` in [0,1] puts the congestion threshold `n*` below 4.
# Every P1/P2 pair above has to argue the mean-shift confound away by matching. Here it is
# unavailable in principle, which makes this the best clustering cell the project has.
#
# Fable proposed the pair as rho = 10 with spread 22 against fixed rho = 21. That is NOT mean
# matched: the hold is floored at one step, so spread 22 on a base of 10 delivers a mean of 12.13,
# not 21, and the arm would have won on the mean alone. Solved by value over the full cooldown
# support instead: `retry_backoff = 21` with `retry_spread = 5` gives mean 21.00 on support
# [16,26], and with `retry_spread = 21` gives mean 21.04 on support [1,42]. Both hold the mean
# against the fixed control's [21,21] and they differ only in width, which turns the pair into a
# three-point width ladder and gives P3 its monotonicity test at the free cell.
#
# REGISTERED. Jitter at matched mean erases the gated GE damage down toward the Bernoulli floor,
# and monotonically in width, which confirms the pump at an operating point where load cannot be
# the explanation. FALSIFIER: the damage survives both jitter widths, in which case the pump is not
# phase compression, and the determinism stratum inherits the file.
for M in success served_per_step arrival_fano; do
echo "### D4 matched-mean jitter where sustained load is off by construction ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=3,4' \
  --arm "ge_noretry={$C,$G}" \
  --arm "ge_fix21={$C,$G,$P,\"retry_backoff\":21,\"retry_spread\":0}" \
  --arm "ge_jit05={$C,$G,$P,\"retry_backoff\":21,\"retry_spread\":5}" \
  --arm "ge_jit21={$C,$G,$P,\"retry_backoff\":21,\"retry_spread\":21}" \
  --arm "be_noretry={$C,\"fano_window\":120}" \
  --arm "be_fix21={$C,\"fano_window\":120,$P,\"retry_backoff\":21,\"retry_spread\":0}"
done

# The n = 3 rung in that sweep is Fable's free falsifier and is worth naming separately. Sustained
# load is off at n = 4, but TRANSIENT load is not: the post-fade spike books `n*d/mu` = 20.8 steps
# against a patience of 20, so the cluster can just barely outlast the requesters' deadline. At
# n = 3 the same arithmetic gives 15.6 steps, comfortably inside P, so the spike account predicts
# NO gated damage there. If n = 3 gates at a similar size the spike arithmetic is wrong and the
# candidate list reopens. That is why it rides in the same sweep rather than a later one.

# D5. AUDIT: is the n = 4 cell an artifact of every vehicle starting in phase?
#
# All blue spawn together and consult on a common clock, so a synchronized first consultation is
# baked in before any channel effect. `stagger_decisions` gives each vehicle an independent
# starting phase. REGISTERED, as an audit with a pre-committed tolerance rather than a conjecture:
# the staggered start shrinks the n = 4 GE-versus-Bernoulli difference by at most 40% and it
# survives, because a synchronized start is ONE extra compression against roughly three fades per
# mission. FALSIFIER: the difference loses more than 40% or stops gating, in which case the cell is
# sculpture, it does not become a poster, and this line is what says so.
echo "### D5 audit: the n=4 cell under staggered starting phases (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=4' \
  --arm "ge_fix21={$C,$G,$P,\"retry_backoff\":21,\"retry_spread\":0}" \
  --arm "ge_fix21_stag={$C,$G,$P,\"retry_backoff\":21,\"retry_spread\":0,\"stagger_decisions\":true}" \
  --arm "be_fix21={$C,$P,\"retry_backoff\":21,\"retry_spread\":0}" \
  --arm "be_fix21_stag={$C,$P,\"retry_backoff\":21,\"retry_spread\":0,\"stagger_decisions\":true}"

# D6. AUDIT: is the damage a per-step rate or a fixed mission-length toll?
#
# Every result in this project is measured at a 1800 s mission. A congestion mechanism should cost
# a RATE, so the per-step damage should be flat in mission length while the success damage need not
# be. REGISTERED: `served_per_step` damage at n = 4 is stable across 1200, 1800 and 3600 s.
# FALSIFIER: the per-step damage moves monotonically with duration, in which case what is being
# measured is a transient of the opening minutes and the mechanism claim needs restating.
for M in served_per_step success; do
echo "### D6 audit: mission length, 1200 / 1800 / 3600 s ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'duration=1200,1800,3600' \
  --arm "ge_noretry={$C,$G,\"n_blue\":4}" \
  --arm "ge_fix21={$C,$G,\"n_blue\":4,$P,\"retry_backoff\":21,\"retry_spread\":0}" \
  --arm "be_fix21={$C,\"n_blue\":4,$P,\"retry_backoff\":21,\"retry_spread\":0}"
done
