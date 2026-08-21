#!/bin/bash
# Generic SandTable autoresearch battery runner.
#
#   sbatch --job-name=st-<battery> --export=ALL,BATTERY=<battery> hopper/ar_job.sbatch
#
# One job per battery, each battery a shell script in hopper/batteries/ that calls
# tools/ar_eval.py. The evaluator parallelizes inside the job with --jobs, so a battery
# is one node's worth of cores rather than a SLURM array: the arms of a contrast then
# share a machine and a wall clock, which keeps a run's cells comparable.
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err

set -euo pipefail
source /opt/sw/spack/apps/linux-rhel8-x86_64_v2/gcc-10.3.0/miniconda3-22.11.1-gy/etc/profile.d/conda.sh
conda activate pol

cd /scratch/vsokolov/sandtable-ar
export PYTHONPATH=src
export JOBS="${SLURM_CPUS_PER_TASK:-8}"
export BLOCKS="${BLOCKS:-0-31}"
export REPS="${REPS:-64}"

echo "# host=$(hostname) job=${SLURM_JOB_ID:-none} battery=${BATTERY} jobs=${JOBS} blocks=${BLOCKS} reps=${REPS}"
echo "# code=$(cd /scratch/vsokolov/sandtable-ar && find src tools -name '*.py' -exec md5sum {} + | sort | md5sum | cut -c1-16)"
# Guard the frozen scoring surface before a single measurement, per the integrity rules.
python tools/autoresearch.py guard
date -u +"# start %Y-%m-%dT%H:%M:%SZ"

bash "hopper/batteries/${BATTERY}.sh"

date -u +"# end %Y-%m-%dT%H:%M:%SZ"
echo "### BATTERY ${BATTERY} COMPLETE"
