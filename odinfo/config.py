import sys
import os


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


# The correct handling of date/timestamps in combination with the sqlite database is dependent
# on this being set correctly. Only change this when you change underlying DB tech.

DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Knowledge of internal directory and file structure

INSTANCE_DIR = './instance'
OUT_DIR = './out'
REF_DATA_DIR = resource_path('ref-data')
OPS_DATA_DIR = 'opsdata'
SECRET_FILE = f'{INSTANCE_DIR}/secret.txt'
USERS_FILE = f'{INSTANCE_DIR}/users.json'

# Knowledge of the URL structure of the OD website

OD_BASE = 'https://www.opendominion.net'
LOGIN_URL = f'{OD_BASE}/auth/login'
SEARCH_PAGE = f'{OD_BASE}/dominion/search'
OP_CENTER_URL = f'{OD_BASE}/dominion/op-center'
TOWN_CRIER_URL = f'{OD_BASE}/dominion/town-crier'
STATUS_URL = f'{OD_BASE}/dominion/status'
SELECT_URL = f'{OD_BASE}/dominion/' + '{}/select'
MY_OP_CENTER_URL = f'{OD_BASE}/dominion/advisors/op-center'

# Global settings that can't be found anywhere else

PLAT_PER_ALCHEMY_PER_TICK = 45
PLAT_PER_PEASANT_PER_TICK = 2.7
PEASANTS_PER_HOME = 30

# Template of the secrets.txt file that gets saved when it can't be found.

SECRETS_TEMPLATE = """# ODInfo Configuration File
# Edit the values below with your actual information

# Your OpenDominion credentials (REQUIRED)
username = EDIT_THIS
password = EDIT_THIS

# Optional Discord webhook URL for notifications
#discord_webhook = None

# Your player ID - find this by hovering over your dominion name in search (REQUIRED)
current_player_id = EDIT_THIS

# Time adjustment: hours to add/subtract from your time to get OD server time
# If OD shows 10:00 and your clock shows 12:00, use -2
# If OD shows 10:00 and your clock shows 8:00, use 2
LOCAL_TIME_SHIFT = 0

# Optional: feature toggles for experimental features (comma-separated list)
#feature_toggles = economy

# Random secret key for web sessions (REQUIRED)
secret_key = EDIT_THIS

# Database file name - change round number as needed (REQUIRED)
database_name = sqlite:///odinfo-round-45.sqlite
"""

USERS_JSON_TEMPLATE = """[
  {
    "id": "1",
    "name": "admin",
    "password": "CHANGE_THIS_PASSWORD",
    "active": "true"
  }
]
"""


def check_dirs_and_configs():
    problems = []
    instance_dir = executable_path(INSTANCE_DIR)
    if not os.path.exists(instance_dir):
        problems.append(f'Expecting "{instance_dir}" subdirectory: creating one for you now.')
        os.makedirs(instance_dir)

    secrets_filename = executable_path(SECRET_FILE)
    if not os.path.exists(secrets_filename):
        problems.append(f'Expected {SECRET_FILE} with your configuration settings.')
        with open(secrets_filename, 'w') as f:
            f.writelines(SECRETS_TEMPLATE)
        problems.append(f"Created {SECRET_FILE} for you.")

    with open(secrets_filename) as f:
        if f.read() == SECRETS_TEMPLATE:
            problems.append(f"You still need to change {secrets_filename}.")

    users_filename = executable_path(USERS_FILE)
    if not os.path.exists(users_filename):
        problems.append(f'Expected {users_filename} with your login settings.')
        with open(users_filename, 'w') as f:
            f.write(USERS_JSON_TEMPLATE)
        problems.append(f"Created {users_filename} for you.")

    with open(users_filename) as f:
        if f.read() == USERS_JSON_TEMPLATE:
            problems.append(f"You still need to change {users_filename}.")


    return problems


def load_secrets():
    """Load secrets.txt configuration file."""
    problems = check_dirs_and_configs()
    if problems:
        sys.exit('\n'.join(problems))

    secrets_filename = executable_path(SECRET_FILE)
    with open(secrets_filename) as f:
        secrets_dict = dict()
        for line_num, line in enumerate(f.readlines(), 1):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Check for malformed config lines
            if '=' not in line:
                sys.exit(f"ERROR: Invalid configuration line {line_num} in {secrets_filename}: '{line}'\nExpected format: key = value")
            key, value = [part.strip() for part in line.split('=', 1)]
            # Check for template placeholder values
            if value == 'EDIT_THIS':
                sys.exit(f"ERROR: Please edit {secrets_filename} and replace 'EDIT_THIS' with actual values for: {key}")
            secrets_dict[key] = value
        return secrets_dict


# Make configuration in secret.txt available to the rest of the codebase

SECRETS = load_secrets()
username = SECRETS['username']
password = SECRETS['password']
DATABASE_NAME = SECRETS['database_name']
current_player_id = int(SECRETS['current_player_id'])
LOCAL_TIME_SHIFT = int(SECRETS['LOCAL_TIME_SHIFT'])
discord_webhook = SECRETS.get('discord_webhook', None)

# Use this to make features toggleable (typically screens in development)

feature_toggles = []
if 'feature_toggles' in SECRETS:
    feature_toggles = [toggle.strip() for toggle in SECRETS['feature_toggles'].split(',')]
