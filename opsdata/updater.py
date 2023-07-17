import json
from datetime import datetime

from app.towncrier import get_number_of_tc_pages, get_tc_page
from opsdata.schema import DOM_HISTORY_MAPPING, CLEARSIGHT_MAPPING, CASTLE_SPY_MAPPING, \
    BARRACKS_SPY_MAPPING, LAND_SPY_MAPPING, TC_FIELDS


# ---------------------------------------------------------------------- Parameterized Queries

def cleanup_timestamp(timestamp: str):
    dt = datetime.fromisoformat(timestamp)
    return dt.isoformat(sep=' ', timespec='seconds')


def _generate_insert(table_name, mapping):
    field_list = ', '.join(mapping.keys())
    param_list = ', '.join([f':{fld}' for fld in mapping.keys()])
    insert_qry = f'''
        INSERT INTO {table_name} ({field_list}) 
        VALUES ({param_list})
        ON CONFLICT DO NOTHING 
    '''
    return insert_qry


def _update_ops_table(ops, db, table_name, mapping, dom_code, timestamp):
    """Note that with a |tojson tag it converts the field to json."""
    qry = _generate_insert(table_name, mapping)
    params = {
        'dominion': dom_code,
        'timestamp': cleanup_timestamp(timestamp)
    }
    for fld, srcpath in mapping.items():
        if srcpath:
            with_conversion = srcpath.split('|')
            if (len(with_conversion) > 1) and ('tojson' in with_conversion[1:]):
                contents = json.dumps(ops.q(with_conversion[0]))
            else:
                contents = ops.q(srcpath)
            params[fld] = contents
    db.execute(qry, params)


# ---------------------------------------------------------------------- Updaters Ops => DB

def update_ops(ops, db, dom_code):
    if ops.has_clearsight:
        update_clearsight(ops, db, dom_code)
    if ops.has_castle:
        update_castle(ops, db, dom_code)
    if ops.has_barracks:
        update_barracks(ops, db, dom_code)


def update_dominion(ops, db):
    qry_update_dom = '''
        INSERT INTO Dominions (code, name, realm, race)
        VALUES (:code, :name, :realm, :race)
        ON CONFLICT DO NOTHING 
    '''

    qry_insert_dom_history = '''
        INSERT INTO DominionHistory (dominion, land, networth, timestamp)
        VALUES(:dominion, :land, :networth, :timestamp)
        ON CONFLICT DO NOTHING 
    '''

    ops['timestamp'] = cleanup_timestamp(ops['timestamp'])

    db.execute(qry_update_dom, ops)
    db.execute(qry_insert_dom_history, ops)


def update_dom_history(ops, db, dom_code, timestamp = None):
    if not timestamp:
        timestamp = ops.q('status.created_at')
    _update_ops_table(ops, db, 'DominionHistory', DOM_HISTORY_MAPPING, dom_code, timestamp)


def update_clearsight(ops, db, dom_code):
    timestamp = ops.q('status.created_at')
    _update_ops_table(ops, db, 'ClearSight', CLEARSIGHT_MAPPING, dom_code, timestamp)
    update_dom_history(ops, db, dom_code, timestamp)


def update_castle(ops, db, dom_code):
    timestamp = ops.q('castle.created_at')
    _update_ops_table(ops, db, 'CastleSpy', CASTLE_SPY_MAPPING, dom_code, timestamp)


def update_barracks(ops, db, dom_code):
    timestamp = ops.q('barracks.created_at')
    _update_ops_table(ops, db, 'BarracksSpy', BARRACKS_SPY_MAPPING, dom_code, timestamp)


def update_land(ops, db, dom_code):
    timestamp = ops.q('land.created_at')
    _update_ops_table(ops, db, 'LandSpy', LAND_SPY_MAPPING, dom_code, timestamp)


def update_town_crier(session, db):
    tc_replace_qry = f'REPLACE INTO TownCrier ({TC_FIELDS}) VALUES (?,?,?,?,?,?,?,?)'

    for page_nr in range(1, get_number_of_tc_pages(session) + 1):
        events = get_tc_page(session, page_nr)
        for event in events:
            db.execute(tc_replace_qry, event)


