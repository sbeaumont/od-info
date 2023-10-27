import sys
import os


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
