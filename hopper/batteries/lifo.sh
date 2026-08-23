# CR-47. NEWEST-FIRST ON A CONSOLE THAT CANNOT DETECT ABANDONMENT.
#
# The published operator is a reservation system, not a queue: a request is committed to a slot at
# ARRIVAL. CR-46 registered six predictions about queue discipline against it and none of them is
# reachable, because nothing ever waits anywhere it could be reordered. `queue_model = "buffer"` is
# the positive control that obligation demanded, and building it produced this.
#
# Under `blind`, oldest-first serves the request most likely to have expired. Newest-first serves the
# freshest, which is the one most likely to still be waited on. Barrer 1957 is the original
# statement that with impatient customers the service ORDER changes how many are lost.
#
# G0 is the INSTRUMENT GATE and it blocks everything else. Buffer must reproduce reserve under the
# policies where the console never commits beyond what it can serve. `blind` is excluded on purpose:
# reserve books doomed work at an ever-receding free time and over-commits past the mission end.
#
#   P1 confirmation: patient_first - fcfs on served_per_step, blind, positive and gated at n >= 8.
#   P2 open: the same on success.
#   P3 open: the sign is negative at n <= 6 and positive at n >= 8.
#   P4 open: under admit the same contrast is NEGATIVE (the two levers substitute).
#   P5 open: it survives with the reliance loop closed.
#   P6 open: the backlog is larger under newest-first, which is what starving the tail costs.
. hopper/batteries/_common.sh
CD='"control_mode":"direct"'
BUF='"queue_model":"buffer"'
RF='"queue_policy":"refund"'
AD='"queue_policy":"admit"'
LI='"queue_discipline":"patient_first"'
RT='"retry_prob":1.0,"retry_backoff":4'

for M in served_per_step requests_per_step; do
echo "### G0 the instrument gate, buffer against reserve where they must agree ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12,16' \
  --arm "res_ref={$CD,\"comms_level\":0,$RF}" \
  --arm "buf_ref={$CD,\"comms_level\":0,$RF,$BUF}" \
  --arm "res_adm={$CD,\"comms_level\":0,$AD}" \
  --arm "buf_adm={$CD,\"comms_level\":0,$AD,$BUF}"
done

for M in served_per_step success stale_frac backlog_mean blue_loss_frac; do
echo "### G1 newest-first against oldest-first on a blind console, clear link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10,12,16' \
  --arm "fifo={$CD,\"comms_level\":0,$BUF}" \
  --arm "lifo={$CD,\"comms_level\":0,$BUF,$LI}" \
  --arm "rand={$CD,\"comms_level\":0,$BUF,\"queue_discipline\":\"random\"}" \
  --arm "adm={$CD,\"comms_level\":0,$BUF,$AD}"
done

for M in served_per_step success; do
echo "### G2 the same on a degraded link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3,4' \
  --arm "fifo={$CD,\"n_blue\":10,$BUF}" \
  --arm "lifo={$CD,\"n_blue\":10,$BUF,$LI}"
echo "### G3 substitution: does newest-first still pay once the console can refuse ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10,12,16' \
  --arm "adm_fifo={$CD,\"comms_level\":0,$BUF,$AD}" \
  --arm "adm_lifo={$CD,\"comms_level\":0,$BUF,$AD,$LI}"
echo "### G4 the reliance loop closed ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10,12' \
  --arm "fifo_rt={$CD,\"comms_level\":0,$BUF,$RT}" \
  --arm "lifo_rt={$CD,\"comms_level\":0,$BUF,$LI,$RT}"
done
