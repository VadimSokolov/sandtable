#!/bin/bash
#SBATCH --job-name=st-search
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err
#SBATCH --partition=normal
#SBATCH --constraint=intel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=06:00:00
set -euo pipefail
ROOT=/scratch/vsokolov/sandtable-ar
SNAP=$ROOT/runs/$SLURM_JOB_ID
mkdir -p "$SNAP"
cp -r "$ROOT/src" "$ROOT/tools" "$ROOT/scenarios" "$SNAP/"
cd "$SNAP"
source /opt/sw/spack/apps/linux-rhel8-x86_64_v2/gcc-10.3.0/miniconda3-22.11.1-gy/etc/profile.d/conda.sh
conda activate pol
export PYTHONPATH="$SNAP/src"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
W="${WORKERS:-32}"
echo "# host=$(hostname) job=$SLURM_JOB_ID snapshot=$SNAP stage=${STAGE:-all} workers=$W"

# Both caches are carried in and out of the snapshot. The truth tables are the answer key; the
# pools are the per-mission draws behind it, and the head-to-head resamples them instead of running
# fresh missions, so losing them would mean paying the whole truth stage again to run the
# comparison a second time.
mkdir -p experiments/results "$ROOT/search/search_truth" "$ROOT/search/search_pools"
cp -r "$ROOT/search/search_truth" experiments/results/ 2>/dev/null || true
cp -r "$ROOT/search/search_pools" experiments/results/ 2>/dev/null || true

save_caches() {
  cp -r experiments/results/search_truth/* "$ROOT/search/search_truth/" 2>/dev/null || true
  cp -r experiments/results/search_pools/* "$ROOT/search/search_pools/" 2>/dev/null || true
}
# Saved on the way out however the job ends. This partition preempts, and a truth stage killed at
# ninety percent with nothing written back is three hours bought and discarded.
trap save_caches EXIT

if [ "${STAGE:-all}" != "run" ]; then
  python -u tools/search_bench.py truth --workers "$W"
  save_caches
fi
if [ "${STAGE:-all}" != "truth" ]; then
  python -u tools/search_bench.py run --out "$ROOT/search/bench-${TAG:-main}.jsonl" \
    --backend "${BACKEND:-pool}" --replicates "${REPS:-300}" --workers "$W"
fi
echo "### SEARCH DONE"
