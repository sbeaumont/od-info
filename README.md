# OD Info
Utility app for the OpenDominion game

This is very much a work in progress. I've tried to make it as easy as possible for a non-programmer to install and run this,
but there are still some quirks that I could improve in the future, like not needing to go into
config files to change things.

If you need some help or have feedback on this readme or the tool look me up in the OpenDominion Discord (AgFx).

## How to Run It

There are three ways, in the order I recommend them:

1. **In a container** - unzip `odinfo-docker.zip` from the [releases page](../../releases)
   and run `start`. Nothing to install but Podman or Docker, and it keeps its own data up
   to date. This is where this project is heading, so it gets the most attention.
2. **From the source** - download this project and run `setup`, described below. Best if
   you want to read or change the code.
3. **As a downloadable program** - take the executable for your platform from the releases
   page. Still supported, and it needs nothing installed at all.

### In a Container (recommended)

Unzip `odinfo-docker.zip` somewhere of your own and run `start.bat` on Windows, or
`./start.sh` on Mac/Linux. It downloads ODInfo, writes the template configuration files
for you to fill in, and on the second start serves the interface on http://localhost:5042.

Next to the interface it fetches new game data every hour by itself, so unlike the other
two ways there is nothing for you to schedule. The unzipped folder has its own README,
and scripts that mirror the ones described below: `start`, `stop`, `update_data`,
`update_refdata` and `logs`.

Where your data lives, the port, and whether the interface is reachable from the rest of
your network are all settings in the `.env` file in that folder. It also explains how to
drive the container yourself instead of through the scripts, for anyone who would rather
do that.

## Running From the Source

### Download files

Download the whole project from here and put it somewhere on your local disk.

## Setup

On Windows, double-click `setup.bat`. On Mac/Linux, run `./setup.sh` from a terminal.

This will install uv (a Python package manager that handles Python and all dependencies for you), and then walk you through the configuration. You don't need to install Python or any packages yourself.

You can re-run setup at any time — for example to update the round number for a new round. Your existing settings will be offered as defaults.

NOTE: If you're not used to using a command prompt, what you need to do is go to the folder where you downloaded the files from GitHub, right-click and choose "Open In Terminal". This will put you in a command prompt at the correct location.

### Discord notifications (optional)

You can send the networth tracking overview to Discord. During setup you'll be asked for a Discord webhook URL. To get one, go to a Discord channel where you have settings access, add a webhook, and copy the URL.

### One database per round

Each round gets its own database file. When a new round starts, re-run setup and enter the new round number. Your old round data is preserved.

### Run application

On Windows, double-click `odinfo.bat`. On Mac/Linux, run `./odinfo.sh` from a terminal.

For debugging add '--debug' but don't use the debug flag in an unsafe setting!
If you're at home you're safe enough, just don't use it in a Starbucks or a hotel:
you're opening up a local webserver.

### Open the browser

Look in the run log of the console (command prompt) for the local URL you can point in your browser, but generally 
it's http://localhost:5042 or http://127.0.0.1:5042.
First time you will be asked to enter a username and password, this is NOT your OD credentials, but what you filled in
the "users.json" file. If you have your browser remember it you won't have to deal with that anymore.

## Usage

If everything is set up correctly you can press on the "update" links on the 
respective pages to pull in new data.

Every time you press "Update" a new timestamped copy is added to the database,
so it depends on you how much history you collect.

The application does NOT do ANY actions itself, or automate collection, since
this is against the rules. You will have to go to the OpenDominion game, perform
your actions there, and then you can use the update links to pull in the latest data.

## Stopping and resetting
You can stop the server by shutting down the Terminal window or pressing Ctrl+C there.

The database "odinfo.sqlite" is created in the folder "instance ". This is just a file:
You can reset the whole application by just renaming, moving or deleting the database file.
As soon as the application sees that there is no database file it will
generate a new one and initialize it.

## Updating reference information

If you're using this app for a while, the reference (.yml) files with facts about races,
tech and wonders might get out of date. The app can fetch them itself from the game's own
source at https://github.com/OpenDominion/OpenDominion/tree/develop/app/data.

On Windows, double-click `update_refdata.bat`. On Mac/Linux, run `./update_refdata.sh`. It
shows you what changed before it replaces anything.

From a terminal you can also look without changing anything:

```bash
uv run python refdata_update.py
```

That downloads nothing to disk, it only reports. Applying it is then:

```bash
uv run python refdata_update.py update
```

The new files go into `instance/ref-data`, alongside your database, and the app uses them
after a restart. Your previous version is archived in `instance/ref-data-archive`, so you
can undo an update with `uv run python refdata_update.py restore`.

Sometimes the report says a perk needs a look. Perks are the game's building blocks for
spells, wonders, techs and units, and a new one can mean a mechanic this app doesn't know
about yet. Updating anyway is fine, the data is newer either way, but some calculation may
quietly ignore the new mechanic until the app catches up. Let AgFx know on Discord when you
see one.

When a later version of this app ships with newer reference data than what you downloaded,
that newer data automatically takes over.

## Creating a Distribution Package

To create a standalone executable for distribution to non-technical users:

### Automated Build (Recommended)

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   python build.py
   ```

This creates a `publish/` folder with:
- The standalone executable
- Template configuration files in `instance/`
- User documentation

### Manual Build

Alternatively, you can build manually:

```bash
pip install pyinstaller
pyinstaller odinfo.spec
```

Then manually copy the executable from `dist/` and create the external `instance/` folder structure.

### Distribution Notes

- The `instance/` folder MUST be distributed alongside the executable
- Users need to edit `instance/secret.txt` and `instance/users.json` before first run
- The SQLite database will be created automatically in the `instance/` folder
- All user data (config, database) stays external to the executable for easy updates

### The Container Bundle

`odinfo-docker.zip` is what users of the recommended route download. Its contents are in
`docker-dist/`: the compose file and the scripts, no image. The image is built from the
`Dockerfile` here and pushed to GitHub Packages, both by
`.github/workflows/publish-image.yml`, on the same `r*` tags that produce the binaries.
The bundle always pulls the `latest` tag, so a new release reaches people the next time
they run `start`.

The first push creates the package as private. It has to be made public once, under the
repository's Packages settings, or `start` gets a 403 when it tries to pull.
