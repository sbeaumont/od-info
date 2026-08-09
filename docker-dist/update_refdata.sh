#!/bin/sh
# Download the game's own reference data, for when a new round changes races or units.
set -e
cd "$(dirname "$0")"
. ./_compose.sh

$compose run --rm --entrypoint python app refdata_update.py update

echo "Restarting ODInfo so it picks up the new data..."
$compose up -d