# CR-55 (C5). THE ONE LEVER IN THIS PAPER THAT IS NOT THE CONSOLE, AND ITS TRANSFER THRESHOLD.
#
# Registered in doc/autoresearch-conjectures.md as CR-55 and AMENDED there before this battery ran.
# The amendment matters: the first mechanism was "on-platform following beats a lossy link", and a
# scouting run showed the link is never lost long enough for that to be true. What survives is
# sharper. A dead-reckoned track a steps stale, following a reference at speed v turning at omega
# rad/step, is wrong by about v*omega*a^2/2. An i.i.d. channel at drop rate p has mean outage
# 1/(1-p), which is 2.2 steps at the worst rung, so its error is under a metre. Mission outcome
# responds to column geometry at the scale of hundreds of metres. The channel therefore reaches the
# mission only if outages last about a minute, which no Bernoulli ladder produces and a bursty
# channel produces routinely.
#
#   A1. Bernoulli ladder: behaviour-chain minus link-star in SUCCESS is TOST-equivalent to zero at
#       every rung. Falsifier: any rung where it gates.
#   A2. log-log slope of track_err_mean against ge_burst_len is 2 within [1.5, 2.5].
#   A3. there is an outage length L* between 40 and 120 steps where the gap GATES UP in success.
#       Falsifier: no gate at any L up to 240, which leaves A1+A2 as a scope boundary.
#   A4. matched mean drop rate, different follow outcome: mean rate is not a sufficient statistic
#       for the platform either, which is C1's claim moved off the console.
#   A5. at the burst length A3 finds, the platform lever and the admission lever COMPOSE.
#
# Instrument defect 10 was fixed first: the behaviour arm used to refresh from ground truth every
# step, so it was omniscient rather than on-platform. No arm here ran on that code.
. hopper/batteries/_common.sh
SUP='"control_mode":"supervisory","blue_behavior":"leader_follow","n_blue":8'
LS='"follow_mode":"link","follow_topology":"star"'
BC='"follow_mode":"behavior","follow_topology":"chain"'
LC='"follow_mode":"link","follow_topology":"chain"'
BS='"follow_mode":"behavior","follow_topology":"star"'
GE='"channel":"gilbert_elliot","channel_clock":"step"'

# F1 is A1 and P4 together: the 2x2 of channel against geometry, so an effect that belongs to the
# formation cannot be reported as an effect of the radio.
for M in success station_err_mean track_err_mean track_stale_frac; do
echo "### F1 the ladder, channel x topology ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=0,1,2,3,4,5' \
  --arm "ls={$SUP,$LS}" --arm "bc={$SUP,$BC}" --arm "lc={$SUP,$LC}" --arm "bs={$SUP,$BS}"
done

# F2 is A2 and A3. The behaviour arm is in it as a control that CANNOT move with burst length,
# because its refresh is a range test and no message is involved: if it moves, the arms are coupled
# through something other than the channel and the whole reading is wrong.
for M in track_err_mean station_err_mean follow_lost_frac success; do
echo "### F2 outage length, at C3 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'ge_burst_len=4,20,60,120,240' \
  --arm "ls={$SUP,$LS,$GE,\"comms_level\":3}" \
  --arm "bc={$SUP,$BC,$GE,\"comms_level\":3}"
done

# F3 is A4: same mean, different second moment. `channel_bursty` is carried as a metric so the log
# says which channel each arm actually ran, which is the guard defect 8 did not have.
for M in track_err_mean station_err_mean success channel_bursty; do
echo "### F3 matched mean drop rate, i.i.d. against bursty ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'comms_level=1,3,5' \
  --arm "iid={$SUP,$LS}" \
  --arm "ge60={$SUP,$LS,$GE,\"ge_burst_len\":60}" \
  --arm "ge240={$SUP,$LS,$GE,\"ge_burst_len\":240}"
done

# F4 is the mission's OWN sensitivity to column geometry, measured on the scripted path with no
# behaviour layer at all. This is the second slope the transfer argument composes, and it has to be
# measured on an arm the follow channel cannot touch or the composition is circular.
for M in success blue_loss_frac time_to_objective; do
echo "### F4 what column geometry is worth, scripted path ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'formation_spread=10,40,120,300,600,900' \
  --arm "scripted={\"control_mode\":\"supervisory\",\"comms_level\":0,\"n_blue\":8}"
done

# F5 is A5. Direct control and the buffer console, so the queue binds and the admission lever has
# something to buy; the longest outage, so the platform lever does too.
for M in success served_per_step; do
echo "### F5 does the platform lever compose with the console lever ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12' \
  --arm "blind_ls={$DB,$GE,\"ge_burst_len\":240,\"comms_level\":3,\"blue_behavior\":\"leader_follow\",$LS}" \
  --arm "blind_bc={$DB,$GE,\"ge_burst_len\":240,\"comms_level\":3,\"blue_behavior\":\"leader_follow\",$BC}" \
  --arm "admit_ls={$DB,$GE,\"ge_burst_len\":240,\"comms_level\":3,\"blue_behavior\":\"leader_follow\",$LS,\"queue_policy\":\"admit\"}" \
  --arm "admit_bc={$DB,$GE,\"ge_burst_len\":240,\"comms_level\":3,\"blue_behavior\":\"leader_follow\",$BC,\"queue_policy\":\"admit\"}"
done
