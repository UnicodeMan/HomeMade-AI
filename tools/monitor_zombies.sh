#!/bin/bash

while true; do
  # Get the number of zombie processes
  zombie_count=$(ps aux | awk '$8 == "Z" {print $0}' | wc -l)

  # Clear the screen
  clear

  # Print the title
  echo "Zombie Processes: $zombie_count"

  # Print the details of zombie processes
  ps aux | awk '$8 == "Z" {print $0}'

  # Sleep for 5 seconds
  sleep 5
done
