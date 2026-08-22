# Review finding: the three-way split of the notification increment was not gateable as built.
# It subtracted the published-physics arm from the teleoperation arm at matched `q_stall` and
# called the difference the stopped-motion channel, but those two arms differ in TWO things: the
# behavior layer is absent under published physics AND `teleop_stop` is off. The subtraction
# therefore crosses two response surfaces and isolates nothing.
#
# The clean design is a 2x2 factorial INSIDE the teleoperation stack, where the only things that
# move are the two factors of interest. `teleop_stop=False` reproduces the pre-CR-2 semantics (a
# vehicle awaiting a decision keeps driving at 0.35 + 0.65*q_stall) with the behavior layer still
# present, which is exactly the counterfactual the decomposition needs.
#
# Registered predictions for admit - refund, from the reviewer, before the run:
#   base (stop=False, q_stall=0.50)  +0.009
#   quality main effect              +0.005
#   stop main effect                 +0.037
#   interaction                      +0.029
# The interaction being the largest single term is the substantive claim: the channel is not
# "quality of waiting" but quality of waiting WHILE STOPPED.
. hopper/batteries/_common.sh
T='"control_mode":"direct","comms_level":0,"blue_behavior":"auto","n_blue":8'

echo "### F1 teleop_stop x q_stall factorial, admit vs refund, inside the teleoperation stack"
$PY tools/ar_eval.py $S --metric success $B --sweep 'q_stall=0.30,0.50' \
  --arm "refund_stop={$T,\"teleop_stop\":true,\"queue_policy\":\"refund\"}" \
  --arm "admit_stop={$T,\"teleop_stop\":true,\"queue_policy\":\"admit\"}" \
  --arm "refund_go={$T,\"teleop_stop\":false,\"queue_policy\":\"refund\"}" \
  --arm "admit_go={$T,\"teleop_stop\":false,\"queue_policy\":\"admit\"}"
