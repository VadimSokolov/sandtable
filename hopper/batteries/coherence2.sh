# CR-19, corrected for the confound Fable found and I confirmed. A burst sweep at fixed uplink
# drop rate does NOT hold the round-trip delivery fixed. The coherent reply is right physics (if
# the uplink got through the channel was good, and a channel with memory is likely still good when
# the reply returns), so `d` rises from 0.655 at a dwell of 4 to 0.790 at 120, measured, matching
# the closed form to three decimals. `d` is the denominator of the collapse span, so `n*` falls
# from 9.88 to 8.17 and a sweep at n_blue = 8 walks the operating point from 0.81 n* to 0.98 n* on
# the FIRST MOMENT while it is also changing the structure. Every effect in the earlier L1 is
# therefore unattributable.
#
# `reply_model=marginal` is the control that severs it: the reply is drawn against the marginal
# rate whatever the lag, so `d = (1-p)^2 = 0.64` at every dwell (verified to 0.001) and the only
# thing the sweep varies is temporal structure. It is a control, not a physical claim.
#
#   mg - bern   isolates the STRUCTURE at fixed round-trip delivery
#   co - mg     isolates the round-trip correlation bonus
#   co - bern   is the old, confounded contrast, kept so the decomposition adds up
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step"'
M='"reply_model":"marginal"'
C='"control_mode":"direct","comms_level":3,"n_blue":8'

for MET in success abandon_queue_frac; do
echo "### N-$MET structure against round-trip bonus, decomposed"
$PY tools/ar_eval.py $S --metric $MET $B --sweep 'ge_burst_len=4,14,28,60,120' \
  --arm "bern={$C}" \
  --arm "co={$C,$G}" \
  --arm "mg={$C,$G,$M}"
done

# Fable's Q3 falsifier. The corrected theory says the knee is set by the FAILED-REQUEST CYCLE
# Lambda = P + tau + 1, which is the same quantity as the numerator of n*. A tau-only reading says
# the knee is flat in P. So sweep P at a fixed dwell of 40 and watch the contrast switch off:
# Lambda runs 27, 35, 43, 59, 83, so theta_v runs 1.17, 0.90, 0.73, 0.53, 0.38 and the contrast
# must DECAY. Span is moved with P to hold the cell at 0.79 n* = 0.185 Lambda, so the operating
# point keeps its position relative to collapse and only the cycle length changes.
echo "### N3 does the knee move with patience? (Lambda-form vs tau-form, success)"
$PY tools/ar_eval.py $S --metric success $B \
  --arm "bern_p04={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":4,\"n_blue\":5}" \
  --arm "mg_p04={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":4,\"n_blue\":5,$G,$M,\"ge_burst_len\":40}" \
  --arm "bern_p12={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":12,\"n_blue\":6}" \
  --arm "mg_p12={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":12,\"n_blue\":6,$G,$M,\"ge_burst_len\":40}" \
  --arm "bern_p20={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":20,\"n_blue\":8}" \
  --arm "mg_p20={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":20,\"n_blue\":8,$G,$M,\"ge_burst_len\":40}" \
  --arm "bern_p36={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":36,\"n_blue\":11}" \
  --arm "mg_p36={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":36,\"n_blue\":11,$G,$M,\"ge_burst_len\":40}" \
  --arm "bern_p60={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":60,\"n_blue\":15}" \
  --arm "mg_p60={\"control_mode\":\"direct\",\"comms_level\":3,\"patience\":60,\"n_blue\":15,$G,$M,\"ge_burst_len\":40}"
