#!/bin/bash
#SBATCH --job-name=st-tests
#SBATCH --output=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.out
#SBATCH --error=/scratch/vsokolov/sandtable-ar/runlogs/%x-%j.err
#SBATCH --partition=normal
#SBATCH --constraint=intel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=01:00:00
set -euo pipefail
ROOT=/scratch/vsokolov/sandtable-ar
# Snapshot before running, the same way search.sbatch does. The suite takes about twenty minutes
# and sync.sh rewrites $ROOT in place, so a run reading $ROOT directly is one resync away from
# executing a half-updated tree. That is already a ledgered defect in this project and it should
# not be reintroduced by a new job script.
SNAP=$ROOT/runs/$SLURM_JOB_ID
mkdir -p "$SNAP"
cp -r "$ROOT/src" "$ROOT/tools" "$ROOT/tests" "$ROOT/scenarios" "$ROOT/pyproject.toml" "$SNAP/"
cd "$SNAP"
source /opt/sw/spack/apps/linux-rhel8-x86_64_v2/gcc-10.3.0/miniconda3-22.11.1-gy/etc/profile.d/conda.sh
conda activate pol
export PYTHONPATH="$SNAP/src:$SNAP/tools"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# The doc, report and manuscript trees are deliberately not synced to the cluster, so the checks
# that read them skip here and run on the laptop instead.
python3 -m pytest tests/ -q --durations=15
echo "### TESTS DONE"
