# CR-18, complete. The first repair priced only the REPLY by its lag and left the request drawing
# one chain transition per message, so two requests four steps apart were still adjacent in chain
# time. Under the completed repair the chain is indexed by TIME: `delivered` advances it by the
# number of steps since it was last resolved, so a chain consulted rarely has decayed toward
# stationarity by the time it is consulted. The marginal drop rate is unchanged at every rung
# (0.0495 / 0.0995 / 0.2016 / 0.3511 / 0.5494 against nominal), so the channels still differ only
# in structure.
#
# This supersedes st-clock-9443902 and st-bclock-9443926, both of which ran the half repair.
# Registered, from the half-repair result and a 64-seed probe of the full one: K1's sign flip
# should vanish, and the J-series interaction should shrink again but may not reach zero. I
# predicted a null for the half repair and was refuted, so this time the registration is that the
# interaction SURVIVES at rung 2 and is null at rung 1.
. hopper/batteries/_common.sh
R='"retry_prob":1.0,"retry_backoff":4'
GEM='"channel":"gilbert_elliot"'
GES='"channel":"gilbert_elliot","channel_clock":"step"'

echo "### K1 rung 3 span sweep under both clocks: does the flip survive physical timing?"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6,7,8,9,10,11,12' \
  --arm "bern={\"control_mode\":\"direct\",\"comms_level\":3}" \
  --arm "ge_msg={\"control_mode\":\"direct\",\"comms_level\":3,$GEM}" \
  --arm "ge_step={\"control_mode\":\"direct\",\"comms_level\":3,$GES}"

echo "### K2 the clock must not touch a memoryless channel"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=1,2,3,4' \
  --arm "bern_msg={\"control_mode\":\"direct\",\"n_blue\":8}" \
  --arm "bern_step={\"control_mode\":\"direct\",\"n_blue\":8,\"channel_clock\":\"step\"}"

echo "### J1 the burst-times-reliance interaction under the completed repair (queue)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "ge_off={\"control_mode\":\"direct\",\"n_blue\":5,$GES}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R}" \
  --arm "ge_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R,$GES}"

echo "### J2 the same on mission outcome"
$PY tools/ar_eval.py $S --metric success $B --sweep 'comms_level=1,2,3' \
  --arm "bern_off={\"control_mode\":\"direct\",\"n_blue\":5}" \
  --arm "ge_off={\"control_mode\":\"direct\",\"n_blue\":5,$GES}" \
  --arm "bern_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R}" \
  --arm "ge_retry={\"control_mode\":\"direct\",\"n_blue\":5,$R,$GES}"
