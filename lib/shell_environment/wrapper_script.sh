#!/bin/bash
# This shell script is a wrapper script that executes a provided script in a new process group.
# It is required to handle termination signals (SIGTERM and SIGINT) gracefully, without producing zombie processes on timeout.
# This is no longer needed
# --- Start of Wrapper Script ---

# Function to handle termination gracefully
function handle_termination {
  # Send SIGTERM to the entire process group
  kill -TERM -$pgid

  # Wait for all processes in the group to finish
  while kill -0 -$pgid 2>/dev/null; do
    wait
  done
}

# Trap SIGTERM and SIGINT to handle termination
trap 'handle_termination' SIGTERM SIGINT

# Check if a script argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <script_to_run>"
  exit 1
fi

script_to_run="$1"

# Create a new process group
set -o monitor # Enable job control
(
  # Execute the provided script
  source "$script_to_run" &
) &> /dev/null &
pgid=$!  # Get the process group ID of the subshell

# Wait for the subshell (and its process group) to finish
wait $pgid

# --- End of Wrapper Script ---