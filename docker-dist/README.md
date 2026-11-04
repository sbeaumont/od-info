# ODInfo - Container Version

This runs ODInfo without installing Python or anything else. All you need is either
[Podman](https://podman.io/) or [Docker](https://www.docker.com/) on your machine.

## First Time Setup

1. **Start it**: double-click `start.bat` on Windows or `start.command` on macOS, or run
   `./start.sh` on Linux. The first start downloads ODInfo and creates the configuration
   files for you. On macOS, see [the first double-click](#the-first-double-click-on-macos).
2. **Edit the configuration files** it just made:
   - `instance/secret.txt` - your OpenDominion credentials and settings
   - `instance/users.json` - your login for the web interface
3. **Start it again.** It will tell you it is running on http://localhost:5042

## Upgrading

1. Run `stop`.
2. Run `start`. It downloads the newest version of ODInfo before it starts.

Your `instance/` folder and your `.env` file stay as they are.

If `start` says that it could not download the newest version, it starts the version you
already have. Check your internet connection and run `start` again.

When you download a newer `odinfo-docker.zip`, copy its files over this folder. The
scripts and the ODInfo version go together. The zip has no `instance/` folder and no
`.env` file, so your own files stay.

## The Scripts

Use these and you never have to type a Podman or Docker command yourself. On Windows use
the `.bat` version of each, on macOS the `.command` version, and on Linux the `.sh`
version. A `.command` file opens a Terminal window and runs the `.sh` file of the same
name. Close the window when the script is done.

### The first double-click on macOS

macOS blocks a script that comes from the internet the first time you open it. It shows
a message that it cannot verify the file. Do these steps once for each `.command` file:

1. Click **Done** in the message.
2. Open **System Settings** and go to **Privacy & Security**.
3. Scroll down and click **Open Anyway** next to the name of the file.
4. Confirm with your password.

After that, a double-click is enough.

| Script            | What it does                                                    |
|-------------------|-----------------------------------------------------------------|
| `start`           | Starts ODInfo, upgrading it first if a newer version is out     |
| `stop`            | Stops ODInfo                                                    |
| `update_data`     | Fetches game data right now, without waiting for the next hour   |
| `update_refdata`  | Downloads the game's own race and unit data, for a new round     |
| `logs`            | Shows what ODInfo is doing                                       |

While ODInfo runs, two things are happening: the web interface on http://localhost:5042,
and an updater that fetches new game data at 45 minutes past every hour. You do not have
to schedule anything yourself, so there is no equivalent of `start_cron` here.

## Settings

Everything you can change lives in the `.env` file next to these scripts. The first start
writes it for you, with the settings below in it, commented out and ready to be used.
After changing something, run `stop` and then `start`.

| Setting           | What it does                                                     | Default                          |
|-------------------|------------------------------------------------------------------|----------------------------------|
| `TZ`              | Your timezone, as `Area/City`. Filled in on the first start       | your machine's timezone          |
| `ODINFO_INSTANCE` | Where your configuration and database live, as a full path        | `./instance`, next to the scripts |
| `ODINFO_PORT`     | The port to reach the web interface on                            | `5042`                           |
| `ODINFO_BIND`     | The address it listens on. `127.0.0.1` is this machine only       | `0.0.0.0`, reachable from your network |
| `ODINFO_ENGINE`   | `docker` or `podman`, when you have both and want a particular one | whichever one is running         |

The web interface is reachable from your network by default, since a machine in a cupboard
is no use if only that machine can open it. It asks for the login from `users.json` before
it shows anything. If you would rather keep it to the machine it runs on, put
`ODINFO_BIND=127.0.0.1` in `.env`.

## Your Data

Everything of yours lives in the `instance/` folder next to these scripts:

- `secret.txt` - your personal configuration (credentials, settings)
- `users.json` - web interface login settings
- `*.sqlite` - your game data database(s)

That folder is the one to back up. Deleting it starts you over from scratch. To keep it
somewhere else, say where your backups already look, put a full path in `.env`:

```
ODINFO_INSTANCE=/srv/odinfo/instance
```

## Running It Yourself

The scripts above are a wrapper around a compose file, so if you would rather drive the
container yourself, nothing stops you:

```
docker run -d --name=odinfo \
  -p 5042:5042 \
  -v /where/you/want/it/instance:/app/instance:Z \
  -e TZ="Europe/Amsterdam" \
  --restart always \
  ghcr.io/sbeaumont/od-info:latest
```

That gives you the web interface and nothing else. The bundle also runs a second container
off the same image that fetches new game data every hour; without it, ODInfo only ever
knows what you pull in by hand from the interface. On your own, a line in your crontab
does the same job:

```
45 * * * * docker exec odinfo python cron.py
```

`docker exec` skips the image's entrypoint, so ODInfo's own commands need nothing more
than their name. The working directory in the container is `/app` and Python is on the
path:

```
docker exec odinfo python cron.py                        # fetch game data now
docker exec -it odinfo python refdata_update.py update   # a new round's races and units
```

## Troubleshooting

- If nothing appears at http://localhost:5042, check that you edited the config files.
- Run `logs` to see what ODInfo is doing.
- Your timezone is stored in the `.env` file here, filled in on first start. If your
  timestamps look wrong, check that it says the right thing.
- If starting fails because port 5042 is already in use, put `ODINFO_PORT=5043` in the
  `.env` file and start again.
- The scripts use whichever of Docker or Podman is running on your machine, with your
  own settings. If you have both and want a particular one, put `ODINFO_ENGINE=podman`
  in the `.env` file.
- For help, check the project documentation or the OpenDominion Discord.