# CR-23 (v2). TWO FLOORS, AND ONLY ONE OF THEM MOVES WITH THE TEAM.
#
# v1 was cancelled unrun on Fable's catch: `retry_backoff` DEFAULTS to a rescaled draw, not a fixed
# hold, so rho=20 actually delivers a hold uniform on [10,30] and rho=12 delivers [6,18]. The arms
# overlap almost completely and any knee is smeared into a slide BEFORE the physics is consulted.
# Every arm here sets `retry_spread=0`, which is the deterministic hold, verified by value.
#
# The retry lever has two floors and the manuscript has been quoting the wrong one as a rule.
#
#   (a) BAND-CLOSING. The CR-17 fold band has width c mu pi (tau - rho)(1 - a_h)/d, so it shuts at
#       rho >= tau - 1/(c mu pi) = 15.33. No n in it. A property of the lever.
#   (b) JAM. A retry shortens the failure cycle from P+tau+1 to P+rho+1 and drags the collapse span
#       down to n_c = c mu (P + rho + 1)/d, so a team of n is jammed by its own retry when
#                          rho < rho*(n, d) = n d / (c mu) - (P + 1).
#       Both n and d in it. A property of the team on its channel.
#
# At P=20, c=1, mu=0.15 the two make incompatible predictions in every cell:
#
#     n     rho* at d=0.780 (GE-120)     rho* at d=0.640 (Bernoulli)
#     4          -0.2  never jammed           -3.9  never jammed
#     5           5.0                          0.3  never jammed
#     6          10.2                          4.6
#     8          20.6                         13.1
#
# REGISTERED.
#   1. The damage KNEES rather than sliding. At n=5 on GE-120 it is large for rho <= 4 and gone by
#      rho = 8.
#   2. The knee WALKS RIGHT WITH SPAN: absent at n=4, near 5 at n=5, near 10 at n=6, near 21 at 8.
#   3. The knee SHIFTS WITH THE CHANNEL: the Bernoulli ladder sits one span later throughout.
# FALSIFIER: (i) the knee sits at the same rho for n = 5, 6 and 8; (ii) the decline is gradual, with
# the damage at rho=8 still more than half the damage at rho=2 at n=5; (iii) the n=4 BERNOULLI cell
# is gated at any rho. The n=4 GE cell is NOT a refuter: rho* = -0.2 there is inside the noise of
# the d estimate, so a small effect proves nothing either way.
#
# AND ONE DISCRIMINATOR BETWEEN TWO READINGS OF d, registered on Fable's construction, binary and
# immune to the jitter confound that killed v1. If d is the STATIONARY round-trip delivery, n=8 on
# GE-120 clears at rho = 20.6, just under the cap of tau = 22, so the n=8 damage must die by
# rho = 21. If instead the relevant d is CONDITIONAL on the forward path having got through, it is
# larger, rho* exceeds the cap, and n=8 on GE-120 CANNOT clear at any settable rho while Bernoulli
# still clears at 13.1. One cell decides it: does GE at n=8 recover by rho=21 or not at all?
. hopper/batteries/_common.sh
G='"channel":"gilbert_elliot","channel_clock":"step","ge_burst_len":120'
C='"control_mode":"direct","comms_level":3'
J='"retry_prob":1.0,"retry_spread":0'
GE_ARMS=()
BE_ARMS=()
for R in 2 4 6 8 10 12 14 16 18 21; do
  GE_ARMS+=(--arm "ge$R={$C,$G,$J,\"retry_backoff\":$R}")
  BE_ARMS+=(--arm "be$R={$C,$J,\"retry_backoff\":$R}")
done

echo "### B1 the rho ladder on the coherent channel, where rho* walks 0/5/10/21 (goodput)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=4,5,6,8' \
  --arm "ge_noretry={$C,$G}" "${GE_ARMS[@]}"

echo "### B2 the Bernoulli ladder, one span later by the same formula (goodput)"
$PY tools/ar_eval.py $S --metric operator_goodput $B --sweep 'n_blue=4,5,6,8' \
  --arm "be_noretry={$C}" "${BE_ARMS[@]}"

echo "### B3 the same on mission success, at the two spans that carry the knee"
$PY tools/ar_eval.py $S --metric success $B --sweep 'n_blue=5,6' \
  --arm "ge_noretry={$C,$G}" "${GE_ARMS[@]}"
