OUT_DIR = './out'
REF_DATA_DIR = './ref-data'
OPS_DATA_DIR = 'opsdata'

DATABASE = './opsdata/odinfo-round-36.sqlite'
DB_SCHEMA_FILE = './opsdata/schema.sql'

OD_BASE = 'https://www.opendominion.net'

VALHALLA_URL = f'{OD_BASE}/valhalla/round'
LOGIN_URL = f'{OD_BASE}/auth/login'
SEARCH_PAGE = f'{OD_BASE}/dominion/search'
OP_CENTER_URL = f'{OD_BASE}/dominion/op-center'
TOWN_CRIER_URL = f'{OD_BASE}/dominion/town-crier'
STATUS_URL = f'{OD_BASE}/dominion/status'
SELECT_URL = f'{OD_BASE}/dominion/' + '{}/select'

MY_OP_CENTER_URL = f'{OD_BASE}/dominion/advisors/op-center'

DOM_INDEX = f'{OUT_DIR}/dom_index.json'
NETWORTH_FILE = f'{OUT_DIR}/nw.json'
PLAT_PER_ALCHEMY_PER_TICK = 45
PLAT_PER_PEASANT_PER_TICK = 2.7
