#!/bin/bash
# Submit one battery per SLURM job. Tier is explicit and defaults to the contract's full
# tier (32 blocks x 64 reps); pass BLOCKS/REPS to run a battery at the proxy tier instead.
#   ./hopper/submit.sh full_teleop staffing theory
#   BLOCKS=0-15 REPS=16 ./hopper/submit.sh fanout      # proxy tier
set -e
BLOCKS="${BLOCKS:-0-31}"
REPS="${REPS:-64}"
for B in "$@"; do
  ssh hopper "cd /scratch/vsokolov/sandtable-ar && sbatch --job-name=st-$B \
    --export=ALL,BATTERY=$B,BLOCKS=$BLOCKS,REPS=$REPS hopper/ar_job.sbatch"
done
