# OD Info
Utility app for the OpenDominion game

This is very much a work in progress. I've tried to make it as easy as possible for a non-programmer to install and run this,
but there are still some quirks that I could improve in the future, like not needing to go into
config files to change things.

If you need some help or have feedback on this readme or the tool look me up in the OpenDominion Discord (AgFx).

### Download files

Download the whole project from here and put it somewhere on your local disk.

## Install uv

The only thing you need to install is **uv**, a Python package manager. It will automatically download the right Python version and all dependencies for you.

### Windows

Open a Command Prompt (type "cmd" in search) or PowerShell, and run:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

NOTE: If you're not used to using a command prompt, what you need to do is go to the folder where you downloaded the files from GitHub, right-click and choose "Open In Terminal". This will put you in a command prompt at the correct location.

### Mac or Linux

Open a Terminal window and run:

    curl -LsSf https://astral.sh/uv/install.sh | sh

That's it! You don't need to install Python or any packages separately — uv handles all of that automatically when you first run the application.

### Run and fail: add instance subdir, secret.txt and users.json file

Do a first run: this will always exit with the message that you need to edit the config files.

On Windows, double-click `odinfo.bat`. On Mac/Linux, run `./odinfo.sh` from a terminal.

These files will have been created for you from templates in a subdirectory called "instance".
 
You will need to edit their contents. For secret.txt:

    username = (your OD username)
    password = (your OD password)
    discord_webhook = (Discord webhook URL, if you have one.)
    current_player_id = (Your player id. Easiest way to find out is go to Search page, hover over your dom name, and note the number at the end of the ".../op-center/<your number>" URL)
    database_name=sqlite:///odinfo-round-<round number>.sqlite
    secret_key=(just some random stuff, only need to put a good key here if you're hosting this server online)
    LOCAL_TIME_SHIFT = (Difference in hours between your local time and OD server time. Positive if your time is ahead of OD server time: e.g. if OD time is 8:21 and your local time is 10:21, you fill in 2 here)

Example:

    username = myODusername
    password = thisisabadpassword123!
    discord_webhook = https://discord.com/api/webhooks/<other stuff>
    current_player_id = 99999
    database_name=sqlite:///my-odinfo-database-for-round-40.sqlite
    secret_key=1234p981(*&^b98g89ubsy89g
    LOCAL_TIME_SHIFT = -2

You can send the networth tracking overview to Discord, but you'll need to set up a
webhook there. On a channel where you can access the settings you can add a webhook
and copy the URL from there.

### One database per round (not for binary version)

Tip: You can change the database_name in secret.txt to a new round number. 
This way you can have a fresh database for every round, and you'll have a copy of the old round's data
if you want to keep it.

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
