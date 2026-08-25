#!/bin/bash
#SBATCH --job-name=st-pred24
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err
#SBATCH --partition=normal
#SBATCH --constraint=intel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=03:00:00
set -euo pipefail
# CR-78's held-out operating point. Fourteen (design, operating point) cells at n_blue=24, grouped
# so that all three axes read slices off the same missions and the group runs once at the dearest
# axis's replication count. The point predictions were frozen in the registration before this ran.
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

mkdir -p experiments/results "$ROOT/search/search_truth"
cp -r "$ROOT/search/search_truth" experiments/results/ 2>/dev/null || true
save_caches() { cp -r experiments/results/search_truth/* "$ROOT/search/search_truth/" 2>/dev/null || true; }
trap save_caches EXIT

python -u tools/search_bench.py truth --workers "$W" --problems \
  qcap_s24_srv qcap_s24_succ qcap_s24_loss disc_s24_srv disc_s24_succ disc_s24_loss
save_caches
echo "### PREDICT24 DONE"
