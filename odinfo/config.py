import json
import sys
import os
from dataclasses import dataclass, field


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

# The port the web interface listens on. Not Flask's own 5000: that one is taken often
# enough to be a nuisance, by macOS AirPlay among others. Every way of starting ODInfo
# uses this same number, so the launchers that don't run Python to work it out
# (odinfo.sh, odinfo.bat, the Dockerfile) repeat it and have to be changed along.

WEB_PORT = 5042

# What the Networth Tracker offers to look at: the periods it can measure a delta over,
# and how many Unchanged rows to list. 0 means every row. The defaults are what the page
# and the Discord report use when nobody says otherwise. Top and Bottom have a fixed
# length that the report service decides, since those are reports rather than a browse.

NW_PERIODS = (12, 24, 36, 48)
NW_DEFAULT_PERIOD = 12
NW_ROW_COUNTS = (10, 25, 50, 0)
NW_UNCHANGED_DEFAULT = 50

# Knowledge of internal directory and file structure

INSTANCE_DIR = './instance'
OUT_DIR = './out'
OPS_DATA_DIR = 'opsdata'
DATA_DIR = 'data'
SECRET_FILE = f'{INSTANCE_DIR}/secret.txt'
USERS_FILE = f'{INSTANCE_DIR}/users.json'

# Game data comes in two copies. The baseline ships with the application and is a plain
# mirror of the game's own data files. The override is what refdata_update.py downloads for
# a user later on, and lives with the rest of their data so a new release can't wipe it.
# Both carry a stamp saying when they were synced, and the youngest one is the one in use.
# That way a release with fresher game data automatically supersedes an older download.

REF_DATA_BASELINE_DIR = resource_path(f'{DATA_DIR}/ref-data')
REF_DATA_OVERRIDE_DIR = executable_path(f'{INSTANCE_DIR}/ref-data')
REF_DATA_ARCHIVE_DIR = executable_path(f'{INSTANCE_DIR}/ref-data-archive')
REF_DATA_STAMP_FILE = '.refdata-version'
# Game numbers that the game doesn't publish in its own data files, so we keep them
# ourselves. Application settings live in this module and in secret.txt, not in there.
GAME_CONSTANTS_FILE = resource_path(f'{DATA_DIR}/game-constants.json')
IGNORED_PERKS_FILE = resource_path(f'{DATA_DIR}/ignored-perks.yml')


def refdata_sync_time(directory: str) -> str:
    """When this copy of the reference data was synced with the game's repository.

    Empty for a copy that was never synced by the updater, which makes it the oldest one
    around: an unstamped copy loses from any stamped one.
    """
    stamp_file = os.path.join(directory, REF_DATA_STAMP_FILE)
    if not os.path.exists(stamp_file):
        return ''
    with open(stamp_file) as f:
        return json.load(f)['synced_at']


def refdata_read_path() -> str:
    """Which of the two copies of the reference data the application reads."""
    if not os.path.exists(REF_DATA_OVERRIDE_DIR):
        return REF_DATA_BASELINE_DIR
    if refdata_sync_time(REF_DATA_OVERRIDE_DIR) < refdata_sync_time(REF_DATA_BASELINE_DIR):
        return REF_DATA_BASELINE_DIR
    return REF_DATA_OVERRIDE_DIR


REF_DATA_DIR = refdata_read_path()

# Knowledge of the URL structure of the OD website

OD_BASE = 'https://www.opendominion.net'
LOGIN_URL = f'{OD_BASE}/auth/login'
SEARCH_PAGE = f'{OD_BASE}/dominion/search'
OP_CENTER_URL = f'{OD_BASE}/dominion/op-center'
TOWN_CRIER_URL = f'{OD_BASE}/dominion/town-crier'
STATUS_URL = f'{OD_BASE}/dominion/status'
SELECT_URL = f'{OD_BASE}/dominion/{{}}/select'
MY_OP_CENTER_URL = f'{OD_BASE}/dominion/advisors/op-center'
BARRACKS_ARCHIVE_URL = f'{OP_CENTER_URL}/{{}}/barracks_spy'

# Knowledge of the OD source repository, where the ref-data game data files come from.

OD_SOURCE_REPO = 'OpenDominion/OpenDominion'
OD_SOURCE_BRANCH = 'develop'
OD_SOURCE_DATA_PATH = 'app/data'
OD_SOURCE_TREE_URL = f'https://api.github.com/repos/{OD_SOURCE_REPO}/git/trees/{{ref}}?recursive=1'
OD_SOURCE_RAW_URL = f'https://raw.githubusercontent.com/{OD_SOURCE_REPO}/{{ref}}/{{path}}'

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


# Injectable configuration class


@dataclass
class Config:
    """Runtime configuration for od-info application.

    This class holds all user-specific configuration that can vary between
    environments (production, testing, etc.). Infrastructure constants like
    URLs and paths remain as module-level constants.
    """
    username: str
    password: str
    current_player_id: int
    database_name: str
    local_time_shift: int = 0
    discord_webhook: str | None = None
    feature_toggles: list[str] = field(default_factory=list)
    secret_key: str = ''

    @classmethod
    def from_secrets_file(cls) -> 'Config':
        """Load configuration from secrets.txt file."""
        secrets = load_secrets()

        toggles = []
        if 'feature_toggles' in secrets:
            toggles = [t.strip() for t in secrets['feature_toggles'].split(',')]

        return cls(
            username=secrets['username'],
            password=secrets['password'],
            current_player_id=int(secrets['current_player_id']),
            database_name=secrets['database_name'],
            local_time_shift=int(secrets.get('LOCAL_TIME_SHIFT', '0')),
            discord_webhook=secrets.get('discord_webhook'),
            feature_toggles=toggles,
            secret_key=secrets.get('secret_key', ''),
        )


# Default configuration instance, loaded at import time
_default_config = Config.from_secrets_file()


def get_config() -> Config:
    """Get the default configuration instance."""
    return _default_config


