# Sourced by the other scripts: work out whether to drive Docker or Podman. Nothing is
# configured here beyond the choice between the two, so whichever one you pick uses your
# own settings. Put ODINFO_ENGINE=podman or ODINFO_ENGINE=docker in .env to force it.
compose=""
if [ -f .env ]; then
    compose=$(sed -n 's/^ODINFO_ENGINE=//p' .env)
fi

if [ -n "$compose" ]; then
    compose="$compose compose"
else
    # Whichever one is actually running. Having both installed is common, having both
    # running is not.
    for engine in docker podman; do
        if $engine info >/dev/null 2>&1; then
            compose="$engine compose"
            break
        fi
    done
fi

if [ -z "$compose" ]; then
    # Nothing responded, so fall back to whichever is installed and let it explain itself.
    for engine in docker podman; do
        if command -v $engine >/dev/null 2>&1; then
            compose="$engine compose"
            break
        fi
    done
fi

if [ -z "$compose" ]; then
    echo "Neither Docker nor Podman is installed. Install one of them and try again."
    exit 1
fi