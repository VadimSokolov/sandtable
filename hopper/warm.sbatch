#!/bin/bash
#SBATCH --job-name=st-warm
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err
#SBATCH --partition=normal
#SBATCH --constraint=intel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=06:00:00
set -euo pipefail
# CR-79. All fourteen methods, the ten of the shipped sweep plus the four repaired variants, so
# every contrast the scorer needs is paired inside one file. Writes to a NEW file: the manuscript
# regenerates from search/bench-r300.jsonl and that must stay exactly what it was.
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
echo "# host=$(hostname) job=$SLURM_JOB_ID snapshot=$SNAP workers=$W"
# Pools read in place from shared storage and truth tables copied in, exactly as search.sbatch
# does. This job runs no truth stage: the answer key is unchanged and rebuilding it would risk
# producing a different key for the same problems.
export SANDTABLE_POOLS="$ROOT/search/search_pools"
mkdir -p experiments/results "$ROOT/search"
cp -r "$ROOT/search/search_truth" experiments/results/ 2>/dev/null || true
python -u tools/search_bench.py run --out "$ROOT/search/bench-warm.jsonl" \
  --backend pool --replicates "${REPS:-300}" --workers "$W"
echo "### WARM SWEEP DONE"
