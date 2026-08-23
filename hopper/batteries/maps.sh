# THE STARVATION REVERSAL, REPLICATED ACROSS THE THREE MAPS.
#
# Registered as the reviewer's precondition on the Round 28 spine question: before any Discussion
# paragraph generalizes from "the metric that reads the requester disagrees with the two that read
# the console", the disagreement has to survive a change of world. It was measured on one map. The
# three maps in this model are not cosmetic: banded gives a covered route beside a fast open one,
# chokepoint forces the force to converge at a place the terrain chooses, and open removes cover
# altogether. Mission success across them runs 0.887 / 0.751 / 0.560 at eight assets, so they are a
# real perturbation of everything downstream of the console.
#
#   N1. THE REVERSAL SURVIVES. On all three maps, mean backlog ranks newest-first at or below
#       oldest-first while the per-vehicle answer rate ranks it far above. FALSIFIER: any map where
#       backlog and answer rate agree, which would make the disagreement a property of one world.
#   N2. UTILIZATION STAYS BLIND ON ALL THREE. The five disciplines stay within the gate's
#       equivalence margin on operator utilization while the answer rate spans an order of
#       magnitude. FALSIFIER: utilization separating the disciplines on any map.
#   N3. THE COLLAPSE SPAN MOVES WITH THE MAP AND THE STARVATION ONSET MOVES WITH IT. The onset is a
#       queue phenomenon, so it must track the span at which the console saturates rather than the
#       terrain. FALSIFIER: an onset that is the same span on all three maps despite different
#       saturation, or one that moves without utilization moving.
. hopper/batteries/_common.sh
CD='"control_mode":"direct","queue_model":"buffer"'
AD='"queue_policy":"admit"'
LI='"queue_discipline":"patient_first"'

echo "### BATTERY maps START"

for T in band chokepoint open; do
for M in starved_frac answer_rate_v backlog_mean operator_utilization served_per_step success; do
echo "### N1 the five levers on the $T map ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,12,16' \
  --arm "fifo={$CD,\"comms_level\":0,\"terrain_profile\":\"$T\"}" \
  --arm "rand={$CD,\"comms_level\":0,\"terrain_profile\":\"$T\",\"queue_discipline\":\"random\"}" \
  --arm "lifo={$CD,\"comms_level\":0,\"terrain_profile\":\"$T\",$LI}" \
  --arm "bound={$CD,\"comms_level\":0,\"terrain_profile\":\"$T\",\"queue_capacity\":2}" \
  --arm "admit={$CD,\"comms_level\":0,\"terrain_profile\":\"$T\",$AD}"
done
done

echo "### BATTERY maps COMPLETE"
