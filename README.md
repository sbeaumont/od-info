# OD Info
Utility app for the OpenDominion game

This is very much a work in progress. I've tried to make it as easy as possible for a non-programmer to install and run this,
but there are still some quirks that I could improve in the future, like not needing to go into
config files to change things.

## Install Python 3

### Windows (direct install)
Go to https://python.org/downloads/ and download the latest release version, install it.

### Mac or Linux (via Homebrew)
To make it work you'll need Python 3 installed. If you have no clue how to do this,
the easiest on Mac is to install the Homebrew package manager (https://brew.sh/#install). 
It tells you to execute this in a Terminal window:

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Next step is installing Python3 (also in the Terminal window):

    brew install python3

### Python3 packages
*Note that there's a whole thing about "virtual environments" that is good practice
if you run or develop different Python applications. If this is the only Python
application you're ever planning on running because you're not a leet hacker,
don't bother with it, just continue to the next step: it just means the packages
will be part of the main Python3 installation, which is fine for this case.*

In a terminal window / command prompt you'll need to "pip3 install":

```bash
    pip3 install bs4 Flask-Login flask jinja2 matplotlib PyYAML requests wtforms
```

This installs these libraries:

- bs4 (Beautiful Soup, to scrape information from webpages)
- Flask-Login (for user login)
- flask (webserver)
- jinja2 (template engine for the web interface)
- matplotlib (for graphs)
- PyYAML (to load configuration files)
- requests (pull stuff from the web)
- wtforms (for forms in the web interface)

### Download files
Download the whole project from here and put it somewhere on your local disk. Easiest is to clone https://github.com/sbeaumont/od-info.git using git.

### Add secret.txt file
(_When you're running the binary app the secret.txt file needs to be next to the executable.
If you run the app the first time and it doesn't see that file it will generate a template for
you and exit._)

You'll also need to add a text file called "secret.txt" file in the project root (or next to the executable 
if you're using that) with contents:

    username = (your OD username, which is an email address)
    password = (your OD password)
    discord_webhook = (Discord webhook URL, if you have one.)
    current_player_id = (Your current round dominion id. Easiest way to find out is go to Search page, hover over your dom name, and note the number at the end of the ".../op-center/<your number>" URL)
    LOCAL_TIME_SHIFT = (Difference in hours between your local time and OD server time. Positive if your time is ahead of OD server time: e.g. if OD time is 8:21 and your local time is 10:21, you fill in 2 here)
    feature_toggles = economy
    secret_key=<random secret key> (this is a random string of characters, used for session management)
    database_name=e.g. odinfo-round-X (name of db without extension or path)


Example:

    username = myemail@mydomain.com
    password = thisisabadpassword123!
    discord_webhook = https://discord.com/api/webhooks/<other stuff>
    current_player_id = 99999
    LOCAL_TIME_SHIFT = -2
    feature_toggles = economy
    secret_key = aApmDI0r3qHCw5AjGdE5rLhHey-q_VeP
    database_name = odinfo-round-round39

You can send the networth tracking overview to Discord, but you'll need to set up a
webhook there. On a channel where you can access the settings you can add a webhook
and copy the URL from there.

### Add users.json file
You will also need to add a file called "users.json" in the project root (or next to the executable if you're using that) with contents:

```json
[
    {
        "id": 1,
        "name": "dummyuser",
        "password": "dummy_password",
        "active": true,
        "authenticated": false
    }
]
```

### One database per round (not for binary version)

You can open the config.py file with a text editor and change the DATABASE = './opsdata/odinfo-round-36.sqlite' line to
a new round number. This way you can have a fresh database for every round.

### Run application
Run the app locally from the Terminal from the root of the project:

    flask --app flask_app run

For debugging add '--debug' but don't use the debug flag in an unsafe setting!
If you're at home you're safe enough, just don't use it in a Starbucks or a hotel:
you're opening up a local webserver.

Look in the run log for the local URL you can point in your browser, but generally it's localhost:5000 or 127.0.0.1:5000.

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

The database "odinfo.sqlite" is created in the folder "opsdata". This is just a file:
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
