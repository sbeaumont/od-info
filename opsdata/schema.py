from domain.scrapetools import get_soup_page
from domain.towncrier import get_number_of_tc_pages, get_tc_page
from config import OP_CENTER_URL
import json


class Ops(object):
    def __init__(self, contents):
        self.contents = contents

    def q_exists(self, q_str, start_node=None) -> bool:
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            if path in current_node:
                current_node = current_node[path]
                if not current_node:
                    return False
            else:
                return False
        return True

    def q(self, q_str, start_node=None):
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            current_node = current_node[path]
        return current_node


def grab_ops(session, dom_code) -> Ops:
    soup = get_soup_page(session, f'{OP_CENTER_URL}/{dom_code}')
    ops_json = soup.find('textarea', id='ops_json').string
    return Ops(json.loads(ops_json))


def update_ops(session, db, dom_code):
    ops = grab_ops(session, dom_code)
    update_clearsight(ops, db, dom_code)
    update_castle(ops, db, dom_code)


def check_exists(db, table, dom_code, timestamp):
    check_exists_qry = f'SELECT 1 FROM {table} WHERE dominion = ? AND timestamp = ?'
    return len(db.query(check_exists_qry, (dom_code, timestamp))) > 0


def _generate_insert(table_name, mapping):
    field_list = ', '.join(mapping.keys())
    param_list = ', '.join([f':{fld}' for fld in mapping.keys()])
    return f'INSERT INTO {table_name} ({field_list}) VALUES ({param_list})'


def _generate_select_by_dominion(table_name, mapping):
    field_list = ', '.join(mapping.keys())
    return f'SELECT {field_list} FROM {table_name} WHERE dominion = :dominion ORDER BY timestamp DESC'


def _query_ops_table_by_dominion(db, table_name, mapping, dom_code):
    qry = _generate_select_by_dominion(table_name, mapping)
    return db.query(qry, {'dominion': dom_code})


def _update_ops_table(ops, db, table_name, mapping, dom_code, timestamp):
    if check_exists(db, table_name, dom_code, timestamp):
        return
    qry = _generate_insert(table_name, mapping)
    params = {
        'dominion': dom_code,
        'timestamp': timestamp
    }
    for fld, srcpath in mapping.items():
        if srcpath:
            params[fld] = ops.q(srcpath)
    db.execute(qry, params)


# ------------------------------------------------------------ DominionHistory

DOM_HISTORY_MAPPING = {
    'dominion': None,
    'timestamp': 'status.created_at',
    'land': 'status.land',
    'networth': 'status.networth'
}


def query_dom_history(db, dom_code):
    return _query_ops_table_by_dominion(db, 'DominionHistory', DOM_HISTORY_MAPPING, dom_code)


def update_dom_history(ops, db, dom_code, timestamp = None):
    if not timestamp:
        timestamp = ops.q('status.created_at')
    _update_ops_table(ops, db, 'DominionHistory', DOM_HISTORY_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ Dominion

DOMINION_MAPPING = {
    'code': 'code',
    'name': 'name',
    'realm': 'realm',
    'race': 'race'
}

QRY_UPDATE_DOM = '''
    INSERT INTO Dominions (code, name, realm, race)
    VALUES (:code, :name, :realm, :race)
    ON CONFLICT DO NOTHING 
'''

QRY_INSERT_DOM_HISTORY = '''
    INSERT INTO DominionHistory
    VALUES(:code, :land, :networth, :timestamp)
    ON CONFLICT DO NOTHING 
'''


def query_dominion(db, dom_code):
    return _query_ops_table_by_dominion(db, 'Dominions', DOMINION_MAPPING, dom_code)


def update_dominion(ops, db):
    db.execute(QRY_UPDATE_DOM, ops)
    db.execute(QRY_INSERT_DOM_HISTORY, ops)


# ------------------------------------------------------------ ClearSight

CLEARSIGHT_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'land': 'status.land',
    'peasants': 'status.peasants',
    'networth': 'status.networth',
    'prestige': 'status.prestige',
    'resource_platinum': 'status.resource_platinum',
    'resource_food': 'status.resource_food',
    'resource_mana': 'status.resource_mana',
    'resource_ore': 'status.resource_ore',
    'resource_gems': 'status.resource_gems',
    'resource_boats': 'status.resource_boats',
    'military_draftees': 'status.military_draftees',
    'military_unit1': 'status.military_unit1',
    'military_unit2': 'status.military_unit2',
    'military_unit3': 'status.military_unit3',
    'military_unit4': 'status.military_unit4'
}


def query_clearsight(db, dom_code):
    return _query_ops_table_by_dominion(db, 'ClearSight', CLEARSIGHT_MAPPING, dom_code)


def update_clearsight(ops, db, dom_code):
    timestamp = ops.q('status.created_at')
    _update_ops_table(ops, db, 'ClearSight', CLEARSIGHT_MAPPING, dom_code, timestamp)
    update_dom_history(ops, db, dom_code, timestamp)


# ------------------------------------------------------------ CastleSpy

CASTLE_SPY_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'science_points': 'castle.science.points',
    'science_rating': 'castle.science.rating',
    'keep_points':    'castle.keep.points',
    'keep_rating':    'castle.keep.rating',
    'spires_points':  'castle.spires.points',
    'spires_rating':  'castle.spires.rating',
    'forges_points':  'castle.forges.points',
    'forges_rating':  'castle.forges.rating',
    'walls_points':   'castle.walls.points',
    'walls_rating':   'castle.walls.rating',
    'harbor_points':  'castle.harbor.points',
    'harbor_rating':  'castle.harbor.rating'
}


def query_castle(db, dom_code):
    return _query_ops_table_by_dominion(db, 'CastleSpy', CASTLE_SPY_MAPPING, dom_code)


def update_castle(ops, db, dom_code):
    timestamp = ops.q('castle.created_at')
    _update_ops_table(ops, db, 'CastleSpy', CASTLE_SPY_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ Town Crier

TC_FIELDS = 'timestamp,event_type,origin,origin_name,target,target_name,amount,text'
TC_REPLACE_QRY = f'REPLACE INTO TownCrier ({TC_FIELDS}) VALUES (?,?,?,?,?,?,?,?)'


def query_town_crier(db):
    return db.query('SELECT * FROM TownCrier ORDER BY timestamp DESC')


def update_town_crier(session, db):
    for page_nr in range(1, get_number_of_tc_pages(session) + 1):
        events = get_tc_page(session, page_nr)
        for event in events:
            db.execute(TC_REPLACE_QRY, event)
