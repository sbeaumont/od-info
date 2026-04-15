# OD Info
Utility app for the OpenDominion game

This is very much a work in progress. I've tried to make it as easy as possible for a non-programmer to install and run this,
but there are still some quirks that I could improve in the future, like not needing to go into
config files to change things.

If you need some help or have feedback on this readme or the tool look me up in the OpenDominion Discord (AgFx).

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
it's http://localhost:5000 or http://127.0.0.1:5000.
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

If you're using this app for a while, the reference (.yml) files with facts
about races, tech and wonders might get out of date. You can just download
updated files from the ref-data folder in this project, or go straight to the source 
at https://github.com/OpenDominion/OpenDominion/tree/develop/app/data and
replace them in the ref-data folder.

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
