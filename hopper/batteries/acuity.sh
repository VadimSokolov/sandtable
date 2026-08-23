# CR-56. THE VALUE OF TRIAGE, PRICED FOR AN OPERATOR WHO IS NOT AN ORACLE.
#
# Registered in doc/autoresearch-conjectures.md. `admit_foresight` gives the console the exact
# service time before it commits, which is an upper bound on what any real triage is worth and has
# to be labelled as one. `admit_acuity` is the same capability as a probability: the console sees
# the realization with probability p and the mean otherwise, same Bayes rule either way, bit
# identical to the old switch at p=1 and to the deadline-field console at p=0.
#
#   B1. delivered service is LINEAR in p. Falsifier: a significant quadratic, or a non-monotone cell.
#   B2. the full-triage gain is mu*cv. Registered new point cv=0.25, predicted 0.0375.
#   B3. the published "bound" rung was never measured: its arms carried queue_policy=admit as well
#       as queue_capacity, and admit_foresight is bit-INERT on a blind console. Bound-alone with and
#       without foresight must be exactly equal here.
#   B4. the counter FORECLOSES most of discernment rather than substituting for it, so the
#       published direction is backwards. Falsifier: bound-plus-triage at or above triage alone.
#   B5. a quantile admission test needs no triage capability, only a number. If it recovers most of
#       the acuity gain, the training recommendation does not survive.
#
# EVERY CELL HERE RUNS AT cv > 0, where the four-bin effort identity stated in JOBS is selectable:
# a triaging console finishes short ones. `busy_total` is carried through every section for exactly
# that reason, and it is the quantity the invariance claim belongs in.
. hopper/batteries/_common.sh
A='"control_mode":"direct","queue_model":"buffer","comms_level":0,"queue_policy":"admit"'
BL='"control_mode":"direct","queue_model":"buffer","comms_level":0'

for M in served_per_step busy_total svc_serviced_mean success; do
echo "### A1 acuity, five points at cv 0.5 ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "p00={$A,\"service_cv\":0.5}" \
  --arm "p25={$A,\"service_cv\":0.5,\"admit_acuity\":0.25}" \
  --arm "p50={$A,\"service_cv\":0.5,\"admit_acuity\":0.5}" \
  --arm "p75={$A,\"service_cv\":0.5,\"admit_acuity\":0.75}" \
  --arm "p100={$A,\"service_cv\":0.5,\"admit_acuity\":1.0}"
done

for M in served_per_step busy_total; do
echo "### A2 the mu*cv scaling, with cv=0.25 as the registered new point ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "cv25={$A,\"service_cv\":0.25}" \
  --arm "cv25f={$A,\"service_cv\":0.25,\"admit_acuity\":1.0}" \
  --arm "cv50={$A,\"service_cv\":0.5}" \
  --arm "cv50f={$A,\"service_cv\":0.5,\"admit_acuity\":1.0}" \
  --arm "cv100={$A,\"service_cv\":1.0}" \
  --arm "cv100f={$A,\"service_cv\":1.0,\"admit_acuity\":1.0}"
done

# A3 is B3 and B4. `bound` is the LADDER's rung: a counter and nothing else, so queue_policy stays
# blind. `boundadm` is what the published sentence was actually measured on. The two foresight
# variants of `bound` must be identical to the last digit; if they are not, the inertness reasoning
# is wrong and the whole rung has to be re-derived. `policy_admit` rides along so the log says which
# console ran, which is the guard defect 8 did not have.
for M in served_per_step busy_total success policy_admit; do
echo "### A3 the counter alone, against the counter plus a deadline test ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "bound={$BL,\"queue_capacity\":2,\"service_cv\":0.5}" \
  --arm "boundf={$BL,\"queue_capacity\":2,\"service_cv\":0.5,\"admit_acuity\":1.0}" \
  --arm "boundadm={$A,\"queue_capacity\":2,\"service_cv\":0.5}" \
  --arm "boundadmf={$A,\"queue_capacity\":2,\"service_cv\":0.5,\"admit_acuity\":1.0}" \
  --arm "adm={$A,\"service_cv\":0.5}" \
  --arm "admf={$A,\"service_cv\":0.5,\"admit_acuity\":1.0}"
done

# A4 is B5, the admissible null. A quantile console budgets the time that covers a q fraction of
# decisions instead of the mean, refuses anything that will not fit, and needs no capability at all:
# q is a number written on the console. If it recovers most of the acuity gain then the finding is
# "set your admission budget correctly", which costs nothing, and no training recommendation
# survives. The sweep runs past 0.9 deliberately, because the mechanism is admission TIGHTNESS
# rather than triage and tightness has no reason to optimise at a middling quantile.
for M in served_per_step busy_total success; do
echo "### A4 the quantile console, which needs no operator skill ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'admit_quantile=0.4,0.6,0.8,0.9,0.95,0.98' \
  --arm "q_cv50={$A,\"service_cv\":0.5}" \
  --arm "q_cv100={$A,\"service_cv\":1.0}"
echo "### A4b the two ends it has to be read against ($M)"
$PY tools/ar_eval.py $S --metric $M $B --sweep 'n_blue=8,12,16' \
  --arm "mean_cv50={$A,\"service_cv\":0.5}" \
  --arm "fore_cv50={$A,\"service_cv\":0.5,\"admit_acuity\":1.0}" \
  --arm "mean_cv100={$A,\"service_cv\":1.0}" \
  --arm "fore_cv100={$A,\"service_cv\":1.0,\"admit_acuity\":1.0}"
done
