# CR-45. THE SAME SOBOL DESIGN ON THE SIMULATOR AND ON THE CLOSED FORM.
#
# The Discussion promises a global sensitivity analysis. Run the usual way it produces a bar chart of
# which knob matters, which is a description. Because the collapse threshold has a closed form, a
# sharper question is available: does the simulator's variance decomposition match the equation's,
# over the identical Saltelli sample?
#
#   P1. Identical rank order and every S1 within 0.10.
#     FALSIFIER. A rank inversion or a gap above 0.10 means eq:nstar is locally accurate rather than
#     the mechanism, which is a weaker claim than the paper makes, and the divergent parameter is
#     named in the text.
#   P2. Total minus first order below 0.10 for every parameter, on both sides.
#     FALSIFIER. A gap present in the simulator and absent in the equation localizes an omitted
#     interaction, reported as a named limitation.
#
# SECOND RUN. The first (9448581) answered both, and then its own error bars said the answer was
# not resolved: the Saltelli first-order estimator returned +-0.59 on an index of 0.495. Two fixes,
# both registered here before this job runs.
#
#   (a) The reference is no longer estimated at the simulator's sample size. The closed form is four
#       lines of arithmetic; matching sample sizes for fairness threw away precision that was free,
#       and at n = 128 it made the reference's patience and decision-interval indices tie to three
#       decimals, which produced an apparent rank inversion that is not in the equation. At
#       n_eq = 65536 they separate by exactly the squared ratio of their ranges, which is what the
#       algebra says.
#   (b) The simulator side runs at n = 512, four times the sample and four times the cost, which
#       halves every confidence interval. The comparison is then made against error bars rather than
#       against a bare tolerance.
#
#   P3 (registered now, from the first run's own diagnostics). The tolerance in P1 must be read
#     against the estimator's confidence interval, and the TOTAL-order comparison is the one that
#     resolves: its intervals were +-0.03 to +-0.12 where the first-order ones were +-0.29 to
#     +-0.59. Prediction: every |ST difference| stays below 0.10 with intervals that do not cover
#     0.10, at n = 512.
#     FALSIFIER. First-order intervals still wider than the tolerance at n = 512 means the design
#     cannot answer P1 at any affordable cost, and P1 is withdrawn in favour of P3.
. hopper/batteries/_common.sh
echo "### G1 Sobol on the collapse threshold, simulator against closed form"
$PY tools/sobol_nstar.py --n 512 --seeds 8 --n-eq 65536 --out runlogs/sobol_nstar.json
