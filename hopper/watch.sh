#!/bin/bash
# One-line status of the SandTable batteries, ignoring the account's other jobs.
ssh hopper 'squeue -u $USER -h -o "%.10i %.16j %.9T %.10M %.6C %R" | grep " st-" || echo "  (no SandTable jobs in the queue)"'
