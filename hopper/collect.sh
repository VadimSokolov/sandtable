#!/bin/bash
# Pull finished battery logs back and index them. Idempotent: rerun as jobs land.
set -e
mkdir -p runlogs/hopper
rsync -az hopper:/scratch/vsokolov/sandtable-ar/runlogs/ runlogs/hopper/ 2>/dev/null || true
echo "== battery logs =="
shopt -s nullglob
for f in runlogs/hopper/st-*.out; do
  rows=$(grep -c '^AR_ROW' "$f" || true); rows=${rows:-0}
  if grep -q '^### ALL BATTERIES COMPLETE' "$f"; then state=COMPLETE
  elif grep -q '^### BATTERY .* COMPLETE' "$f"; then state=partial
  else state=running; fi
  last=$(grep -E '^(###|@@@|## )' "$f" | tail -1 | cut -c1-58)
  printf "  %-34s %8s %6s rows  %s\n" "$(basename "$f" .out)" "$state" "$rows" "$last"
done
