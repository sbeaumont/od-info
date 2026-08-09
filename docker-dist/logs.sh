#!/bin/sh
# Watch what ODInfo is doing. Press Ctrl-C to stop watching; ODInfo keeps running.
set -e
cd "$(dirname "$0")"
. ./_compose.sh

$compose logs -f