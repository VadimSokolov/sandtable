#!/bin/bash
# Submit one battery per SLURM job.
#
#   ./hopper/submit.sh full_teleop staffing theory          # full tier, the default
#   BLOCKS=0-15 REPS=16 ./hopper/submit.sh fanout decouple  # proxy tier, for searches
#   CPUS=32 TIME=06:00:00 ./hopper/submit.sh staffing       # when the queue is empty
#
# Tier is explicit on every submission and lands in the log header, so a result can never
# be read at the wrong tier by accident. Job size defaults to a backfill-friendly shape.
set -e
BLOCKS="${BLOCKS:-0-31}"
REPS="${REPS:-64}"
CPUS="${CPUS:-16}"
TIME="${TIME:-02:00:00}"
# `normal` is fairshare-starved for this account and a job can sit at Reason=Priority for hours;
# `interactive` has seven nodes and clears immediately. Default there, override for long shapes.
PART="${PART:-interactive}"
for B in "$@"; do
  ssh hopper "cd /scratch/vsokolov/sandtable-ar && sbatch --job-name=st-$B \
    --partition=$PART --cpus-per-task=$CPUS --time=$TIME \
    --export=ALL,BATTERY=$B,BLOCKS=$BLOCKS,REPS=$REPS hopper/ar_job.sbatch"
done
