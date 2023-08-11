"""
Basic CRUD access to tables.
"""

import json
import logging
import re
from datetime import datetime


logger = logging.getLogger('od-info.db')

# ---------------------------------------------------------------------- Data Conversion


def cleanup_timestamp(timestamp: str):
    """Ensures that a timestamp has a YYYY-MM-DD HH:MM:SS format."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", timestamp)
    clean_ts = f"{m.group(1)} {m.group(2)}"
    dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=None).isoformat(sep=' ', timespec='seconds')


def row_s_to_dict(row_s):
    if row_s:
        if isinstance(row_s, list):
            return [dict(zip(row.keys(), row)) for row in row_s]
        else:
            return dict(zip(row_s.keys(), row_s))
    else:
        return dict()

# ---------------------------------------------------------------------- Parameterized Queries


def _generate_select_by_dominion(table_name, mapping):
    field_list = ', '.join(mapping.keys())
    return f'''
        SELECT {field_list} 
        FROM {table_name} 
        WHERE dominion = :dominion 
        ORDER BY timestamp DESC
    '''


def _generate_last_of_dominion(table_name, mapping):
    field_list = ', '.join(mapping.keys())
    return f'''
        SELECT {field_list}, max(timestamp) 
        FROM {table_name} 
        WHERE dominion = :dominion
    '''


def _query_ops_table_by_dominion(db, table_name, mapping, dom_code, latest=False):
    if latest:
        qry = _generate_last_of_dominion(table_name, mapping)
    else:
        qry = _generate_select_by_dominion(table_name, mapping)
    logger.debug("Executing query %s", qry)

    return db.query(qry, {'dominion': dom_code}, one=latest)


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
            with_tags = srcpath.split('|')
            tags = with_tags[1:] if len(with_tags) > 1 else list()
            path_part = with_tags[0]
            if ('optional' in tags) and not ops.q_exists(path_part):
                params[fld] = ''
            else:
                if 'tojson' in tags:
                    contents = json.dumps(ops.q(path_part))
                else:
                    contents = ops.q(path_part)
                params[fld] = contents

    param_str = '|'.join([str(v) for v in params.values()])
    logger.debug("Inserting into %s values %s", table_name, param_str)

    db.execute(qry, params)

# ------------------------------------------------------------ DominionHistory


DOM_HISTORY_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'land': 'status.land',
    'networth': 'status.networth'
}


def query_dom_history(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'DominionHistory', DOM_HISTORY_MAPPING, dom_code, latest)


def update_dom_history(ops, db, dom_code, timestamp=None):
    if not timestamp:
        timestamp = ops.q('status.created_at')
    _update_ops_table(ops, db, 'DominionHistory', DOM_HISTORY_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ Dominion

DOMINION_MAPPING = {
    'code': 'code',
    'name': 'name',
    'realm': 'realm',
    'race': 'race',
    'last_op': None
}


def query_dominion(db, dom_code):
    field_list = ', '.join(DOMINION_MAPPING.keys())
    qry = f'''
        SELECT {field_list} 
        FROM Dominions 
        WHERE code = :code
    '''
    return db.query(qry, {'code': dom_code}, one=True)


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
    'military_unit4': 'status.military_unit4',
    'military_spies': 'status.military_spies|optional',
    'military_assassins': 'status.military_assassins|optional',
    'military_wizards': 'status.military_wizards|optional',
    'military_archmages': 'status.military_archmages|optional'
}


def query_clearsight(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'ClearSight', CLEARSIGHT_MAPPING, dom_code, latest)


def update_clearsight(ops, db, dom_code):
    timestamp = cleanup_timestamp(ops.q('status.created_at'))
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


def query_castle(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'CastleSpy', CASTLE_SPY_MAPPING, dom_code, latest)


def update_castle(ops, db, dom_code):
    timestamp = cleanup_timestamp(ops.q('castle.created_at'))
    _update_ops_table(ops, db, 'CastleSpy', CASTLE_SPY_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ BarracksSpy

BARRACKS_SPY_MAPPING = {
    'dominion':   None,
    'timestamp':  None,
    'draftees':   'barracks.units.home.draftees',
    'home_unit1': 'barracks.units.home.unit1',
    'home_unit2': 'barracks.units.home.unit2',
    'home_unit3': 'barracks.units.home.unit3',
    'home_unit4': 'barracks.units.home.unit4',
    'training':   'barracks.units.training|tojson',
    'return':     'barracks.units.returning|tojson',
}


def query_barracks(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'BarracksSpy', BARRACKS_SPY_MAPPING, dom_code, latest)


def update_barracks(ops, db, dom_code):
    timestamp = cleanup_timestamp(ops.q('barracks.created_at'))
    _update_ops_table(ops, db, 'BarracksSpy', BARRACKS_SPY_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ LandSpy

LAND_SPY_MAPPING = {
    'dominion':   None,
    'timestamp':  None,
    'total': 'land.totalLand',
    'barren': 'land.totalBarrenLand',
    'constructed': 'land.totalConstructedLand',
    'plain': 'land.explored.plain.amount',
    'plain_constructed': 'land.explored.plain.constructed',
    'mountain': 'land.explored.mountain.amount',
    'mountain_constructed': 'land.explored.mountain.constructed',
    'swamp': 'land.explored.swamp.amount',
    'swamp_constructed': 'land.explored.swamp.constructed',
    'cavern': 'land.explored.cavern.amount',
    'cavern_constructed': 'land.explored.cavern.constructed',
    'forest': 'land.explored.forest.amount',
    'forest_constructed': 'land.explored.forest.constructed',
    'hill': 'land.explored.hill.amount',
    'hill_constructed': 'land.explored.hill.constructed',
    'water': 'land.explored.water.amount',
    'water_constructed': 'land.explored.water.constructed',
    'incoming': 'land.incoming|tojson'
}


def query_land(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'LandSpy', LAND_SPY_MAPPING, dom_code, latest)


def update_land(ops, db, dom_code):
    timestamp = cleanup_timestamp(ops.q('land.created_at'))
    _update_ops_table(ops, db, 'LandSpy', LAND_SPY_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ Survey Dominion


SURVEY_DOMINION_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'home': 'survey.constructed.home',
    'alchemy': 'survey.constructed.alchemy',
    'farm': 'survey.constructed.farm',
    'smithy': 'survey.constructed.smithy',
    'masonry': 'survey.constructed.masonry',
    'ore_mine': 'survey.constructed.ore_mine',
    'gryphon_nest': 'survey.constructed.gryphon_nest',
    'tower': 'survey.constructed.tower',
    'wizard_guild': 'survey.constructed.wizard_guild',
    'temple': 'survey.constructed.temple',
    'diamond_mine': 'survey.constructed.diamond_mine',
    'school': 'survey.constructed.school',
    'lumberyard': 'survey.constructed.lumberyard',
    'forest_haven': 'survey.constructed.forest_haven',
    'factory': 'survey.constructed.factory',
    'guard_tower': 'survey.constructed.guard_tower',
    'shrine': 'survey.constructed.shrine',
    'barracks': 'survey.constructed.barracks',
    'dock': 'survey.constructed.dock',
    'constructing': 'survey.constructing|tojson|optional',
    'barren_land': 'survey.barren_land',
    'total_land': 'survey.total_land'
}


def query_survey(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'SurveyDominion', SURVEY_DOMINION_MAPPING, dom_code, latest)


def update_survey(ops, db, dom_code):
    timestamp = cleanup_timestamp(ops.q('survey.created_at'))
    _update_ops_table(ops, db, 'SurveyDominion', SURVEY_DOMINION_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ Vision


VISION_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'techs': 'vision.techs|tojson',
}


def query_vision(db, dom_code, latest=False):
    return _query_ops_table_by_dominion(db, 'Vision', VISION_MAPPING, dom_code, latest)


def update_vision(ops, db, dom_code):
    timestamp = cleanup_timestamp(ops.q('vision.created_at'))
    _update_ops_table(ops, db, 'Vision', VISION_MAPPING, dom_code, timestamp)


# ------------------------------------------------------------ Town Crier

TC_FIELDS = 'timestamp,event_type,origin,origin_name,target,target_name,amount,text'


def query_town_crier(db):
    return db.query('SELECT * FROM TownCrier ORDER BY timestamp DESC')


