#!/bin/bash
# Block until every SandTable job leaves the queue, then collect. Runs over SSH, so the
# laptop stays idle.
while ssh hopper 'squeue -u $USER -h -o "%j" | grep -q " *st-"'; do sleep 120; done
