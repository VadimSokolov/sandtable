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
. hopper/batteries/_common.sh
echo "### G1 Sobol on the collapse threshold, simulator against closed form"
$PY tools/sobol_nstar.py --n 128 --seeds 8 --out runlogs/sobol_nstar.json
