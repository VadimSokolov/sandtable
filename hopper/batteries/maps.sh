# CR-52. EVERY RESULT IN THIS PAPER WAS FOUND ON ONE MAP.
#
# build_world produced one profile until today: a lateral Gaussian band of cover broadcast along the
# whole field, with no longitudinal structure, so a route choice is a choice of latitude. Two new
# maps, chosen to attack from opposite sides. `open` has no cover at all and is the negative control
# for anything claimed about terrain. `chokepoint` is a transverse ridge with one gap, so a dispersed
# force must converge where the MAP chooses rather than where the operator does.
#
# REGISTERED (CR-52), before any arm on a new map was read:
#   P1. admit over blind holds its sign and gates on success AND served_per_step, at the collapse
#       span, on both new maps.
#   P2. the capacity ladder's argmax is unchanged by the map.
#   P3. the collapse span is SMALLER on chokepoint than on band.
. hopper/batteries/_common.sh
BLIND='"control_mode":"direct","comms_level":0'
AD='"control_mode":"direct","comms_level":0,"queue_policy":"admit"'
BUF='"control_mode":"direct","comms_level":0,"queue_model":"buffer","queue_policy":"blind"'

for M in success served_per_step operator_goodput requests_per_step; do
echo "### M1 the lever against the map ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12,16' \
  --arm "band_blind={$BLIND}" \
  --arm "band_admit={$AD}" \
  --arm "open_blind={$BLIND,\"terrain_profile\":\"open\"}" \
  --arm "open_admit={$AD,\"terrain_profile\":\"open\"}" \
  --arm "choke_blind={$BLIND,\"terrain_profile\":\"chokepoint\"}" \
  --arm "choke_admit={$AD,\"terrain_profile\":\"chokepoint\"}"
done

for M in served_per_step success; do
echo "### M2 the capacity ladder against the map ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "band_c1={$BUF,\"queue_capacity\":1}" \
  --arm "band_c2={$BUF,\"queue_capacity\":2}" \
  --arm "band_c4={$BUF,\"queue_capacity\":4}" \
  --arm "choke_c1={$BUF,\"queue_capacity\":1,\"terrain_profile\":\"chokepoint\"}" \
  --arm "choke_c2={$BUF,\"queue_capacity\":2,\"terrain_profile\":\"chokepoint\"}" \
  --arm "choke_c4={$BUF,\"queue_capacity\":4,\"terrain_profile\":\"chokepoint\"}" \
  --arm "open_c1={$BUF,\"queue_capacity\":1,\"terrain_profile\":\"open\"}" \
  --arm "open_c2={$BUF,\"queue_capacity\":2,\"terrain_profile\":\"open\"}" \
  --arm "open_c4={$BUF,\"queue_capacity\":4,\"terrain_profile\":\"open\"}"
done
