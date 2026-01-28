#!/bin/bash
# Stop the od-info cron job

PLIST_NAME="nl.serge.odinfo"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# Check if loaded
if ! launchctl list | grep -q "$PLIST_NAME"; then
    echo "Service is not running."
    exit 0
fi

# Unload the service
launchctl unload "$PLIST_PATH"

echo "Service stopped."