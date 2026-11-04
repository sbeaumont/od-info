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

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) or
[Podman](https://podman.io/) on your computer. Make sure that it runs before you start.

#### Install

1. Download `odinfo-docker.zip` from the [releases page](../../releases).
2. Unzip it to a folder that you can find again, for example `Documents`. This gives you
   the `odinfo-docker` folder. Windows can put it in a second folder with the same name.
   Use the folder that holds `start.bat`.
3. Open the `odinfo-docker` folder. On Windows, double-click `start.bat`. On Mac,
   double-click `start.command`. On Linux, run `./start.sh` from a terminal. The first
   time, macOS blocks the file: the `README.md` in the folder tells you how to allow it.
4. Edit the two files that the first start makes in `odinfo-docker/instance`:
   `secret.txt` and `users.json`.
5. Start it again. Open http://localhost:5042 in your browser.

ODInfo then fetches new game data every hour by itself.

#### The odinfo-docker folder

You do everything from this folder. The ODInfo program runs in a container, but you never
go into the container.

```
odinfo-docker/
├── start.bat / .command / .sh              starts ODInfo, upgrades it first
├── stop.bat / .command / .sh               stops ODInfo
├── update_data.bat / .command / .sh        fetches game data now
├── update_refdata.bat / .command / .sh     gets the race and unit data for a new round
├── logs.bat / .command / .sh               shows what ODInfo does
├── README.md                               all settings and help
├── .env                                    your settings, made by the first start
└── instance/                               your configuration and database
```

Back up the `instance` folder. It holds all of your data.

#### Upgrade

1. Open the `odinfo-docker` folder.
2. Double-click `stop.bat` (Windows) or `stop.command` (Mac), or run `./stop.sh` (Linux).
3. Double-click `start.bat` (Windows) or `start.command` (Mac), or run `./start.sh`
   (Linux). It downloads the
   newest version of ODInfo before it starts.

When you download a newer `odinfo-docker.zip`, copy its files over your `odinfo-docker`
folder. The zip has no `instance` folder and no `.env` file, so your own files stay.

The `README.md` in the `odinfo-docker` folder tells you about the settings in `.env`: the
port, the place of the `instance` folder, and who can open the interface.

## Running From the Source

### Download files

Download the whole project from here and put it somewhere on your local disk.

## Setup

On Windows, double-click `setup.bat`. On Mac/Linux, run `./setup.sh` from a terminal.

This will install uv (a Python package manager that handles Python and all dependencies for you), and then walk you through the configuration. You don't need to install Python or any packages yourself.

You can run setup again at any time, for example to enter the API key of a new round. Setup shows your current settings as defaults.

NOTE: If you're not used to using a command prompt, what you need to do is go to the folder where you downloaded the files from GitHub, right-click and choose "Open In Terminal". This will put you in a command prompt at the correct location.

### Discord notifications (optional)

You can send the networth tracking overview to Discord. During setup you'll be asked for a Discord webhook URL. To get one, go to a Discord channel where you have settings access, add a webhook, and copy the URL.

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

## Configuration

Your configuration is in two files in the `instance` folder: `secret.txt` and `users.json`.
In the container version, this is the `odinfo-docker/instance` folder.

### secret.txt

| Setting              | What it is                                                                          |
|----------------------|-------------------------------------------------------------------------------------|
| `api_key`            | Required. Your OpenDominion API key. Make it on the Settings page of your dominion. |
| `username`           | Required. Your OpenDominion login name. ODInfo uses it to read the full Town Crier. |
| `password`           | Required. Your OpenDominion password.                                               |
| `secret_key`         | Required. A long random text that protects the web login. `setup` makes one for you. |
| `discord_webhook`    | Optional. Sends the networth overview to a Discord channel.                         |
| `feature_toggles`    | Optional. Experimental pages to show, with commas between them. Example: `economy`. |
| `database_name`      | Optional. Opens a different database, for example one from an old round.            |

You do not set a round number. ODInfo asks OpenDominion which round your API key is for,
and gives the database a name from that: `odinfo-round-{number}-id-{id}.sqlite`.

### A new round

Each round has a new API key and its own database.

1. Make a new API key on the Settings page of your new dominion in OpenDominion.
2. Put the key in `secret.txt`, or on the ODInfo Settings page.
3. Stop ODInfo and start it again. It makes a new database for the new round.

The database of the old round stays in the `instance` folder.

### users.json

These are the logins for the ODInfo web interface. They are not your OpenDominion login.

```json
[
  {
    "id": "1",
    "name": "admin",
    "password": "a password that you choose",
    "active": "true",
    "admin": "true"
  }
]
```

To add a user, add a second block with a different `id`.

### The Settings page

A user with `"admin": "true"` in `users.json` sees the Settings page in the menu. A new
install gives the first user this line. If you installed ODInfo before this version, add
the line to your own user yourself. Put a comma at the end of the line above it.

On the Settings page you can:

- change the API key, the Discord webhook and your OpenDominion login
- reset the database. This deletes all data, and you cannot undo it.

After you change a setting, stop ODInfo and start it again. The hourly data update uses
the new values from its next run.

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

The database is a file in the `instance` folder, with a name like
`odinfo-round-{number}-id-{id}.sqlite`. To start again with no data, delete that file or
move it somewhere else. ODInfo makes a new, empty database the next time it starts.

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
