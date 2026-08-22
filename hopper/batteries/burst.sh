# C1 (backlog) crossed with CR-17. The C0-C5 ladder loses messages independently, and real jamming
# does not: losses arrive in runs. `channel="gilbert_elliot"` is calibrated so its stationary drop
# rate equals the ladder value at every rung (verified: 0.050/0.099/0.199/0.351/0.551 against
# nominal, mean loss-run 4.0 against Bernoulli's 1.05 to 2.23), so any difference is attributable
# to burst structure alone. Otte, Kuhlman and Sofge sweep both channels for exactly this reason.
#
# The first question is the recorded backlog item: does the modality crossover rung move?
#
# The second is new, and it is the one worth the cores. A burst DROPS requests, and a dropped
# request is one the operator never has to work, so burstiness should HELP a queue. It does, with
# the reliance loop open. Close the loop (CR-17) and the sign flips: the vehicles that abandoned
# together during a burst come back together after it, onto an operator that just idled, which is
# the synchronized start that lands inside the fold band on the collapsed branch. Local probe at
# n=5, rung 2: retry off, GE 0.794 against Bernoulli 0.757; retry on, GE 0.343 against 0.609.
#
# The isolating quantity is the difference of differences, gated by tools/ar_contrast.py --did.
. hopper/batteries/_common.sh
GE='"channel":"gilbert_elliot"'
R='"retry_prob":1.0,"retry_backoff":4'

echo "### C1 does burstiness move the modality crossover, at matched mean drop rate?"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=0,1,2,3,4,5' \
  --arm "dir_bern={\"control_mode\":\"direct\",\"n_blue\":6}" \
  --arm "dir_ge={\"control_mode\":\"direct\",\"n_blue\":6,$GE}" \
  --arm "sup_bern={\"control_mode\":\"supervisory\",\"n_blue\":6}" \
  --arm "sup_ge={\"control_mode\":\"supervisory\",\"n_blue\":6,$GE}"

echo "### C2 does the reliance loop turn burstiness from a help into a harm? (queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "ge_off={\"control_mode\":\"direct\",\"n_blue\":5,$GE}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R}" \
  --arm "ge_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R,$GE}"

echo "### C3 the same contrast on mission outcome"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "ge_off={\"control_mode\":\"direct\",\"n_blue\":5,$GE}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R}" \
  --arm "ge_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R,$GE}"
