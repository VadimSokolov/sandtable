# CR-54 CONTINUED. THE METRICS JOB 9449071 DID NOT REACH BEFORE ITS TIME LIMIT.
#
# 9449071 completed all FOUR BINS on both K1 (clear) and K2 (C3): served, stale, worked_lost and
# worked_late, which is the whole of P1. It was cancelled at two hours part-way through the sum,
# which is computable from the four, and never reached operator_utilization, starved_frac or
# answer_rate_v. Those three carry P6 and P7 and are the two headline reads, so they run here.
#
# Registrations unchanged from capacity.sh, which was written before 9449071 ran:
#   P6. operator_utilization is INVARIANT across the five arms at n >= 8, within one materiality
#       floor. The four bins already say this indirectly, since they sum to within 0.0014 of each
#       other across arms whose delivered service spans a factor of 65, but the direct measurement
#       is the one to quote and it is the one that can still fail.
#   P7. newest-first does NOT starve vehicles. starved_frac near zero under lifo, the bound and
#       admit; large under fifo and rand. This contradicts a paragraph that was in the manuscript
#       and has since been corrected on a single-seed smoke run; this is the full-tier check of the
#       correction, and if it fails the correction was wrong too.
. hopper/batteries/_common.sh
CD='"control_mode":"direct","queue_model":"buffer"'
AD='"queue_policy":"admit"'
LI='"queue_discipline":"patient_first"'

for M in operator_utilization starved_frac answer_rate_v requests_per_step backlog_mean; do
echo "### K1 the five levers, clear link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10,12,16' \
  --arm "fifo={$CD,\"comms_level\":0}" \
  --arm "rand={$CD,\"comms_level\":0,\"queue_discipline\":\"random\"}" \
  --arm "lifo={$CD,\"comms_level\":0,$LI}" \
  --arm "bound={$CD,\"comms_level\":0,\"queue_capacity\":2}" \
  --arm "admit={$CD,\"comms_level\":0,$AD}"
echo "### K2 the five levers, C3 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,5,6,8,10,12,16' \
  --arm "fifo={$CD,\"comms_level\":3}" \
  --arm "rand={$CD,\"comms_level\":3,\"queue_discipline\":\"random\"}" \
  --arm "lifo={$CD,\"comms_level\":3,$LI}" \
  --arm "bound={$CD,\"comms_level\":3,\"queue_capacity\":1}" \
  --arm "admit={$CD,\"comms_level\":3,$AD}"
done
