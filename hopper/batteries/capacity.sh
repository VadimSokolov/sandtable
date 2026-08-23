# CR-54. THE CONSOLE'S CAPACITY IS CONSERVED, AND POLICY ONLY DECIDES HOW IT IS SPENT.
#
# CR-47 and CR-48 produced four levers that reach nearly the same delivered service on a collapsed
# blind console: refuse at the door (0.1490), work newest-first (0.1464), bound the queue at k*
# (0.1476), against oldest-first's 0.0023. A fifth, RANDOM order, recovers almost nothing (0.0100,
# TOST-equivalent to zero at n=16). That is the clue this battery chases: if breaking FIFO were the
# mechanism, random would work. It does not, so the mechanism is not the order.
#
# The proposed mechanism is an accounting identity. Every step the console is busy goes either to a
# request someone is still holding for (n_serviced) or to one whose requester has already given up
# and re-asked (n_stale). Those are the only two bins, so
#
#     served_per_step + stale_frac * requests_per_step  =  mu * operator_utilization
#
# and the whole design problem has ONE degree of freedom: what fraction of a fixed capacity is spent
# on answers nobody is waiting for. Oldest-first maximises that fraction by construction, because
# the oldest request is the one most likely to have expired. Random draws it at the population rate.
# The three working levers each drive it to near zero by a different route, which is why they
# substitute (CR-47 P4) rather than stack.
#
# v2, AFTER ADVERSARIAL REVIEW AND BEFORE ANY FULL-TIER ROW WAS READ. Two corrections, both from
# the reviewer, both confirmed against the source rather than accepted:
#
#   (a) THE PARTITION HAS FOUR BINS, NOT TWO. A claimed slot exits as serviced, as stale, as a reply
#   the DOWNLINK dropped, or as a reply that arrived after its requester had gone. `n_abandon_queue`
#   and `n_abandon_link` cannot stand in for the last two, because each also counts paths where no
#   slot was claimed at all. `n_worked_lost` and `n_worked_late` were added for exactly this and the
#   battery reads them as rates.
#
#   (b) MEAN BACKLOG IS THE WRONG UNIT FOR STARVATION. It counts requests that never leave, which is
#   a memory statistic, and under newest-first a starved requester re-asks and its new request lands
#   on top of the pile it was buried under, so the requests starve and the VEHICLES may not.
#   `starved_frac` (asked at least once, never once answered) and `answer_rate_v` are the harm
#   statistics and are read here for the first time.
#
#   The reviewer also timestamped a prediction against P1, recorded here before the run: the
#   residual is rank-ordered fifo ~ rand > lifo > admit, peaks at n = 6 to 10, and nearly closes at
#   n = 16.
#
#   P1 confirmation: the identity closes on FOUR bins. |LHS - RHS| < 2 * the gate's materiality
#     floor at every cell, where LHS is served + stale + worked_lost + worked_late.
#   P2 open: stale_frac at n=16 clear is ordered fifo > rand >> lifo > bound > admit, and the
#     ordering of served_per_step is its exact inverse at every span.
#   P3 open: the three working levers are TOST-equivalent to each other on served_per_step at
#     n >= 10 clear, while all three separate from rand and fifo.
#   P4 open: they are NOT equivalent on backlog_mean. bound < admit << fifo < lifo, and lifo is
#     ABOVE fifo, because the requests it never serves are the ones that never leave.
#   P5 open: on a C3 link the identity still closes but the split moves, because utilization itself
#     falls and there is less capacity to misspend.
#   P6 open, AND IT IS THE ONE THAT CAN COST A PUBLISHED SENTENCE: operator_utilization is
#     INVARIANT across the five arms at n >= 8, within one materiality floor. If it is, then the
#     spread in delivered service is composition and not effort, and that is the sentence rather
#     than any of the per-arm numbers.
#   P7 open, and it contradicts a paragraph already in the manuscript: newest-first does NOT starve
#     vehicles. starved_frac is near zero under newest-first, the bound and admission control, and
#     LARGE under oldest-first and random order, so the manuscript's "throughput bought by starving
#     the tail" is backwards and the backlog figure it cites is measuring zombie requests.
#
# FALSIFIER for P1, which is the only limb that can void the framing: if the identity misses by more
# than 2 * MPE at more than 2 of the cells, or if the residuals are rank-ordered by arm, then
# service is leaking somewhere these two counters do not see and the one-degree-of-freedom claim is
# retracted rather than patched.
. hopper/batteries/_common.sh
CD='"control_mode":"direct","queue_model":"buffer"'
AD='"queue_policy":"admit"'
LI='"queue_discipline":"patient_first"'

for M in served_per_step stale_per_step worked_lost_per_step worked_late_per_step \
         worked_per_step operator_utilization starved_frac answer_rate_v \
         requests_per_step stale_frac backlog_mean; do
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
