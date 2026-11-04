#!/bin/sh
# Lets a Mac user start start.sh with a double-click in Finder.
exec /bin/sh "$(dirname "$0")/start.sh"