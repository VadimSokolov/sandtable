# CR-56 ADDENDUM. THE SOUND TEST FOR "IS THIS INFORMATION OR IS IT ADMISSION RATE".
#
# Review rejected the discriminator I proposed (foresight serves more while abandoning less) because
# per-step abandonment is a DEMAND meter, not a knowledge meter: any arm that lengthens a refused
# vehicle's hold drops abandonment mechanically while serving as much. The sound instrument is the
# one the busy-weighted bins just added: a console has difficulty information if and only if the mean
# service of the decisions it WORKS is below the population mean by more than a materiality floor.
# Length cannot be selected without seeing length. Registered before the run:
#
#   C1. foresight works BELOW population (pilot 5.53 against 6.667).
#   C2. the coin, which refuses at random, works AT population: it has the lever and no information.
#   C3. the quantile console works AT population too, because it selects on the requester's SLACK
#       and not on the decision's length, which is why it is free software rather than a skill.
#   C4. the honest mean-test console works AT population but SERVES below it (pilot 6.76 worked,
#       5.85 served), because the long draws overrun the deadline and land in the late bin. That is
#       selection by attrition rather than by triage, and it is the one this paper did not name.
#   FALSIFIER for the section: if the coin or the quantile also works below population, the
#   instrument does not separate what it claims to and the decomposition comes out.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'

for M in svc_worked_mean svc_serviced_mean served_per_step busy_total; do
echo "### W1 what each console works, against what it serves ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "mean={$A,\"service_cv\":0.5}" \
  --arm "coin={$A,\"service_cv\":0.5,\"admit_refuse\":0.25}" \
  --arm "quant={$A,\"service_cv\":0.5,\"admit_quantile\":0.9}" \
  --arm "fore={$A,\"service_cv\":0.5,\"admit_acuity\":1.0}" \
  --arm "half={$A,\"service_cv\":0.5,\"admit_acuity\":0.5}" \
  --arm "cap={$A,\"service_cv\":0.5,\"queue_capacity\":2}"
done

# W2 is the demand-side confound review named: served plus abandoned is arm-dependent, so an
# abandonment column cannot be read without the demand it sits on. answer_rate_v is the per-vehicle
# readout that no policy can inflate by changing the asking.
for M in abandoned_per_step requests_per_step answer_rate_v starved_frac; do
echo "### W2 the demand each policy creates, beside the harm it does ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "mean={$A,\"service_cv\":0.5}" \
  --arm "coin={$A,\"service_cv\":0.5,\"admit_refuse\":0.25}" \
  --arm "quant={$A,\"service_cv\":0.5,\"admit_quantile\":0.9}" \
  --arm "fore={$A,\"service_cv\":0.5,\"admit_acuity\":1.0}"
done
