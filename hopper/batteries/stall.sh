# CR-28. IS "DO NOT RE-ASK" AN ARTIFACT OF PRICING A WAIT FLAT?
#
# The project's closest-to-shippable recommendation is that on a channel with long outages the
# operator should not re-ask. `st-backoff-9445984` B3 says it at full tier on success with the
# rescale smear removed: at n = 5 and n = 6 every retry arm loses to no-retry and the damage decays
# smoothly to zero with no knee. Fable's objection is that the model makes that recommendation
# cheap. Waiting is priced FLAT: a vehicle stopped at `q_stall` on the twentieth step of its wait
# is exactly as badly off as on the first. Where waiting is dangerous the wait costs more the
# longer it runs, and a rule that tells a stopped vehicle to keep waiting is spending something
# this model does not charge it for.
#
# `stall_decay` moves control quality from `q_stall` toward `stall_floor` in proportion to how far
# into its own patience window the requester has waited. `stall_decay = 0` is byte-identical to the
# published model, which is what makes the sweep a robustness test of a shipped claim rather than a
# different experiment.
#
# REGISTERED, on Fable's construction, before the run.
#   1. As `stall_decay` rises the optimal backoff moves LEFT, toward re-asking sooner.
#   2. The adaptive rule beats `fixed20` at high decay, where under flat pricing it does not.
#   FALSIFIER for the pair: the arm ordering is unchanged in sign at `stall_decay = 1` and no retry
#   arm gates above no-retry, in which case the recommendation is not an artifact of flat pricing,
#   the caveat is answered rather than conceded, and the exposure sweep IS the evidence for saying
#   so in the manuscript.
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
J='"retry_prob":1.0,"retry_spread":0'

# S1. The backoff ladder at four exposure prices. If prediction 1 is right the minimum of the
# damage walks left across the panels; if the falsifier is right the ladder keeps its shape.
for SD in 0.0 0.33 0.67 1.0; do
E="\"stall_decay\":$SD,\"stall_floor\":0.0"
for M in success served_per_step; do
echo "### S1 backoff ladder at stall_decay=$SD ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=5,6' \
  --arm "noretry={$C,$G,$E}" \
  --arm "rho04={$C,$G,$E,$J,\"retry_backoff\":4}" \
  --arm "rho08={$C,$G,$E,$J,\"retry_backoff\":8}" \
  --arm "rho12={$C,$G,$E,$J,\"retry_backoff\":12}" \
  --arm "rho16={$C,$G,$E,$J,\"retry_backoff\":16}" \
  --arm "rho21={$C,$G,$E,$J,\"retry_backoff\":21}" \
  --arm "adapt={$C,$G,$E,$J,\"retry_backoff\":4,\"retry_mode\":\"double\"}"
done
done

# S2. The exposure sweep read the other way round: each arm against itself across the decay
# ladder, which is the paired contrast that can gate. S1 compares arms within a panel; S2 asks
# whether the decay is doing anything at all to each arm, and its sizes are what tell prediction 1
# apart from a ladder that merely gets noisier.
for M in success blue_loss_frac; do
echo "### S2 each arm against itself across the exposure ladder ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'stall_decay=0.0,0.33,0.67,1.0' \
  --arm "noretry={$C,$G,\"n_blue\":6}" \
  --arm "rho04={$C,$G,\"n_blue\":6,$J,\"retry_backoff\":4}" \
  --arm "rho12={$C,$G,\"n_blue\":6,$J,\"retry_backoff\":12}" \
  --arm "rho21={$C,$G,\"n_blue\":6,$J,\"retry_backoff\":21}" \
  --arm "adapt={$C,$G,\"n_blue\":6,$J,\"retry_backoff\":4,\"retry_mode\":\"double\"}"
done

# S3. The floor matters as much as the rate. `stall_floor = 0` says a maximally exposed wait is
# worth nothing at all, which is the most favourable case for prediction 1 and therefore the one to
# check is not carrying the whole effect on its own.
echo "### S3 the same at a non-zero floor, so the result does not rest on q -> 0 (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6' \
  --arm "noretry={$C,$G,\"stall_decay\":1.0,\"stall_floor\":0.15}" \
  --arm "rho04={$C,$G,\"stall_decay\":1.0,\"stall_floor\":0.15,$J,\"retry_backoff\":4}" \
  --arm "rho12={$C,$G,\"stall_decay\":1.0,\"stall_floor\":0.15,$J,\"retry_backoff\":12}" \
  --arm "rho21={$C,$G,\"stall_decay\":1.0,\"stall_floor\":0.15,$J,\"retry_backoff\":21}" \
  --arm "adapt={$C,$G,\"stall_decay\":1.0,\"stall_floor\":0.15,$J,\"retry_backoff\":4,\"retry_mode\":\"double\"}"
