# CR-60. THE DISSOCIATION HAS A DIRECTION, AND IT RESCUES THE METRIC INSTEAD OF DISCARDING IT.
#
# Registered in doc/autoresearch-conjectures.md with its 24-replication pilot disclosed. CR-57 D1
# left a bare null: station-keeping error does not predict mission outcome. This battery asks which
# COMPONENT the mission is blind to. `station_along_mean` and `station_cross_mean` resolve the same
# error onto the reference's heading and its normal; `fleet_spread_mean` is the independent check
# with no commanded geometry in it.
#
# The two families are the whole design. One holds the commanded geometry fixed and degrades the
# tracking of it (follow_outage); the other holds the tracking fixed and degrades the commanded
# geometry (formation_spread). Station error cannot tell them apart. Everything here is about
# whether a projection can.
. hopper/batteries/_common.sh
F='"control_mode":"supervisory","blue_behavior":"leader_follow","follow_mode":"link","follow_topology":"star","comms_level":0,"n_blue":8'

echo "### BATTERY cross START"

# L1, J1 and J2 in one table. The two families side by side on one sweep so the pooled ordering is
# read off a single frame and the within-family ordering off each half of it.
for M in success station_err_mean station_cross_mean fleet_spread_mean fleet_along_mean fleet_cross_mean support_frac; do
echo "### L1 the two families against every reading of the same positions ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8' \
  --arm "base={$F}" \
  --arm "out40={$F,\"follow_outage\":40}" \
  --arm "out80={$F,\"follow_outage\":80}" \
  --arm "out160={$F,\"follow_outage\":160}" \
  --arm "out320={$F,\"follow_outage\":320}" \
  --arm "sp60={$F,\"formation_spread\":60}" \
  --arm "sp120={$F,\"formation_spread\":120}" \
  --arm "sp300={$F,\"formation_spread\":300}" \
  --arm "sp450={$F,\"formation_spread\":450}" \
  --arm "sp600={$F,\"formation_spread\":600}"
done

# L2, J3. The mechanism test, and the one that can fail while L1 holds. If cross-track error costs
# mission outcome because it leaves a survivable corridor, then removing the corridor removes most
# of the penalty. Terrain is the sweep so the same arms are read in three worlds.
for M in success station_cross_mean fleet_spread_mean fleet_cross_mean support_frac; do
echo "### L2 does the penalty need a corridor ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'terrain_profile=banded,chokepoint,open' \
  --arm "base={$F}" \
  --arm "out320={$F,\"follow_outage\":320}" \
  --arm "sp120={$F,\"formation_spread\":120}" \
  --arm "sp300={$F,\"formation_spread\":300}" \
  --arm "sp600={$F,\"formation_spread\":600}"
done

# L3, J4. The acceptance rule needs the threshold to survive a column length it was not fitted on,
# because a threshold that only works at eight assets is a fitted constant and not a specification.
for M in success station_err_mean station_cross_mean fleet_cross_mean; do
echo "### L3 does one threshold survive column length ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,8,12,16' \
  --arm "base={$F}" \
  --arm "out320={$F,\"follow_outage\":320}" \
  --arm "sp300={$F,\"formation_spread\":300}" \
  --arm "sp600={$F,\"formation_spread\":600}"
done

# L4. And the bridge, which CR-58 says is the standard this project holds a forced probe to. A
# Gilbert-Elliot channel produces the same staleness stochastically. If the projection is an
# instrument and not an artefact of the sawtooth, it must read the same way under a real channel.
for M in success station_err_mean station_cross_mean fleet_cross_mean support_frac; do
echo "### L4 the same reading under a channel rather than a probe ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,2,3,4' \
  --arm "chan={$F,\"channel\":\"gilbert_elliot\",\"channel_clock\":\"step\",\"ge_burst_len\":60}" \
  --arm "chansp={$F,\"channel\":\"gilbert_elliot\",\"channel_clock\":\"step\",\"ge_burst_len\":60,\"formation_spread\":300}"
done

# L5 IS THE REGISTERED COUNTEREXAMPLE, and the pilot that suggested it is disclosed in the conjecture
# file: at a fixed 300 m spread, route_bias 0.0 gives fleet cross-track dispersion of 2.9 m, TIGHTER
# than the undisturbed formation, and mission success of 0.208. A formation metric cannot see a route
# error, exactly as a tracking metric cannot see a commanded-geometry error. If cross-track ordered
# this family too it would travel further than the blindness law predicts, which would be good news
# and would still have to be recorded against the law as stated.
for M in success fleet_cross_mean fleet_spread_mean station_cross_mean support_frac; do
echo "### L5 the family a formation metric must be blind to ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'route_bias=0.0,0.25,0.5,0.75,1.0' \
  --arm "tight={$F}" \
  --arm "sp300={$F,\"formation_spread\":300}"
done

echo "### BATTERY cross COMPLETE"
