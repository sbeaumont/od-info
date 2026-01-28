#!/bin/bash
# Start the od-info cron job via macOS launchctl
# Runs cron.py at minute 45 of every hour

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="nl.serge.odinfo"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# Check if already loaded
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "Service is already running. Use stop_cron.sh to stop it first."
    exit 1
fi

# Create the plist file
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${SCRIPT_DIR}/cron.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Minute</key>
        <integer>45</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/instance/odinfo_cron.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/instance/odinfo_cron.log</string>
</dict>
</plist>
EOF

echo "Created plist at: $PLIST_PATH"

# Load the service
launchctl load "$PLIST_PATH"

echo "Service started. cron.py will run at minute 45 of every hour."
echo "Logs will be written to: ${SCRIPT_DIR}/instance/odinfo_cron.log"