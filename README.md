# OD Info
Utility app for the OpenDominion game

## Installation

I don't use Windows machines, but on python.org there are probably good installers
to be found for Python3.

### Homebrew and Python3 (Mac or Linux)
To make it work you'll need Python 3 installed. If you have no clue how to do this,
the easiest on Mac is to install the Homebrew package manager (https://brew.sh/#install). 
It tells you to execute this in a Terminal window:

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Next step is installing Python3 (also in the Terminal window):

    brew install python3

### Python3 packages
*Note that there's a whole thing about "virtual environments" that is good practice
if you run or develop different applications. If this is the only Python
application you're ever planning on running because you're not a leet hacker,
don't bother with it, just continue to the next step: it just means the packages
will be part of the main Python3 installation, which is fine for this case.*

In a terminal window you'll need to "pip3 install":

    pip3 install flask requests jinja2 PyYAML bs4

This installs these libraries:

 - flask (webserver)
 - requests (pull stuff from the web)
 - jinja2 (template engine for the web interface)
 - PyYAML (to load configuration files)
 - bs4 (Beautiful Soup, to scrape information from webpages)

### Download files
Download the whole project from here and put it somewhere on your local disk.

### Add secrets.py file
You'll also need to add a text file called "secrets.py" file in the project root with contents:

    username = (your OD username)
    password = (your OD password)
    discord_webhook = (Discord webhook URL)

You can send the networth tracking overview to Discord, but you'll need to set up a
webhook there. On a channel where you can access the settings you can add a webhook
and copy the URL from there.

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
