# The centerpiece's span sweep varies TWO things at once and the paper reads it as one.
#
# Raising `n_blue` against a FIXED four defenders loads the operator AND improves the force ratio.
# Measured at rung 0 under `blind`, 32 reps a point, mission success against span:
#
#   n        2      3      4      5      6      7      8     10     12     16
#   success  .531   .375   .500   .688   .562   .375   .469   .750   .906   .969
#   goodput  1.000  1.000  .985   .962   .784   .361   .195   .062   .018   .007
#   loss_frac.641   .594   .578   .400   .552   .580   .512   .388   .315   .201
#
# Mission success is 97% while the operator answers 0.7% of requests. Success has a local minimum
# at seven, exactly where the queue collapses, and then climbs monotonically as the operator
# becomes irrelevant. Blue loss fraction falls the whole way, which is the tell: a larger force
# beats four defenders more efficiently, so the sweep is buying combat power along with span.
#
# The paper reports spans one-to-two through one-to-eight, which is the dip and nothing else. Its
# headline that congestion defeats direct control at high span is therefore measured inside a
# window where the confound is favourable to it, and the effect reverses on mission success just
# outside that window.
#
# S1 reproduces the published design. S2 holds the force ratio at the published 6:4 = 1.5 by
# scaling the defenders with the span, so the only thing that changes is how many assets one
# operator holds. Registered: under S2 the climb above eight disappears and what remains is the
# queue dip alone. If the climb survives S2, the confound is not the explanation and the U-shape
# is a real span effect.
. hopper/batteries/_common.sh
C='"control_mode":"direct","comms_level":0'

echo "### S1 the published design: defenders fixed at four (success)"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=3,6,9,12,15' --arm "fixed={$C,\"n_red\":4}"

echo "### S2 force ratio held at the published 1.5 (success)"
$PY tools/ar_eval.py $S --metric success $B \
  --arm "r03={$C,\"n_blue\":3,\"n_red\":2}" \
  --arm "r06={$C,\"n_blue\":6,\"n_red\":4}" \
  --arm "r09={$C,\"n_blue\":9,\"n_red\":6}" \
  --arm "r12={$C,\"n_blue\":12,\"n_red\":8}" \
  --arm "r15={$C,\"n_blue\":15,\"n_red\":10}"

echo "### S3 the same pair on the queue, which should not care about the defenders"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=3,6,9,12,15' --arm "fixed={$C,\"n_red\":4}"
$PY tools/ar_eval.py $S --metric operator_goodput $B \
  --arm "r03={$C,\"n_blue\":3,\"n_red\":2}" \
  --arm "r06={$C,\"n_blue\":6,\"n_red\":4}" \
  --arm "r09={$C,\"n_blue\":9,\"n_red\":6}" \
  --arm "r12={$C,\"n_blue\":12,\"n_red\":8}" \
  --arm "r15={$C,\"n_blue\":15,\"n_red\":10}"

echo "### S4 and per-vehicle efficiency, which is what a program actually buys"
$PY tools/ar_eval.py $S --metric blue_loss_frac $B --sweep 'n_blue=3,6,9,12,15' --arm "fixed={$C,\"n_red\":4}"
$PY tools/ar_eval.py $S --metric blue_loss_frac $B \
  --arm "r03={$C,\"n_blue\":3,\"n_red\":2}" \
  --arm "r06={$C,\"n_blue\":6,\"n_red\":4}" \
  --arm "r09={$C,\"n_blue\":9,\"n_red\":6}" \
  --arm "r12={$C,\"n_blue\":12,\"n_red\":8}" \
  --arm "r15={$C,\"n_blue\":15,\"n_red\":10}"
