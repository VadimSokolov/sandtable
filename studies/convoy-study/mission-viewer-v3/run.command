#!/bin/zsh
set -e
VIEWER_REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$VIEWER_REPO"
export PYTHONPATH="$VIEWER_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VIEWER_REPO/.venv/bin/python" -B -m sandtable.mission_viewer "$@"
