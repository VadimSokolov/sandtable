#!/bin/bash
# Generic SandTable autoresearch battery runner.
#
#   sbatch --job-name=st-<battery> --export=ALL,BATTERY=<battery> hopper/ar_job.sbatch
#
# One job per battery, each battery a shell script in hopper/batteries/ that calls
# tools/ar_eval.py. The evaluator parallelizes inside the job with --jobs, so a battery
# is one node's worth of cores rather than a SLURM array: the arms of a contrast then
# share a machine and a wall clock, which keeps a run's cells comparable.
# Sized for BACKFILL, not for peak speed. A 32-core six-hour request waited a day behind
# the account's other work; 16 cores for two hours slots into the gaps the scheduler is
# already leaving. Override with `sbatch --cpus-per-task=... --time=...` when the queue is
# empty and wall clock matters more than start time.
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err

set -euo pipefail
source /opt/sw/spack/apps/linux-rhel8-x86_64_v2/gcc-10.3.0/miniconda3-22.11.1-gy/etc/profile.d/conda.sh
conda activate pol

# Run from a PER-JOB SNAPSHOT, not from the shared tree. `hopper/sync.sh` rsyncs into
# /scratch/vsokolov/sandtable-ar with --delete, and a running job used to read its source from there
# at every python invocation, so editing the working tree while a battery was in flight silently
# changed the code under it between sections. That happened twice on 2026-08-23, to jobs 9448824 and
# 9448688. Both were checked afterwards and reproduced their pre-edit block values bit for bit, so
# nothing was lost, but the `# code=` line in the header was asserting a hash the run had stopped
# keeping, which is exactly the guarantee it exists to give. A snapshot makes the header true again
# and makes a battery safe to leave running while work continues.
SNAP=/scratch/vsokolov/sandtable-ar/runs/${SLURM_JOB_ID:-manual}
mkdir -p "$SNAP"
cp -r /scratch/vsokolov/sandtable-ar/{src,tools,scenarios,hopper,.autoresearch} "$SNAP"/ 2>/dev/null || true
cd "$SNAP"
export PYTHONPATH=src
# Unbuffered, so a long battery reports rows as it produces them rather than at exit.
# Without this a job looks stalled for its whole run and there is no way to tell a slow
# battery from a hung one.
export PYTHONUNBUFFERED=1
export JOBS="${SLURM_CPUS_PER_TASK:-8}"
export BLOCKS="${BLOCKS:-0-31}"
export REPS="${REPS:-64}"

echo "# host=$(hostname) job=${SLURM_JOB_ID:-none} battery=${BATTERY} jobs=${JOBS} blocks=${BLOCKS} reps=${REPS}"
CODEHASH=$(find src tools -name '*.py' -exec md5sum {} + | sort | md5sum | cut -c1-16)
echo "# code=$CODEHASH snapshot=$SNAP"
# Guard the frozen scoring surface before a single measurement, per the integrity rules.
python tools/autoresearch.py guard
date -u +"# start %Y-%m-%dT%H:%M:%SZ"

# BATTERY may name several batteries; they run in sequence inside one allocation, which
# is the polite way to use a partition with few nodes.
for b in ${BATTERY}; do
  echo "### BATTERY $b START"
  bash "hopper/batteries/${b}.sh"
  echo "### BATTERY $b COMPLETE"
done

date -u +"# end %Y-%m-%dT%H:%M:%SZ"
# Re-stamp the hash. On a snapshot it must match, and a mismatch means something wrote into the
# snapshot mid-run, which is a stronger failure than the one this replaced and should stop a read.
ENDHASH=$(find src tools -name '*.py' -exec md5sum {} + | sort | md5sum | cut -c1-16)
if [ "$ENDHASH" != "$CODEHASH" ]; then
  echo "### CODE CHANGED MID-RUN: $CODEHASH -> $ENDHASH. DO NOT READ THIS LOG."
else
  echo "# code unchanged through the run: $ENDHASH"
fi
echo "### ALL BATTERIES COMPLETE"
