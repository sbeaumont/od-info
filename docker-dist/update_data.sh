#!/bin/sh
# Fetch game data right now, instead of waiting for the hourly update.
set -e
cd "$(dirname "$0")"
. ./_compose.sh

$compose run --rm --entrypoint python app cron.py