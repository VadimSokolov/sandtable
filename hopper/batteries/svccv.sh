# CR-51 and CR-53 v2. THE OPERATOR IS A METRONOME, AND WHAT IT COSTS NOT TO BE.
#
# service_cv is a parameter of the console: zero is the published metronome and every closed form in
# this paper was derived against it; above zero the service time is a gamma with the SAME MEAN so
# anything that moves is variability and not speed. The draw is skipped at zero, so the published
# path is bit-identical, which tests/test_c2.py pins.
#
# v2 EXISTS BECAUSE v1 (job 9448848, cancelled unread past its second section) MEASURED THE WRONG
# CONSOLE. Its `admit` arms delivered 0.1908 served per step at cv = 0.5 against 0.1505 at cv = 0,
# which reads as "erratic operators do better" and is not real: `c2.py` drew the service time and
# then tested the deadline against the DRAW, so the console knew before committing exactly how long
# each decision would take and accepted precisely the quick ones. That is a triage capability, not a
# deadline field, and this paper's argument is a requirements ladder. `admit_foresight` now selects
# between the two consoles and defaults to the honest one. See instrument defect 7.
#
# v1 also carried `ajit` arms that were bit-identical to their `admit` controls. `retry_spread`
# jitters the hold a REBUFFED vehicle waits and `retry_prob` is zero by default, so there is nothing
# to jitter whatever the queue policy is. An earlier pass diagnosed this as "blind rebuffs nobody"
# and moved the arms onto `admit`, which was the wrong precondition and left them inert. They are
# dropped here rather than repaired, because the jitter question is CR-44's and already answered.
#
# REGISTERED (CR-53 v2), with nothing from v1 past its C1 section read:
#   P1. on a blind console, variability is a LOSS below the collapse span and IRRELEVANT above it.
#       v1's C1 section is the evidence and its letter is the reverse of what CR-53 v1 registered,
#       so this is recorded as a prediction carried over from a refutation, not as a fresh one:
#       cv = 1.0 costs 0.0213 served per step at four assets and 0.0332 at six, both gated down,
#       and is TOST-equivalent to the metronome at 8, 10, 12 and 16.
#   P2 open. On the HONEST admitting console, variability is a loss at every span, because a
#       feasibility test against the mean admits work the draw then fails to finish in time.
#   P3 open. FORESIGHT IS WORTH MORE THAN THE VARIABILITY COSTS. The triage console beats the
#       honest one by more than the honest one loses to the metronome, so an operator who can tell
#       a hard request from an easy one is worth MORE than an operator who is merely consistent.
#   P4 open. The price of foresight rises with span, because triage only matters when there is
#       something to triage away.
#   P5 open. Under the derived backlog bound the foresight gap SHRINKS, because a console holding
#       two requests has almost nothing to choose between.
#
# FALSIFIER for P3, which is the one worth having: if the foresight gap is smaller than the
# variability loss at a majority of spans, then triage is the lesser capability and the paper says
# so instead.
. hopper/batteries/_common.sh
D='"control_mode":"direct","queue_model":"buffer","comms_level":0'
FS='"admit_foresight":true'

for M in served_per_step success; do
echo "### C1 service variability against span, blind console ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12,16' \
  --arm "cv00={$D}" --arm "cv25={$D,\"service_cv\":0.25}" \
  --arm "cv50={$D,\"service_cv\":0.5}" --arm "cv100={$D,\"service_cv\":1.0}"
echo "### C2 the honest admitting console against the triage one ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12,16' \
  --arm "adm_cv00={$D,\"queue_policy\":\"admit\"}" \
  --arm "adm_cv50={$D,\"queue_policy\":\"admit\",\"service_cv\":0.5}" \
  --arm "fore_cv50={$D,\"queue_policy\":\"admit\",\"service_cv\":0.5,$FS}" \
  --arm "adm_cv100={$D,\"queue_policy\":\"admit\",\"service_cv\":1.0}" \
  --arm "fore_cv100={$D,\"queue_policy\":\"admit\",\"service_cv\":1.0,$FS}"
echo "### C3 does the bound blunt foresight ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=4,6,8,10,12,16' \
  --arm "bound_cv00={$D,\"queue_capacity\":2}" \
  --arm "bound_cv50={$D,\"queue_capacity\":2,\"service_cv\":0.5}" \
  --arm "boundadm_cv50={$D,\"queue_capacity\":2,\"queue_policy\":\"admit\",\"service_cv\":0.5}" \
  --arm "boundfore_cv50={$D,\"queue_capacity\":2,\"queue_policy\":\"admit\",\"service_cv\":0.5,$FS}"
done
