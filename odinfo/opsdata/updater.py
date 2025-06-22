"""
Higher order update actions.
"""

import logging

from odinfo.opsdata.ops import grab_search
from odinfo.timeutils import cleanup_timestamp
from odinfo.domain.dataaccesslayer import all_doms, dom_by_id
from odinfo.domain.models import Dominion, DominionHistory, TownCrier
from odinfo.facade.towncrier import get_number_of_tc_pages, get_tc_page
from odinfo.domain.models import (ClearSight, CastleSpy, BarracksSpy,
                                  SurveyDominion, LandSpy, Vision, Revelation)
from sqlalchemy import text

logger = logging.getLogger('od-info.updater')

# ---------------------------------------------------------------------- Updaters Ops => DB


def update_dom_index(session, db):
    doms = {d.code: d for d in all_doms(db)}
    for code, line in grab_search(session).items():
        timestamp = cleanup_timestamp(line['timestamp'])
        if code not in doms:
            dom = Dominion(code=int(line['code']),
                           name=line['name'],
                           realm=int(line['realm']),
                           race=line['race'])
            db.session.add(dom)

        dh = DominionHistory(dominion_id=int(line['code']),
                             timestamp=timestamp,
                             land=int(line['land']),
                             networth=int(line['networth']))
        # dom.history.append(dh)
        db.session.add(dh)
    db.session.commit()


def update_dominion(ops, db):
    session = db.session
    dom = session.scalar(db.select(Dominion).where(ops.dom_id))
    timestamp = ops.timestamp
    if not dom:
        dom = Dominion(code=ops.dom_id, name=ops.name, realm=ops.realm, _race=ops.race)
        session.add(dom)

    dh = DominionHistory(dominion_id=dom.code, timestamp=timestamp, land=ops.land, networth=ops.networth)
    db.session.add(dh)
    # dom.history.append(dh)

    session.commit()


def update_obj(ops, obj, mapping):
    """Note that with a |tojson tag it converts the field to json."""
    for fld, srcpath in mapping.items():
        if srcpath:
            with_tags = srcpath.split('|')
            tags = with_tags[1:] if len(with_tags) > 1 else list()
            path_part = with_tags[0]
            if ('optional' in tags) and not ops.q_exists(path_part):
                setattr(obj, fld, None)
            else:
                # if 'tojson' in tags:
                #     contents = json.loads(ops.q(path_part))
                # else:
                #     contents = ops.q(path_part)
                # setattr(obj, fld, contents)
                setattr(obj, fld, ops.q(path_part))


def update_ops(ops, db, dom_code):
    logger.debug("Updating ops for dominion %s", dom_code)
    dom = dom_by_id(db, dom_code)
    # Ensure the dominion object is tracked by the session so last_op changes get saved
    db.session.add(dom)
    if ops.has_clearsight:
        timestamp = cleanup_timestamp(ops.q('status.created_at'))
        if not db.session.get(ClearSight, [dom_code, timestamp]):
            obj = ClearSight(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, CLEARSIGHT_MAPPING)
            db.session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had ClearSight for {dom_code} at {timestamp}")
    if ops.has_castle:
        timestamp = cleanup_timestamp(ops.q('castle.created_at'))
        if not db.session.get(CastleSpy, [dom_code, timestamp]):
            obj = CastleSpy(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, CASTLE_SPY_MAPPING)
            db.session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Castle Spy for {dom_code} at {timestamp}")
    if ops.has_barracks:
        timestamp = cleanup_timestamp(ops.q('barracks.created_at'))
        if not db.session.get(BarracksSpy, [dom_code, timestamp]):
            obj = BarracksSpy(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, BARRACKS_SPY_MAPPING)
            db.session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Barracks Spy for {dom_code} at {timestamp}")
    if ops.has_survey:
        timestamp = cleanup_timestamp(ops.q('survey.created_at'))
        if not db.session.get(SurveyDominion, [dom_code, timestamp]):
            obj = SurveyDominion(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, SURVEY_DOMINION_MAPPING)
            db.session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had SurveyDominion for {dom_code} at {timestamp}")
    if ops.has_land:
        timestamp = cleanup_timestamp(ops.q('land.created_at'))
        if not db.session.get(LandSpy, [dom_code, timestamp]):
            obj = LandSpy(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, LAND_SPY_MAPPING)
            db.session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had LandSpy for {dom_code} at {timestamp}")
    if ops.has_vision:
        timestamp = cleanup_timestamp(ops.q('vision.created_at'))
        if not db.session.get(Vision, [dom_code, timestamp]):
            obj = Vision(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, VISION_MAPPING)
            db.session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Vision for {dom_code} at {timestamp}")
    if ops.has_revelation:
        update_revelation(db, ops, dom)
    db.session.commit()


