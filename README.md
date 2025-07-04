# OD Info
Utility app for the OpenDominion game

This is very much a work in progress. I've tried to make it as easy as possible for a non-programmer to install and run this,
but there are still some quirks that I could improve in the future, like not needing to go into
config files to change things.

If you need some help or have feedback on this readme or the tool look me up in the OpenDominion Discord (AgFx).

### Download files

Download the whole project from here and put it somewhere on your local disk.

## Install Python 3

### Windows (direct install)

Option 1: Open a Command Prompt (type in search). In that command prompt type "python" and press enter. Windows
opens up the store page if you don't have Python installed and allows you to "Get" it. This will download and install
the Python runtime correctly.

If that doesn't work for you go to https://python.org/downloads/ and download the latest release version, install it.
Note that this is more for users who know a bit of programming and know how to set the PATH variable and such. 

NOTE: If you're not used to using a command prompt, double clicking on the Python icon will not work.
What you need to do is go to the folder where you downloaded the files from GitHub, right-click and
choose "Open In Terminal". This will put you in a command prompt at the correct location.

### Mac or Linux (via Homebrew)

To make it work you'll need Python 3 installed. If you have no clue how to do this,
the easiest on Mac is to install the Homebrew package manager (https://brew.sh/#install). 
It tells you to execute this in a Terminal window:

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Next step is installing Python3 (also in the Terminal window):

    brew install python3

## (Mac and Windows) Install Python3 packages

*Note that there's a whole thing about "virtual environments" that is good practice
if you run or develop different Python applications. If this is the only Python
application you're ever planning on running because you're not a leet hacker,
don't bother with it, just continue to the next step: it just means the packages
will be part of the main Python3 installation, which is fine for this case.*

In a terminal window / command prompt you'll need to "pip3 install":

    pip3 install flask requests jinja2 PyYAML bs4 pillow matplotlib flask_login flask_sqlalchemy wtforms

If "pip3" does not work, try using "pip" without the 3.

This installs these libraries:

 - flask (webserver)
 - flask-sqlalchemy (database stuff)
 - flask-login (login stuff)
 - wtforms (better forms, now only used for login)
 - requests (pull stuff from the web)
 - jinja2 (template engine for the web interface)
 - PyYAML (to load configuration files)
 - bs4 (Beautiful Soup, to scrape information from webpages)
 - Pillow and matplotlib (for graphs)

### Run and fail: add instance subdir, secret.txt and users.json file

Do a first run: this will always exit with the message that you need to edit the config files. In a terminal in the root directory of the tool, run:

```bash
    python -m flask --app odinfoweb.flask_app run
```

These files will have been created for you from templates in a subdirectory called "instance".
 
You will need to edit their contents. For secret.txt:

    username = (your OD username)
    password = (your OD password)
    discord_webhook = (Discord webhook URL, if you have one.)
    current_player_id = (Your player id. Easiest way to find out is go to Search page, hover over your dom name, and note the number at the end of the ".../op-center/<your number>" URL)
    database_name=sqlite:///odinfo-round-<round number>.sqlite
    secret_key=(just some random stuff)
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

On Windows: easiest is to double-click the "odinfo.bat" file. 

Run the app locally from the Terminal from the root of the project (right click on root folder and "Open In Terminal"):

    flask --app odinfoweb.flask_app run

If that does not work you can try:

    python -m flask --app odinfoweb.flask_app run

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

## Packaging the app to your own architecture

If you also install PyInstaller, 

    pip3 install pyinstaller

you can use

    pyinstaller odinfo.spec

to build an executable that will run on your architecture.
