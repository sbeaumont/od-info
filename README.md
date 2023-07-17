# OD Info
Utility app for the OpenDominion game

## Installation
To make it work you'll need to "pip3 install".

- flask
- requests
- jinja2
- PyYAML
- bs4 (Beautiful Soup)

You'll also need to add a "secrets.py" file in the project root with contents:


    username = (your OD username)
    password = (your OD password)
    discord_webhook = (Discord webhook URL)

You can send the networth tracking overview to Discord, but you'll need to set up a
webhook there. On a channel where you can access the settings you can add a webhook
and copy the URL from there.

Run the app locally with:

    flask --app flask_app run

For debugging add '--debug' but the debug flag in an unsafe setting!!!

Look in the run log for the local URL you can point to.

## Usage
If everything is set up correctly you can press on the "update" links on the 
respective pages to pull in new data.

Every time you press "Update" a new timestamped copy is added to the database,
so it depends on you how much history you collect.

The application does NOT do ANY actions itself, or automate collection, since
this is against the rules. You will have to go to the OpenDominion game, perform
your actions there, and then you can use the update links to pull in the latest data.