def update_town_crier(session, db):
    logger.debug("Updating all TC records.")
    db.session.query(TownCrier).delete()
    db.session.commit()

    for page_nr in range(1, get_number_of_tc_pages(session) + 1):
        events = get_tc_page(session, page_nr)
        for event in events:
            tc_event = TownCrier(timestamp=cleanup_timestamp(event[0]),
                              origin=event[2],
                              origin_name=event[3],
                              target=event[4],
                              target_name=event[5],
                              event_type=event[1],
                              amount=event[6],
                              text=event[7])
            db.session.add(tc_event)
        db.session.commit()


"""
Maps the opsdata JSON to the domain model.
"""

# ------------------------------------------------------------ DominionHistory

DOM_HISTORY_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'land': 'status.land',
    'networth': 'status.networth'
}

# ------------------------------------------------------------ Dominion

DOMINION_MAPPING = {
    'code': 'code',
    'name': 'name',
    'realm': 'realm',
    'race': 'race',
    'player': 'player',
    'last_op': None
}

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
    'resource_lumber': 'status.resource_lumber',
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
    'military_archmages': 'status.military_archmages|optional',
    'wpa': 'status.wpa|optional'
}


qry_stealables = """
select
    max(c.timestamp),
    c.dominion,
    d.name,
    c.land,
    c.resource_platinum as platinum,
    c.resource_food as food,
    c.resource_gems as gems,
    c.resource_mana as mana,
    c.resource_lumber as lumber
from
    ClearSight c,
    Dominions d
where
    (c.dominion = d.code)
    and (d.realm != :realm)
    and (c.timestamp > :timestamp)
    and (d.realm != 0)
group by
    c.dominion
order by
    c.resource_platinum desc,
    c.resource_food desc,
    c.resource_mana desc,
    c.resource_gems desc,
    c.resource_lumber desc
"""


def query_stealables(db, timestamp, my_realm: int):
    """Query where the stealables are, while filtering out the bots."""
    params = {
        'timestamp': cleanup_timestamp(timestamp),
        'realm': my_realm
    }
    return db.session.execute(text(qry_stealables), params)


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

# ------------------------------------------------------------ BarracksSpy

BARRACKS_SPY_MAPPING = {
    'dominion':   None,
    'timestamp':  None,
    'draftees':   'barracks.units.home.draftees',
    'home_unit1': 'barracks.units.home.unit1',
    'home_unit2': 'barracks.units.home.unit2',
    'home_unit3': 'barracks.units.home.unit3',
    'home_unit4': 'barracks.units.home.unit4',
    'training':   'barracks.units.training|optional',
    'return':     'barracks.units.returning|optional',
}

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
    'incoming': 'land.incoming|optional'
}

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
    # 'forest_haven': 'survey.constructed.forest_haven',
    'factory': 'survey.constructed.factory',
    'guard_tower': 'survey.constructed.guard_tower',
    'shrine': 'survey.constructed.shrine',
    'barracks': 'survey.constructed.barracks',
    'dock': 'survey.constructed.dock',
    'constructing': 'survey.constructing|optional',
    'barren_land': 'survey.barren_land',
    'total_land': 'survey.total_land'
}

# ------------------------------------------------------------ Vision

VISION_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'techs': 'vision.techs',
}

# ------------------------------------------------------------ Revelation


def update_revelation(db, ops, dom):
    for spell in ops.q('revelation.spells'):
        if not db.session.get(Revelation, [dom.code, ops.timestamp, spell['spell']]):
            obj = Revelation(dominion_id=dom.code,
                             timestamp=ops.timestamp,
                             spell=spell['spell'],
                             duration=int(spell['duration']))
            dom.revelation.append(obj)
            dom.add_last_op(ops.timestamp)
        else:
            logger.debug(f"Already had Vision for {dom.code} at {ops.timestamp}")


# ------------------------------------------------------------ Town Crier

TC_FIELDS = 'timestamp,event_type,origin,origin_name,target,target_name,amount,text'

