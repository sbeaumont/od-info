#!/bin/sh
# Start ODInfo, and keep it running until you stop it.
set -e
cd "$(dirname "$0")"
. ./_compose.sh

# A container has no idea what timezone you are in, so tell it once.
if [ ! -f .env ]; then
    timezone=$(readlink /etc/localtime | sed 's|.*zoneinfo/||')
    if [ -z "$timezone" ]; then
        echo "Could not work out your timezone."
        echo "Create a file called .env next to this script containing: TZ=Europe/Amsterdam"
        exit 1
    fi
    echo "TZ=$timezone" > .env
    echo "Timezone set to $timezone. Edit the .env file if that is wrong."
fi

$compose pull 2>/dev/null || echo "Could not reach the registry, using the version already on this machine."

# Make the folder ourselves so it belongs to you, not to the container runtime.
mkdir -p instance

if [ ! -f instance/secret.txt ]; then
    echo "Creating configuration files..."
    # Exits non-zero on purpose: the files it writes still need your details, which the
    # message further down puts better than the container runtime would. So its output is
    # held back until it turns out something genuinely went wrong.
    log=$(mktemp)
    $compose run --rm --entrypoint python app -c "import odinfo.config" >"$log" 2>&1 || true

    if [ ! -f instance/secret.txt ]; then
        echo ""
        echo "Could not start ODInfo, most likely because it could not be downloaded."
        echo "Check your internet connection. What went wrong:"
        echo ""
        cat "$log"
        rm -f "$log"
        exit 1
    fi
    rm -f "$log"
fi

if grep -q EDIT_THIS instance/secret.txt; then
    echo ""
    echo "Almost there. Edit these two files, then run start again:"
    echo "  instance/secret.txt   your OpenDominion login and the round number"
    echo "  instance/users.json   the login for the web interface"
    exit 0
fi

port=$(sed -n 's/^ODINFO_PORT=//p' .env)
[ -n "$port" ] || port=5042

if ! $compose up -d; then
    echo ""
    echo "ODInfo could not start. If the message above says the address is already in"
    echo "use, something else on this machine is sitting on port $port: put a line like"
    echo "ODINFO_PORT=5043 in the .env file and start again."
    exit 1
fi

echo ""
echo "ODInfo is running: http://localhost:$port"
echo "The data updates itself at 45 minutes past every hour."