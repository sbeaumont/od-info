import sys
import os

SECRETS_TEMPLATE = """Remove this line and all the <...> sections to make it work.
username = <your OD username>
password = <your OD password>
discord_webhook = None <An https:// URL with a discord webhook to send stuff to>
current_player_id = <Five number id of your player this round>
LOCAL_TIME_SHIFT = 0 <(Negative) number. If you see the timing of the app being off, this allows you to correct it.>
"""


def resource_path(rel_path: str):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, rel_path)
    else:
        return rel_path


def executable_path(rel_path: str):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), rel_path)
    else:
        return rel_path


def load_secrets():
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


SECRETS = load_secrets()
username = SECRETS['username']
password = SECRETS['password']
current_player_id = int(SECRETS['current_player_id'])
LOCAL_TIME_SHIFT = int(SECRETS['LOCAL_TIME_SHIFT'])
discord_webhook = SECRETS['discord_webhook']

OUT_DIR = './out'
REF_DATA_DIR = './ref-data'
OPS_DATA_DIR = 'opsdata'

if getattr(sys, 'frozen', False):
    DATABASE = executable_path('odinfo-database.sqlite')
else:
    DATABASE = executable_path('./opsdata/odinfo-round-37.sqlite')

DB_SCHEMA_FILE = resource_path('./opsdata/schema.sql')

OD_BASE = 'https://www.opendominion.net'

LOGIN_URL = f'{OD_BASE}/auth/login'
SEARCH_PAGE = f'{OD_BASE}/dominion/search'
OP_CENTER_URL = f'{OD_BASE}/dominion/op-center'
TOWN_CRIER_URL = f'{OD_BASE}/dominion/town-crier'
STATUS_URL = f'{OD_BASE}/dominion/status'
SELECT_URL = f'{OD_BASE}/dominion/' + '{}/select'

MY_OP_CENTER_URL = f'{OD_BASE}/dominion/advisors/op-center'

DOM_INDEX = f'{OUT_DIR}/dom_index.json'
NETWORTH_FILE = f'{OUT_DIR}/nw.json'
DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

PLAT_PER_ALCHEMY_PER_TICK = 45
PLAT_PER_PEASANT_PER_TICK = 2.7
