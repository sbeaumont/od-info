#!/bin/sh
# Stop ODInfo. Your instance/ folder is left alone.
set -e
cd "$(dirname "$0")"
. ./_compose.sh

$compose down

echo "ODInfo stopped. Your configuration and database in instance/ are untouched."