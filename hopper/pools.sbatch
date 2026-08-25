#!/bin/bash
# The expensive half of the search benchmark, sized for BACKFILL rather than for peak speed.
#
#   sbatch --array=0-15 hopper/pools.sbatch
#
# Half a million missions as one job waited more than a day behind the account's other work. The
# same work as sixteen twenty-minute shards slots into gaps the scheduler is already leaving. Shards
# write disjoint pool files and read none of each other's, so they are independent, order does not
# matter, and a lost shard is re-runnable alone. Everything downstream (the truth tables, then the
# head-to-head) runs no missions at all and costs seconds.
#SBATCH --job-name=st-pools
#SBATCH --partition=normal
#SBATCH --constraint=intel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%A_%a.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%A_%a.err
set -euo pipefail
ROOT=/scratch/vsokolov/sandtable-ar
SNAP=$ROOT/runs/pools-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}
mkdir -p "$SNAP"
cp -r "$ROOT/src" "$ROOT/tools" "$ROOT/scenarios" "$SNAP/"
cd "$SNAP"
source /opt/sw/spack/apps/linux-rhel8-x86_64_v2/gcc-10.3.0/miniconda3-22.11.1-gy/etc/profile.d/conda.sh
conda activate pol
export PYTHONPATH="$SNAP/src"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
N=${N_SHARDS:-16}
echo "# host=$(hostname) shard=${SLURM_ARRAY_TASK_ID}/$N"

mkdir -p experiments/results/search_pools "$ROOT/search/search_pools"
# Existing pools are carried in so a re-run of a shard skips cells already stored.
cp -r "$ROOT/search/search_pools/." experiments/results/search_pools/ 2>/dev/null || true

# Written back on the way out however the job ends, so a shard killed at ninety percent keeps the
# cells it finished rather than paying for them twice.
save() { cp -r experiments/results/search_pools/. "$ROOT/search/search_pools/" 2>/dev/null || true; }
trap save EXIT

python -u tools/search_bench.py pools --shard "${SLURM_ARRAY_TASK_ID}" --of "$N" --workers 16
echo "### SHARD ${SLURM_ARRAY_TASK_ID} DONE"
