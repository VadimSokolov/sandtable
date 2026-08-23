# CR-48. THE CONSOLE HAS BUFFERBLOAT, AND THE RIGHT BUFFER SIZE IS ALREADY DERIVED IN THIS PAPER.
#
# CR-47 P7's falsifier fired: a two-deep oldest-first queue reaches and slightly passes an unbounded
# newest-first one at every span. So the lever is the bound, not the inversion. The question this
# battery asks is whether the bound has a derivation or is a tuned parameter.
#
# A request joining a buffer holding k-1 others, with one more in service, is answered at
# 2L + (k+1)/mu after it was sent, so it makes its deadline only while (k+1)/mu <= P - 2L:
#
#     k* = floor((P - 2L) * mu) - 1
#
# At the published point (P=20, 1/mu=6.67) that is 2 clear and 0 at C3. The arms are the capacities
# and the SWEEP is the parameter the rule depends on, so each sweep point yields an argmax that can
# be read against a prediction with no fitting.
#
#   P1 confirmation: argmax at rung 0 is in {1, 2}.
#   P2 open: argmax at C3 is 0 or 1.
#   P3 open: patience 20/30/45 moves the argmax to 2/3/5.
#   P4 open: service rate 0.075/0.15/0.30 moves it to 0/2/5.
#   P5 open: the bound is not worse than admission control on delivered service at the collapse span.
#
# CR-49 rides on Q3. The mean-fits rule above tests E[W] <= D when the deadline test is a
# probability, and W is Erlang(k+1, mu), which is right-skewed, so the mean over-states the typical
# wait and the rule under-sizes the buffer. Replacing the mean with the median gives
#
#     k* = median(Poisson((P - 2L) mu)) - 1  ~=  floor((P - 2L) mu + 1/3) - 1     (Choi 1994)
#
# The two rules disagree at exactly four of the ten operating points in this battery, and the
# patience sweep below carries three of them. Predictions, mean-fits vs median-fits:
#   P=12 -> 0 vs 1     P=20 -> 2 vs 2     P=25 -> 2 vs 3     P=27 -> 3 vs 3
#   P=30 -> 3 vs 3     P=34 -> 4 vs 4     P=38 -> 4 vs 5     P=45 -> 5 vs 6
# The four ties are the controls: an argmax that misses them fails both rules at once.
. hopper/batteries/_common.sh
CD='"control_mode":"direct","queue_model":"buffer","queue_policy":"blind"'
CAPS='cap_none=-1 cap_zero=0 cap_one=1 cap_two=2 cap_three=3 cap_four=4 cap_five=5 cap_six=6 cap_ten=10'

# The capacity ladder as arms, so any sweep below reads an argmax per sweep point.
mkarms() {
  A=""
  for kv in $CAPS; do
    nm=${kv%%=*}; v=${kv##*=}
    A="$A --arm $nm={$CD,\"queue_capacity\":$v$1}"
  done
  echo "$A"
}

for M in served_per_step success dropped_frac; do
echo "### Q1 the capacity ladder against span, clear link ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,10,12,16' $(mkarms ',"comms_level":0')
echo "### Q2 the capacity ladder against span, C3 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,10,12,16' $(mkarms ',"comms_level":3')
done

for M in served_per_step success; do
echo "### Q3 the capacity ladder against PATIENCE, clear link, n=12 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'patience=12,20,25,27,30,34,38,45' \
  $(mkarms ',"comms_level":0,"n_blue":12')
echo "### Q4 the capacity ladder against SERVICE RATE, clear link, n=12 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'service_rate=0.075,0.15,0.30' \
  $(mkarms ',"comms_level":0,"n_blue":12')
echo "### Q5 the requirements ladder: a counter, a stack, a message field ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=6,8,10,12,16' \
  --arm "bound={$CD,\"comms_level\":0,\"queue_capacity\":2}" \
  --arm "newest={$CD,\"comms_level\":0,\"queue_discipline\":\"patient_first\"}" \
  --arm "deadline={\"control_mode\":\"direct\",\"queue_model\":\"buffer\",\"queue_policy\":\"admit\",\"comms_level\":0}" \
  --arm "nothing={$CD,\"comms_level\":0}"
done
