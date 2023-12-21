import sys
import os

# Template of the secrets.txt file that gets saved when it can't be found.

SECRETS_TEMPLATE = """Remove this line and all the <...> sections to make it work.
username = <your OD username>
password = <your OD password>
discord_webhook = None <An https:// URL with a discord webhook to send stuff to>
current_player_id = <Five number id of your player this round>
LOCAL_TIME_SHIFT = 0 <(Negative) number. If you see the timing of the app being off, this allows you to correct it.>
"""

# Utility functions
# The getattr() in these functions checks determines whether we're running as a pyinstaller binary.


def resource_path(rel_path: str):
    """Changes given relative path in case we're a pyinstaller binary version"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, rel_path)
    else:
        return rel_path


def executable_path(rel_path: str):
    """Gives the correct work directory depending on running from the project of as a pyinstaller binary version"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), rel_path)
    else:
        return rel_path


def load_secrets():
    """Load secrets.txt configuration file."""
    secrets_filename = executable_path('secret.txt')
    if not os.path.exists(secrets_filename):
        with open(secrets_filename, 'w') as f:
            f.writelines(SECRETS_TEMPLATE)
        print("You did not have a secrets.txt file yet. Edit it and restart the application.")
        sys.exit("Edit the secret.txt file and restart.")

    with open(secrets_filename) as f:
        secrets_dict = dict()
        for line in f.readlines():
            key, value = [part.strip() for part in line.split('=', 1)]
            secrets_dict[key] = value
        return secrets_dict


# Make configuration in secrets.txt available to the rest of the codebase

SECRETS = load_secrets()
username = SECRETS['username']
password = SECRETS['password']
current_player_id = int(SECRETS['current_player_id'])
LOCAL_TIME_SHIFT = int(SECRETS['LOCAL_TIME_SHIFT'])
discord_webhook = SECRETS.get('discord_webhook', None)

# Use this to make features toggleable (typically screens in development)

feature_toggles = []
if 'feature_toggles' in SECRETS:
    feature_toggles = [toggle.strip() for toggle in SECRETS['feature_toggles'].split(',')]

# Location and name of database file. schema.sql is what initializes a new database.

if getattr(sys, 'frozen', False):
    DATABASE = executable_path('odinfo-database.sqlite')
else:
    DATABASE = executable_path(f"./opsdata/{SECRETS['database_name']}.sqlite")

DB_SCHEMA_FILE = resource_path('./opsdata/schema.sql')

# The correct handling of date/timestamps in combination with the sqlite database is dependent
# on this being set correctly. Only change this when you change underlying DB tech.

DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Knowledge of internal directory structure

OUT_DIR = './out'
REF_DATA_DIR = './ref-data'
OPS_DATA_DIR = 'opsdata'

# Knowledge of the URL structure of the OD website

OD_BASE = 'https://www.opendominion.net'
LOGIN_URL = f'{OD_BASE}/auth/login'
SEARCH_PAGE = f'{OD_BASE}/dominion/search'
OP_CENTER_URL = f'{OD_BASE}/dominion/op-center'
TOWN_CRIER_URL = f'{OD_BASE}/dominion/town-crier'
STATUS_URL = f'{OD_BASE}/dominion/status'
SELECT_URL = f'{OD_BASE}/dominion/' + '{}/select'
MY_OP_CENTER_URL = f'{OD_BASE}/dominion/advisors/op-center'

# Probably deprecated, older versions used files extensively.

DOM_INDEX = f'{OUT_DIR}/dom_index.json'
NETWORTH_FILE = f'{OUT_DIR}/nw.json'

# Global settings that can't be found anywhere else

PLAT_PER_ALCHEMY_PER_TICK = 45
PLAT_PER_PEASANT_PER_TICK = 2.7
