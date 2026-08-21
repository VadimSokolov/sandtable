#!/bin/bash
# Pull finished battery logs back and index them. Idempotent: rerun as jobs land.
set -e
mkdir -p runlogs/hopper
rsync -az hopper:/scratch/vsokolov/sandtable-ar/runlogs/ runlogs/hopper/ 2>/dev/null || true
echo "== battery logs =="
for f in runlogs/hopper/st-*.out; do
  [ -e "$f" ] || continue
  n=$(grep -c '^AR_ROW' "$f" 2>/dev/null || echo 0)
  done_marker=$(grep -c 'BATTERY .* COMPLETE' "$f" 2>/dev/null || echo 0)
  state=$([ "$done_marker" -gt 0 ] && echo COMPLETE || echo running)
  printf "  %-46s %8s  %5s rows\n" "$(basename "$f")" "$state" "$n"
done
