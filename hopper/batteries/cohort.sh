# CR-21. J1 of `st-clockfull-9444130` gated a burst-times-reliance interaction on operator goodput
# at every rung (-0.0617 / -0.0509 / -0.0356, |t| up to 13.2) while the retry-free contrast was at
# most -0.008. So the retry is what makes the team sensitive to the link's burst structure, and
# nothing in the CR-19 closed form explains it: at a dwell of four the within-vehicle excess is
# 9e-5. There is a third mechanism and this battery goes after it.
#
# The candidate is a COHORT. A retry does two things the published parameterization cannot tell
# apart. It shortens the cycle, which is what opens the fold band, and it also rescales the
# standing jittered interval, which shrinks the ABSOLUTE jitter from about 22 steps to about 4. A
# common-mode outage drops several vehicles at once; with the standing cycle they disperse, with
# the rescaled backoff they come back together and hit one console as a block. `retry_spread` holds
# the backoff MEAN at rho and sets its jitter width independently, so the two can be separated for
# the first time. Verified: mean exactly rho for every spread used here, and spread=2 at rho=4
# reproduces the published rescale exactly, range [2, 6].
#
# Registered: |DiD| falls monotonically as the spread widens, and is largest at spread=0, where
# every retrying vehicle returns after exactly rho steps. If it is flat in the spread, the cohort
# is not the mechanism and I am still missing one.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step"'
M='"reply_model":"marginal"'
C='"control_mode":"direct","n_blue":5,"comms_level":1'

echo "### P1 does widening the backoff jitter dissolve the interaction? (rho=4, queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'retry_spread=0,1,2,3' \
  --arm "bern_off={$C}" \
  --arm "ge_off={$C,$G}" \
  --arm "bern_retry={$C,\"retry_prob\":1.0,\"retry_backoff\":4}" \
  --arm "ge_retry={$C,\"retry_prob\":1.0,\"retry_backoff\":4,$G}"

# rho = 4 admits a jitter of at most 3 steps before the floor at one step starts lifting the mean.
# rho = 12 admits 11, which is the full absolute spread of the standing cycle, so this section
# carries the range the mechanism needs while P1 carries the published operating point.
echo "### P2 the same across the full jitter range the standing cycle has (rho=12, queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'retry_spread=0,4,8,11' \
  --arm "bern_off={$C}" \
  --arm "ge_off={$C,$G}" \
  --arm "bern_retry={$C,\"retry_prob\":1.0,\"retry_backoff\":12}" \
  --arm "ge_retry={$C,\"retry_prob\":1.0,\"retry_backoff\":12,$G}"

# How much of J1 is the round-trip correlation bonus rather than the structure? The bonus RAISES
# delivery, so it works against the measured negative, and removing it should make the contrast
# MORE negative rather than less. If instead the contrast vanishes under `marginal`, J1 was the
# first moment all along and the cohort story is unnecessary.
echo "### P3 J1 decomposed: how much of it survives with round-trip delivery pinned? (queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "co_off={\"control_mode\":\"direct\",\"n_blue\":5,$G}" \
  --arm "mg_off={\"control_mode\":\"direct\",\"n_blue\":5,$G,$M}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,\"retry_prob\":1.0,\"retry_backoff\":4}" \
  --arm "co_retry={\"control_mode\":\"direct\",\"n_blue\":5,\"retry_prob\":1.0,\"retry_backoff\":4,$G}" \
  --arm "mg_retry={\"control_mode\":\"direct\",\"n_blue\":5,\"retry_prob\":1.0,\"retry_backoff\":4,$G,$M}"
