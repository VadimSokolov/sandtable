# CR-66. WHAT A CONSOLE HAS TO KNOW IS SET BY HOW UNLIKE EACH OTHER ITS VEHICLES ARE.
#
# Registered in doc/autoresearch-conjectures.md with the pilot disclosed. Four rungs, each costing
# strictly more than the one below it, priced on the same console at the same span:
#
#   blind unbounded   knows nothing, refuses nothing
#   bounded k         knows nothing, refuses by overflow (drop the oldest at capacity)
#   admitting         reads the deadline field, refuses what it cannot finish
#   admitting + EDF   reads the same field twice, to refuse AND to order
#
# On a UNIFORM fleet the pilot puts a two-slot bound at 0.1476 served per step against the admitting
# console's 0.1489, with exclusion at 0.0000 in both: the deadline field buys essentially nothing
# over a free bound. On a TWO-POINT fleet the same bound gets 0.0602 against 0.1494 and excludes
# 0.3516. The variable that decides how much console information has to be bought is therefore the
# heterogeneity of the fleet, and V3 sweeps it to find where each rung starts earning.
. hopper/batteries/_common.sh
BLD='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind","n_blue":16'
BLDN='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"blind"'
ADM='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'
MIX='"patience_spread":12,"patience_shape":"twopoint"'

echo "### BATTERY ladder START"

# V1. The ladder against span on a UNIFORM fleet, where the registered prediction is that the free
# bound is equivalent to the deadline field on throughput and on exclusion, and the order adds
# nothing on top because there is nothing to order.
for M in served_per_step answer_rate_v starved_frac abandoned_per_step busy_dead success; do
echo "### V1 the four rungs on a uniform fleet ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24' \
  --arm "blindUnbound={$BLDN}" \
  --arm "boundOne={$BLDN,\"queue_capacity\":1}" \
  --arm "boundTwo={$BLDN,\"queue_capacity\":2}" \
  --arm "admits={$ADM}" \
  --arm "admitsEdf={$ADM,\"queue_discipline\":\"edf\"}"
done

# V2. The same four rungs on a TWO-POINT fleet, which is where the pilot says they come apart: the
# bound gets half the throughput and does NOT fix exclusion, the field gets the throughput and
# leaves 0.30 excluded, and only the field read twice gets both. If this holds it is the whole
# requirements argument in one section.
for M in served_per_step answer_rate_v starved_frac answer_step_share answer_step_censored abandoned_per_step busy_dead success; do
echo "### V2 the four rungs on a two-point fleet ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16,24' \
  --arm "blindUnbound={$BLDN,$MIX}" \
  --arm "boundOne={$BLDN,$MIX,\"queue_capacity\":1}" \
  --arm "boundTwo={$BLDN,$MIX,\"queue_capacity\":2}" \
  --arm "admits={$ADM,$MIX}" \
  --arm "admitsEdf={$ADM,$MIX,\"queue_discipline\":\"edf\"}"
done

# V3. The threshold section. Heterogeneity is the sweep and the rung is the arm, so each rung's
# curve can be read against the others and the crossing located. Zero spread is carried because the
# stratified readings are undefined there and their censoring flag has to be on the record beside
# them rather than inferred from a suspicious 1.0000.
for M in served_per_step answer_rate_v starved_frac answer_step_share answer_step_censored abandoned_per_step success; do
echo "### V3 where the deadline field starts earning, against fleet heterogeneity ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'patience_spread=0,3,6,9,12,18' \
  --arm "blindUnbound={$BLD,\"patience_shape\":\"twopoint\"}" \
  --arm "boundTwo={$BLD,\"patience_shape\":\"twopoint\",\"queue_capacity\":2}" \
  --arm "admits={$ADM,\"n_blue\":16,\"patience_shape\":\"twopoint\"}" \
  --arm "admitsEdf={$ADM,\"n_blue\":16,\"patience_shape\":\"twopoint\",\"queue_discipline\":\"edf\"}"
done

# V4. The sizing curve for the free rung. A bound is only a bound if it is TIGHT: the pilot reads
# 0.1476 served at capacity two and 0.0079 at capacity eight, so a loose bound is not a weak version
# of the repair, it is no repair. The section exists because a sizing rule is the part of a
# zero-information recommendation that a programme office can actually act on, and because a
# recommendation with an interior optimum has to have that optimum measured rather than asserted.
for M in served_per_step answer_rate_v starved_frac busy_dead abandoned_per_step dropped_frac; do
echo "### V4 how tight the free bound has to be ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'queue_capacity=1,2,3,4,6,8,12' \
  --arm "uniform={$BLD}" \
  --arm "twoPoint={$BLD,$MIX}"
done

echo "### BATTERY ladder DONE"
