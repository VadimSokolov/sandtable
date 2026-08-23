# Sourced by every battery. JOBS/BLOCKS/REPS come from the sbatch wrapper.
PY=python
S="--scenario scenarios/sc_span_control.json"
B="--blocks ${BLOCKS} --reps ${REPS} --jobs ${JOBS}"
# `D` is the PUBLISHED console, which is `queue_model = "reserve"`: a request is committed to a slot
# at arrival and nothing ever waits anywhere it could be reordered. Eleven batteries use it and are
# right to. It is NOT the console any question about backlog, discipline or capacity is asking about,
# and forgetting that costs a battery: svccv v1 (job 9448848) registered CR-51/CR-53 against the
# buffer console, wrote `$D` for its arms, and measured reserve for two sections before the
# discrepancy against `st-lifo`'s identical configuration gave it away. Use `DB` for anything with a
# queue in it, and never leave the model implicit in a battery whose question is about the queue.
D='"control_mode":"direct","comms_level":0'
DB='"control_mode":"direct","comms_level":0,"queue_model":"buffer"'
