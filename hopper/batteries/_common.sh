# Sourced by every battery. JOBS/BLOCKS/REPS come from the sbatch wrapper.
PY=python
S="--scenario scenarios/sc_span_control.json"
B="--blocks ${BLOCKS} --reps ${REPS} --jobs ${JOBS}"
D='"control_mode":"direct","comms_level":0'
