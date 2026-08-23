#!/bin/bash
# Push the working tree to Hopper. Excludes build products and the report, which never
# run on the cluster. Deliberately NOT --delete on runlogs, so results already collected
# there survive a resync.
set -e
DEST=/scratch/vsokolov/sandtable-ar
ssh hopper "mkdir -p $DEST/runlogs"
rsync -az --delete \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude 'runlogs' --exclude 'report' --exclude 'build' --exclude 'runs' \
  src tools scenarios tests experiments studies hopper .autoresearch pyproject.toml \
  hopper:$DEST/
echo "synced to hopper:$DEST"
