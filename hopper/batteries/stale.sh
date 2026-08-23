# CR-57. THE DISTURBANCE MEASURED IN ITS OWN COORDINATE.
#
# Registered in doc/autoresearch-conjectures.md as D1-D4, and the registered prediction is the
# REVIEWER'S rather than mine: mission outcome is FLAT in track age at every length up to 320 steps.
#
# CR-55 asked the follow question through two intermediaries: a channel that produces outages of a
# distribution rather than a length, and a composition of two slopes measured on different arms.
# Review found the transfer threshold I registered was my own `track_timeout` echoing back, and that
# the spread slope I composed with was read off the flat middle of a curve whose steep segment is the
# operating point. Both intermediaries are avoidable. The disturbance is TRACK AGE, so sweep it:
# `follow_outage = a` forces one refresh every a+1 steps whatever the channel does, so the age is a
# sawtooth from 0 to a with mean a/2, exactly and by construction.
#
#   D2. run it twice, timeout at its default and effectively infinite. Coinciding curves say the
#       channel acts smoothly and the timeout is not doing the work; separating curves say the
#       effect IS the mode transition and must be reported as one.
#   D3. mission outcome is flat in a, because a follower that cannot follow reverts to the scripted
#       behaviour this paper measures everywhere else, and that behaviour is not much worse.
#       FALSIFIER: any gated separation across the sweep.
#   D4. if D3 holds on the mean, the residual is the turn-aligned tail, so the map axis is where an
#       effect would have to live: the chokepoint profile turns the column most.
. hopper/batteries/_common.sh
F='"control_mode":"supervisory","blue_behavior":"leader_follow","follow_mode":"link","follow_topology":"star","comms_level":0'
INF='"track_timeout":1000000000'

# G1 is D2 and D3 together, and it is the whole conjecture.
for M in success station_err_mean follow_lost_frac; do
echo "### G1 mission outcome against forced track age, reversion on and off ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'follow_outage=0,20,40,80,160,320' \
  --arm "revert={$F,\"n_blue\":8}" \
  --arm "noreverts={$F,\"n_blue\":8,$INF}"
done

# G2 is the contrast that turns a null into a finding. Commanded spread and estimator error are
# measured on the SAME arm here, so the comparison is not across two experiments: geometry the
# planner ASKS for against geometry the estimator FAILS to hold.
for M in success station_err_mean time_to_objective; do
echo "### G2 commanded geometry on the same arm that the estimator disturbs ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'formation_spread=10,30,60,120,300,600' \
  --arm "commanded={$F,\"n_blue\":8}"
done

# G3 is D4. The map decides how much the reference turns, and a dead-reckoned track is only wrong
# while its reference is turning, so this is where a mean-null can still hide a tail.
for M in success station_err_mean; do
echo "### G3 the turn axis, at the outage length where reversion starts ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'follow_outage=0,80' \
  --arm "band={$F,\"n_blue\":8}" \
  --arm "choke={$F,\"n_blue\":8,\"terrain_profile\":\"chokepoint\"}" \
  --arm "open={$F,\"n_blue\":8,\"terrain_profile\":\"open\"}"
done

# G4 asks whether the null survives a longer column, since a star follower's station is rank*gap
# behind and the deepest follower in a sixteen-vehicle column is stationed 600 m back, which is
# where the commanded-spread sweep DOES bite.
for M in success station_err_mean; do
echo "### G4 does the null survive column length ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,8,12,16' \
  --arm "a0={$F,\"follow_outage\":0}" \
  --arm "a80={$F,\"follow_outage\":80}"
done
