#!/bin/sh
# Lets a Mac user start stop.sh with a double-click in Finder.
exec /bin/sh "$(dirname "$0")/stop.sh"