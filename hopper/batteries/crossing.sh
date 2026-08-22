# CR-22. The burst-times-reliance interaction is MULTIPLICATIVE IN THE PAPER'S OWN COLLAPSE
# FORMULA, and neither factor alone crosses the threshold.
#
#     n_c = c mu (P + rho + 1) / d.
#
# A CR-17 retry cuts the NUMERATOR from 43 steps to 25. A long-dwell coherent channel raises the
# DENOMINATOR from 0.640 to about 0.780, because if the request got through the channel was good
# and is probably still good when the answer returns. Measured on the live model at rung 3:
#
#   arm                  cycle      d     n_c    five vehicles collapsed?
#   bern,  no retry         43  0.640   10.08    no
#   ge120, no retry         43  0.780    8.27    no
#   bern,  retry rho=4      25  0.640    5.86    no
#   ge120, retry rho=4      25  0.780    4.81    YES
#
# So five vehicles sits in the ONE cell where the two factors together carry the team over its own
# collapse span and neither does alone. That is why `ge_off - bern_off` is null at every dwell and
# `ge_retry - bern_retry` is -0.166.
#
# REGISTERED, and it is a shape prediction rather than a magnitude one: the DiD has an INTERIOR
# MAXIMUM IN SPAN at five vehicles, is null at three and four where both arms are healthy, and
# decays to null by seven or eight where both are collapsed. A DiD that grows monotonically in span
# refutes it. So does a DiD that survives at n = 5 with `reply_model=marginal`, which pins d at
# 0.640 and therefore puts BOTH retry arms at n_c = 5.86, leaving no state difference to find.
#
# I got here after refuting my own coherence-excess account of the same contrast on its registered
# falsifier, and after wrongly asserting that five vehicles was too far below the cliff for a
# first-moment story to reach. It is not: the retry moves the cliff down to meet it.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
M='"reply_model":"marginal"'
R='"retry_prob":1.0,"retry_backoff":4'
C='"control_mode":"direct","comms_level":3'

echo "### R1 the interior maximum in span (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=3,4,5,6,7,8,10' \
  --arm "bern_off={$C}" \
  --arm "ge_off={$C,$G}" \
  --arm "bern_retry={$C,$R}" \
  --arm "ge_retry={$C,$R,$G}"

echo "### R2 the same on the queue, where n_c is defined"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=3,4,5,6,7,8,10' \
  --arm "bern_off={$C}" \
  --arm "ge_off={$C,$G}" \
  --arm "bern_retry={$C,$R}" \
  --arm "ge_retry={$C,$R,$G}"

# Pinning d puts both retry arms at the same n_c, so the state difference the whole account rests
# on cannot exist. If the DiD survives here, the account is wrong and there is structure left over.
echo "### R3 pin the denominator and the interaction must vanish (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=4,5,6' \
  --arm "bern_off={$C}" \
  --arm "mg_off={$C,$G,$M}" \
  --arm "bern_retry={$C,$R}" \
  --arm "mg_retry={$C,$R,$G,$M}"

echo "### R4 and the same, on the queue"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=4,5,6' \
  --arm "bern_off={$C}" \
  --arm "mg_off={$C,$G,$M}" \
  --arm "bern_retry={$C,$R}" \
  --arm "mg_retry={$C,$R,$G,$M}"
