#!/bin/sh
# Lets a Mac user start logs.sh with a double-click in Finder.
exec /bin/sh "$(dirname "$0")/logs.sh"