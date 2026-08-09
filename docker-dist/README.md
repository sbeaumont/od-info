# ODInfo - Container Version

This runs ODInfo without installing Python or anything else. All you need is either
[Podman](https://podman.io/) or [Docker](https://www.docker.com/) on your machine.

## First Time Setup

1. **Start it**: double-click `start.bat` on Windows, or run `./start.sh` on macOS and
   Linux. The first start downloads ODInfo and creates the configuration files for you.
2. **Edit the configuration files** it just made:
   - `instance/secret.txt` - your OpenDominion credentials and settings
   - `instance/users.json` - your login for the web interface
3. **Update the round number** in `secret.txt` to match the current OpenDominion round.
4. **Start it again.** It will tell you it is running on http://localhost:5042

## The Scripts

Use these and you never have to type a Podman or Docker command yourself. On Windows use
the `.bat` version of each, on macOS and Linux the `.sh` version.

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

## Upgrading

Run `stop`, then `start`. Starting always checks for a newer version of ODInfo first.
Your `instance/` folder is never touched by an upgrade.

## Your Data

Everything of yours lives in the `instance/` folder next to these scripts:

- `secret.txt` - your personal configuration (credentials, settings)
- `users.json` - web interface login settings
- `*.sqlite` - your game data database(s)

That folder is the one to back up. Deleting it starts you over from scratch.

## Troubleshooting

- If nothing appears at http://localhost:5042, check that you edited the config files.
- Run `logs` to see what ODInfo is doing.
- Your timezone is stored in the `.env` file here, filled in on first start. If your
  timestamps look wrong, check that it says the right thing.
- If starting fails because port 5042 is already in use, add a line like
  `ODINFO_PORT=5043` to the `.env` file and start again.
- The scripts use whichever of Docker or Podman is running on your machine, with your
  own settings. If you have both and want a particular one, put a line like
  `ODINFO_ENGINE=podman` in the `.env` file.
- For help, check the project documentation or the OpenDominion Discord.