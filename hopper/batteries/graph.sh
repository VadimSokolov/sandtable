# CR-68. DOES THE TOPOLOGY CARRY ANYTHING THE GEOMETRY DOES NOT?
#
# Registered in doc/autoresearch-conjectures.md. CR-60 scored four GEOMETRIC readings of one set of
# positions and recommended the one that never looks at the commanded formation: the RMS distance of
# the living force from its own centroid. This battery adds two GRAPH readings of the same positions,
# from the resilient-consensus literature: algebraic connectivity, which an earlier idea in this
# project's notes proposed for the degradation ladder, and exact vertex connectivity, which is the
# quantity the 2f+1 result is stated in. The literature says those two disagree with each other and
# the path graph shows they do. The question here is different and it is the one a requirement needs
# answered: does either of them order the design space the way mission success does BETTER than the
# geometric reading already recommended, and at what cost in assumptions.
#
# The cost is a parameter. A graph reading needs a peer-link range assumed before it can be computed
# and the geometric reading needs nothing, so X2 exists to show the band outside which the graph
# reading saturates and stops discriminating at all.
. hopper/batteries/_common.sh
F='"control_mode":"supervisory","blue_behavior":"leader_follow","follow_mode":"link","comms_level":0,"graph_range":400'
ST='"follow_topology":"star"'
CH='"follow_topology":"chain"'

echo "### BATTERY graph START"

# X1. Six readings of one set of positions, across topology, commanded spread and column length.
# Scored exactly as CR-60 scored its four: inversions counted only over the pairs mission success
# separates, and a separating threshold reported only where one exists.
for M in success fleet_spread_mean fleet_cross_mean station_err_mean station_cross_mean fleet_fiedler_mean fleet_kappa_mean fleet_faults_mean fleet_disconnected_frac; do
echo "### X1 the geometric and graph readings on one grid ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,8,12,16' \
  --arm "starTight={$F,$ST}" \
  --arm "starWide={$F,$ST,\"formation_spread\":300}" \
  --arm "chainTight={$F,$CH}" \
  --arm "chainWide={$F,$CH,\"formation_spread\":300}" \
  --arm "starVeryWide={$F,$ST,\"formation_spread\":600}"
done

# X2. What the graph reading costs in assumptions. Outside a band of assumed peer-link range it
# saturates: everything is complete at a generous range and everything is severed at a tight one,
# and a saturated reading cannot separate anything. The registered expectation is that the band
# exists and is narrow, which is the argument for the parameter-free geometric reading rather than
# against the graph one.
for M in fleet_fiedler_mean fleet_kappa_mean fleet_faults_mean fleet_disconnected_frac success; do
echo "### X2 the band of assumed link range in which a graph reading discriminates ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'graph_range=150,250,400,600,1000' \
  --arm "starTight={$F,$ST,\"n_blue\":8}" \
  --arm "starWide={$F,$ST,\"n_blue\":8,\"formation_spread\":300}" \
  --arm "chainTight={$F,$CH,\"n_blue\":8}" \
  --arm "chainWide={$F,$CH,\"n_blue\":8,\"formation_spread\":300}" \
  --arm "starVeryWide={$F,$ST,\"n_blue\":8,\"formation_spread\":600}"
done

# X3. The disturbance family CR-60 used, which degrades the FOLLOW CHANNEL rather than the commanded
# geometry. A reading computed from positions should follow the positions the disturbance actually
# produces, and the two families are carried together so the graph readings are scored on the same
# disturbances the geometric ones were.
for M in success fleet_spread_mean fleet_fiedler_mean fleet_kappa_mean fleet_disconnected_frac station_err_mean; do
echo "### X3 the graph readings under a degraded follow channel ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'follow_outage=0,40,160,320' \
  --arm "star={$F,$ST,\"n_blue\":8}" \
  --arm "chain={$F,$CH,\"n_blue\":8}" \
  --arm "starWide={$F,$ST,\"n_blue\":8,\"formation_spread\":300}"
done

# X4. The family a formation metric must be BLIND to, now with the graph readings in it. Route bias
# moves the whole force without changing its internal geometry, so a reading that fires on it is
# reporting the route and calling it a formation. CR-60 established that the recommended geometric
# reading is blind; whether a graph reading is has never been asked.
for M in success fleet_spread_mean fleet_fiedler_mean fleet_kappa_mean fleet_faults_mean fleet_disconnected_frac; do
echo "### X4 the nuisance family, with the graph readings in it ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'route_bias=0.0,0.25,0.5,0.75,1.0' \
  --arm "tightEight={$F,$ST,\"n_blue\":8}" \
  --arm "wideEight={$F,$ST,\"n_blue\":8,\"formation_spread\":300}" \
  --arm "tightSixteen={$F,$ST,\"n_blue\":16}" \
  --arm "wideSixteen={$F,$ST,\"n_blue\":16,\"formation_spread\":300}"
done

echo "### BATTERY graph DONE"
