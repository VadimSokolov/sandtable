#!/bin/bash
#SBATCH --job-name=st-search
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
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
echo "# host=$(hostname) job=$SLURM_JOB_ID snapshot=$SNAP stage=${STAGE:-all}"
mkdir -p "$ROOT/search"
if [ "${STAGE:-all}" != "run" ]; then
  # Truth tables are the answer key and must exist before any search is scored against them.
  mkdir -p experiments/results
  cp -r "$ROOT/search/search_truth" experiments/results/ 2>/dev/null || true
  python -u tools/search_bench.py truth --workers "${WORKERS:-16}"
  mkdir -p "$ROOT/search/search_truth"
  cp -r experiments/results/search_truth/* "$ROOT/search/search_truth/" 2>/dev/null || true
fi
if [ "${STAGE:-all}" != "truth" ]; then
  python -u tools/search_bench.py run --out "$ROOT/search/bench-${TAG:-main}.jsonl" \
    --replicates "${REPS:-24}" --workers "${WORKERS:-16}"
fi
echo "### SEARCH DONE"
