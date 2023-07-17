def _generate_select_by_dominion(table_name, mapping):
    field_list = ', '.join(mapping.keys())
    return f'SELECT {field_list} FROM {table_name} WHERE dominion = :dominion ORDER BY timestamp DESC'


def _query_ops_table_by_dominion(db, table_name, mapping, dom_code):
    qry = _generate_select_by_dominion(table_name, mapping)
    return db.query(qry, {'dominion': dom_code})


# ------------------------------------------------------------ DominionHistory

DOM_HISTORY_MAPPING = {
    'dominion': None,
    'land': 'status.land',
    'networth': 'status.networth',
    'timestamp': 'status.created_at'
}


def query_dom_history(db, dom_code):
    return _query_ops_table_by_dominion(db, 'DominionHistory', DOM_HISTORY_MAPPING, dom_code)


# ------------------------------------------------------------ Dominion

DOMINION_MAPPING = {
    'code': 'code',
    'name': 'name',
    'realm': 'realm',
    'race': 'race'
}


def query_dominion(db, dom_code):
    return _query_ops_table_by_dominion(db, 'Dominions', DOMINION_MAPPING, dom_code)


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


def query_barracks(db, dom_code):
    return _query_ops_table_by_dominion(db, 'BarracksSpy', BARRACKS_SPY_MAPPING, dom_code)


# ------------------------------------------------------------ LandSpy

LAND_SPY_MAPPING = {
    'dominion':   None,
    'timestamp':  None,
    'total': 'land.totalLand',
    'barren': 'land.totalBarrenLand',
    'constructed': 'land.totalConstructedLand',
    'plain': 'land.explored.amount',
    'plain_constructed': 'land.explored.constructed',
    'mountain': 'land.explored.amount',
    'mountain_constructed': 'land.explored.constructed',
    'swamp': 'land.explored.amount',
    'swamp_constructed': 'land.explored.constructed',
    'cavern': 'land.explored.amount',
    'cavern_constructed': 'land.explored.constructed',
    'forest': 'land.explored.amount',
    'forest_constructed': 'land.explored.constructed',
    'hill': 'land.explored.amount',
    'hill_constructed': 'land.explored.constructed',
    'water': 'land.explored.amount',
    'water_constructed': 'land.explored.constructed',
    'incoming': 'land.incoming|tojson'
}


def query_land(db, dom_code):
    return _query_ops_table_by_dominion(db, 'LandSpy', LAND_SPY_MAPPING, dom_code)


# ------------------------------------------------------------ Town Crier

TC_FIELDS = 'timestamp,event_type,origin,origin_name,target,target_name,amount,text'


def query_town_crier(db):
    return db.query('SELECT * FROM TownCrier ORDER BY timestamp DESC')


