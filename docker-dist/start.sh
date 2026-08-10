#!/bin/sh
# Start ODInfo, and keep it running until you stop it.
set -e
cd "$(dirname "$0")"
. ./_compose.sh

# A container has no idea what timezone you are in, so tell it once. The rest of the
# settings go in the same file, commented out, so they are there when you want them.
if [ ! -f .env ]; then
    timezone=$(readlink /etc/localtime | sed 's|.*zoneinfo/||')
    if [ -z "$timezone" ]; then
        echo "Could not work out your timezone."
        echo "Create a file called .env next to this script containing: TZ=Europe/Amsterdam"
        exit 1
    fi
    cat > .env <<EOF
TZ=$timezone

# Where your configuration and database live. Uncomment and give a full path to keep
# them somewhere else, for instance where your backups already look.
#ODINFO_INSTANCE=/srv/odinfo/instance

# How to reach ODInfo. It listens on every interface, so other machines on your network
# can reach it as well; set the address to 127.0.0.1 to keep it to this machine only.
#ODINFO_BIND=0.0.0.0
#ODINFO_PORT=5042

# Docker or Podman, for when you have both and want a particular one.
#ODINFO_ENGINE=docker
EOF
    echo "Timezone set to $timezone. Edit the .env file if that is wrong."
fi

instance=$(env_value ODINFO_INSTANCE)
[ -n "$instance" ] || instance=./instance

port=$(env_value ODINFO_PORT)
[ -n "$port" ] || port=5042

bind=$(env_value ODINFO_BIND)
[ -n "$bind" ] || bind=0.0.0.0

$compose pull 2>/dev/null || echo "Could not reach the registry, using the version already on this machine."

# Make the folder ourselves so it belongs to you, not to the container runtime.
mkdir -p "$instance"

if [ ! -f "$instance/secret.txt" ]; then
    echo "Creating configuration files in $instance ..."
    # Exits non-zero on purpose: the files it writes still need your details, which the
    # message further down puts better than the container runtime would. So its output is
    # held back until it turns out something genuinely went wrong.
    log=$(mktemp)
    $compose run --rm --entrypoint python app -c "import odinfo.config" >"$log" 2>&1 || true

    if [ ! -f "$instance/secret.txt" ]; then
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

if grep -q EDIT_THIS "$instance/secret.txt"; then
    echo ""
    echo "Almost there. Edit these two files, then run start again:"
    echo "  $instance/secret.txt   your OpenDominion login and the round number"
    echo "  $instance/users.json   the login for the web interface"
    exit 0
fi

if ! $compose up -d; then
    echo ""
    echo "ODInfo could not start. If the message above says the address is already in"
    echo "use, something else on this machine is sitting on port $port: put a line like"
    echo "ODINFO_PORT=5043 in the .env file and start again."
    exit 1
fi

echo ""
echo "ODInfo is running: http://localhost:$port"
case "$bind" in
    127.0.0.1|localhost) echo "Only from this machine, since ODINFO_BIND says so." ;;
    *) echo "From another machine, use this machine's own name or address instead of localhost." ;;
esac
echo "The data updates itself at 45 minutes past every hour."