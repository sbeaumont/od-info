"""
Higher order update actions.
"""

import logging

from sqlalchemy import text

from odinfo.opsdata.ops import Ops
from odinfo.services.od_api import ODApi, EVENT_LIMIT
from odinfo.timeutils import cleanup_timestamp, current_od_time
from odinfo.domain.models import Dominion, DominionHistory, TownCrier, MyDominion, Wonder, War
from odinfo.facade.towncrier import get_number_of_tc_pages, get_tc_page
from odinfo.domain.models import (ClearSight, CastleSpy, BarracksSpy,
                                  SurveyDominion, LandSpy, Vision, Revelation)
from odinfo.repositories.game import GameRepository

logger = logging.getLogger('od-info.updater')

# ---------------------------------------------------------------------- Updaters Ops => DB


def init_my_dominion(od_api: ODApi, repo: GameRepository):
    """Store the dominion of the API key and its round."""
    me = od_api.me()
    with repo.transaction():
        repo.session.add(MyDominion(code=me['id'],
                                    realm=me['realm']['number'],
                                    round_id=me['round']['id'],
                                    round_start=cleanup_timestamp(me['round']['start_date']),
                                    round_duration_days=me['round']['duration_days']))


def update_realms(od_api: ODApi, repo: GameRepository):
    """Update the wonders and wars from the realms in the OpenDominion API."""
    realms = od_api.realms(repo.get_my_dominion().round_id)
    update_wonders(realms, repo)
    update_wars(realms, repo)


def update_wonders(realms: list, repo: GameRepository):
    """Replace the wonders with the ones the realms hold now."""
    wonders = []
    for realm in realms:
        for wonder in realm['wonders']:
            wonders.append(Wonder(key=wonder['key'],
                                  realm=realm['number'],
                                  name=wonder['name'],
                                  power=wonder['power'],
                                  max_power=wonder['max_power'],
                                  power_is_approximate=wonder['power_is_approximate']))
    repo.replace_wonders(wonders)


def update_wars(realms: list, repo: GameRepository):
    """Replace the wars with the declarations that have not ended."""
    wars = []
    for realm in realms:
        for war in realm['wars']:
            if war['direction'] == 'outgoing':
                wars.append(War(realm=realm['number'],
                                target_realm=war['realm_number'],
                                target_realm_name=war['realm_name'],
                                status=war['status'],
                                declared_at=cleanup_timestamp(war['declared_at']),
                                active_at=cleanup_timestamp(war['active_at']) if war['active_at'] else None,
                                inactive_at=cleanup_timestamp(war['inactive_at']) if war['inactive_at'] else None))
    repo.replace_wars(wars)


def update_dom_index(od_api: ODApi, repo: GameRepository):
    """Update the dominion index from the OpenDominion API."""
    timestamp = current_od_time()
    doms = {d.code: d for d in repo.all_dominions()}
    new_doms = []
    new_history = []
    for line in od_api.dominions(repo.get_my_dominion().round_id):
        code = line['id']
        if code not in doms:
            dom = Dominion(code=code,
                           name=line['name'],
                           realm=line['realm_number'],
                           race=line['race'])
            new_doms.append(dom)

        dh = DominionHistory(dominion_id=code,
                             timestamp=timestamp,
                             land=line['land'],
                             networth=line['networth'])
        new_history.append(dh)

    with repo.transaction():
        for dom in new_doms:
            repo.session.add(dom)
        for dh in new_history:
            repo.session.add(dh)


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


def update_ops(ops, repo: GameRepository, dom_code):
    """Update ops data for a single dominion."""
    logger.debug("Updating ops for dominion %s", dom_code)
    dom = repo.get_dominion(dom_code)
    session = repo.session
    # Ensure the dominion object is tracked by the session so last_op changes get saved
    session.add(dom)
    if ops.has_clearsight:
        timestamp = cleanup_timestamp(ops.q('clear_sight.created_at'))
        if not session.get(ClearSight, [dom_code, timestamp]):
            obj = ClearSight(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, CLEARSIGHT_MAPPING)
            # The game sends null for an exact clear sight
            accuracy = ops.q('clear_sight.clear_sight_accuracy')
            obj.clear_sight_accuracy = 1.0 if accuracy is None else accuracy
            session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had ClearSight for {dom_code} at {timestamp}")
    if ops.has_castle:
        timestamp = cleanup_timestamp(ops.q('castle_spy.created_at'))
        if not session.get(CastleSpy, [dom_code, timestamp]):
            obj = CastleSpy(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, CASTLE_SPY_MAPPING)
            session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Castle Spy for {dom_code} at {timestamp}")
    if ops.has_barracks:
        timestamp = cleanup_timestamp(ops.q('barracks_spy.created_at'))
        if not session.get(BarracksSpy, [dom_code, timestamp]):
            obj = BarracksSpy(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, BARRACKS_SPY_MAPPING)
            session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Barracks Spy for {dom_code} at {timestamp}")
    if ops.has_survey:
        timestamp = cleanup_timestamp(ops.q('survey_dominion.created_at'))
        if not session.get(SurveyDominion, [dom_code, timestamp]):
            obj = SurveyDominion(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, SURVEY_DOMINION_MAPPING)
            session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had SurveyDominion for {dom_code} at {timestamp}")
    if ops.has_land:
        timestamp = cleanup_timestamp(ops.q('land_spy.created_at'))
        if not session.get(LandSpy, [dom_code, timestamp]):
            obj = LandSpy(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, LAND_SPY_MAPPING)
            session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had LandSpy for {dom_code} at {timestamp}")
    if ops.has_vision:
        timestamp = cleanup_timestamp(ops.q('vision.created_at'))
        if not session.get(Vision, [dom_code, timestamp]):
            obj = Vision(dominion_id=dom_code, timestamp=timestamp)
            update_obj(ops, obj, VISION_MAPPING)
            session.add(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Vision for {dom_code} at {timestamp}")
    if ops.has_revelation:
        update_revelation(session, ops, dom)
    session.commit()


def update_barracks_archive(od_api: ODApi, repo: GameRepository, dom_code: int, max_age_hours: int):
    """Store every barracks spy of the archive within max_age_hours."""
    logger.debug(f"Updating barracks archive for dom {dom_code}")
    archive = od_api.op_archive(dom_code, 'barracks_spy', max_age_hours=max_age_hours)
    for barracks_spy in archive['ops']:
        update_ops(Ops({'barracks_spy': barracks_spy}, dom_code), repo, dom_code)


def scraped_number(value: str) -> int | None:
    """A code or amount from the Town Crier scraper, which gives blank text for none."""
    return int(value) if value.strip() else None


def reload_town_crier(od_session, repo: GameRepository):
    """Replace all Town Crier records with every page scraped from OpenDominion."""
    logger.debug("Reloading all TC records.")
    all_events = []
    for page_nr in range(1, get_number_of_tc_pages(od_session) + 1):
        events = get_tc_page(od_session, page_nr)
        for event in events:
            tc_event = TownCrier(timestamp=cleanup_timestamp(event[0]),
                                 origin=scraped_number(event[2]),
                                 origin_name=event[3],
                                 target=scraped_number(event[4]),
                                 target_name=event[5],
                                 event_type=event[1],
                                 amount=scraped_number(event[6]))
            # The scraper gives the defender first for a bounce, the API the attacker
            if tc_event.event_type == 'bounce':
                tc_event.origin, tc_event.target = tc_event.target, tc_event.origin
                tc_event.origin_name, tc_event.target_name = tc_event.target_name, tc_event.origin_name
            all_events.append(tc_event)
    repo.replace_all_town_crier_events(all_events)


TC_EVENT_TYPES = {
    'war_declared': 'war_declare',
    'war_canceled': 'war_cancel',
    'wonder_spawned': 'wonder_spawn',
    'wonder_attacked': 'wonder_attack',
    'wonder_destroyed': 'wonder_destruction',
    'raid_attacked': 'raid_attack',
    'abandoned': 'abandon',
}


def town_crier_event(event: dict) -> TownCrier:
    """Map an API Town Crier event to a TownCrier row. Wars and abandons use realm numbers."""
    tc = TownCrier(timestamp=cleanup_timestamp(event['created_at']),
                   origin=event['source_id'],
                   origin_name=event['source_name'],
                   target=event['target_id'],
                   target_name=event['target_name'])
    data = event['data']
    if event['type'] == 'invasion':
        tc.event_type = 'invasion' if data['success'] else 'bounce'
        tc.amount = data['land_lost']
        return tc
    tc.event_type = TC_EVENT_TYPES[event['type']]
    if event['type'] in ('war_declared', 'war_canceled'):
        tc.origin, tc.origin_name = data['source_realm']['number'], data['source_realm']['name']
        tc.target, tc.target_name = data['target_realm']['number'], data['target_realm']['name']
    elif event['type'] == 'wonder_spawned':
        tc.origin, tc.origin_name = None, None
        tc.target, tc.target_name = None, data['wonder']
    elif event['type'] == 'wonder_attacked':
        tc.target, tc.target_name = data['realm_number'], data['wonder']
    elif event['type'] == 'wonder_destroyed':
        rebuilt_by = data['rebuilt_by_realm']
        tc.origin = rebuilt_by['number'] if rebuilt_by else None
        tc.origin_name = rebuilt_by['name'] if rebuilt_by else None
        tc.target, tc.target_name = None, data['wonder']
    elif event['type'] == 'raid_attacked':
        tc.target, tc.target_name = None, data['tactic']
    elif event['type'] == 'abandoned':
        tc.target = event['source_realm_number']
    return tc


def update_town_crier(od_api: ODApi, repo: GameRepository):
    """Add the Town Crier events since the newest stored one."""
    since = repo.latest_town_crier_timestamp()
    logger.debug("Updating TC records since %s.", since)
    events = od_api.events(repo.get_my_dominion().round_id, since=since)
    if len(events) == EVENT_LIMIT:
        logger.warning("The API returned the maximum of %d Town Crier events, older events may be missing",
                       EVENT_LIMIT)
    new_events = []
    for event in events:
        tc_event = town_crier_event(event)
        key = [tc_event.timestamp, tc_event.origin, tc_event.event_type, tc_event.target]
        if not repo.session.get(TownCrier, key):
            new_events.append(tc_event)
    repo.add_town_crier_events(new_events)


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
    'land': 'clear_sight.land',
    'peasants': 'clear_sight.peasants',
    'networth': 'clear_sight.networth',
    'prestige': 'clear_sight.prestige',
    'resource_platinum': 'clear_sight.resource_platinum',
    'resource_food': 'clear_sight.resource_food',
    'resource_lumber': 'clear_sight.resource_lumber',
    'resource_mana': 'clear_sight.resource_mana',
    'resource_ore': 'clear_sight.resource_ore',
    'resource_gems': 'clear_sight.resource_gems',
    'resource_boats': 'clear_sight.resource_boats',
    'military_draftees': 'clear_sight.military_draftees',
    'military_unit1': 'clear_sight.military_unit1',
    'military_unit2': 'clear_sight.military_unit2',
    'military_unit3': 'clear_sight.military_unit3',
    'military_unit4': 'clear_sight.military_unit4',
    'military_spies': 'clear_sight.military_spies|optional',
    'military_assassins': 'clear_sight.military_assassins|optional',
    'military_wizards': 'clear_sight.military_wizards|optional',
    'military_archmages': 'clear_sight.military_archmages|optional',
    'wpa': 'clear_sight.wpa|optional',
    'spa': 'clear_sight.spa|optional'
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
    c.resource_lumber as lumber,
    c.resource_ore as ore
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
    c.resource_lumber desc,
    c.resource_ore desc
"""


def query_stealables(repo: GameRepository, timestamp, my_realm: int):
    """Query where the stealables are, while filtering out the bots."""
    params = {
        'timestamp': cleanup_timestamp(timestamp),
        'realm': my_realm
    }
    return repo.session.execute(text(qry_stealables), params)


# ------------------------------------------------------------ CastleSpy

CASTLE_SPY_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'science_points': 'castle_spy.science.points',
    'science_rating': 'castle_spy.science.rating',
    'keep_points':    'castle_spy.keep.points',
    'keep_rating':    'castle_spy.keep.rating',
    'spires_points':  'castle_spy.spires.points',
    'spires_rating':  'castle_spy.spires.rating',
    'forges_points':  'castle_spy.forges.points',
    'forges_rating':  'castle_spy.forges.rating',
    'walls_points':   'castle_spy.walls.points',
    'walls_rating':   'castle_spy.walls.rating',
    'harbor_points':  'castle_spy.harbor.points',
    'harbor_rating':  'castle_spy.harbor.rating'
}

# ------------------------------------------------------------ BarracksSpy

BARRACKS_SPY_MAPPING = {
    'dominion':   None,
    'timestamp':  None,
    'draftees':   'barracks_spy.units.home.draftees',
    'home_unit1': 'barracks_spy.units.home.unit1',
    'home_unit2': 'barracks_spy.units.home.unit2',
    'home_unit3': 'barracks_spy.units.home.unit3',
    'home_unit4': 'barracks_spy.units.home.unit4',
    'training':   'barracks_spy.units.training|optional',
    'returning':  'barracks_spy.units.returning|optional',
}

# ------------------------------------------------------------ LandSpy

LAND_SPY_MAPPING = {
    'dominion':   None,
    'timestamp':  None,
    'total': 'land_spy.totalLand',
    'barren': 'land_spy.totalBarrenLand',
    'constructed': 'land_spy.totalConstructedLand',
    'plain': 'land_spy.explored.plain.amount',
    'plain_constructed': 'land_spy.explored.plain.constructed',
    'mountain': 'land_spy.explored.mountain.amount',
    'mountain_constructed': 'land_spy.explored.mountain.constructed',
    'swamp': 'land_spy.explored.swamp.amount',
    'swamp_constructed': 'land_spy.explored.swamp.constructed',
    'cavern': 'land_spy.explored.cavern.amount',
    'cavern_constructed': 'land_spy.explored.cavern.constructed',
    'forest': 'land_spy.explored.forest.amount',
    'forest_constructed': 'land_spy.explored.forest.constructed',
    'hill': 'land_spy.explored.hill.amount',
    'hill_constructed': 'land_spy.explored.hill.constructed',
    'water': 'land_spy.explored.water.amount',
    'water_constructed': 'land_spy.explored.water.constructed',
    'incoming': 'land_spy.incoming|optional'
}

# ------------------------------------------------------------ Survey Dominion

SURVEY_DOMINION_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'home': 'survey_dominion.constructed.home',
    'alchemy': 'survey_dominion.constructed.alchemy',
    'farm': 'survey_dominion.constructed.farm',
    'smithy': 'survey_dominion.constructed.smithy',
    'masonry': 'survey_dominion.constructed.masonry',
    'ore_mine': 'survey_dominion.constructed.ore_mine',
    'gryphon_nest': 'survey_dominion.constructed.gryphon_nest',
    'tower': 'survey_dominion.constructed.tower',
    'wizard_guild': 'survey_dominion.constructed.wizard_guild',
    'temple': 'survey_dominion.constructed.temple',
    'diamond_mine': 'survey_dominion.constructed.diamond_mine',
    'school': 'survey_dominion.constructed.school',
    'lumberyard': 'survey_dominion.constructed.lumberyard',
    # 'forest_haven': 'survey_dominion.constructed.forest_haven',
    'factory': 'survey_dominion.constructed.factory',
    'guard_tower': 'survey_dominion.constructed.guard_tower',
    'shrine': 'survey_dominion.constructed.shrine',
    'barracks': 'survey_dominion.constructed.barracks',
    'dock': 'survey_dominion.constructed.dock',
    'constructing': 'survey_dominion.constructing|optional',
    'barren_land': 'survey_dominion.barren_land',
    'total_land': 'survey_dominion.total_land'
}

# ------------------------------------------------------------ Vision

VISION_MAPPING = {
    'dominion': None,
    'timestamp': None,
    'techs': 'vision.techs',
}

# ------------------------------------------------------------ Revelation


def update_revelation(session, ops, dom):
    """Update revelation spells for a dominion."""
    timestamp = cleanup_timestamp(ops.q('revelation.created_at'))
    for spell in ops.q('revelation.spells'):
        if not session.get(Revelation, [dom.code, timestamp, spell['spell']]):
            obj = Revelation(dominion_id=dom.code,
                             timestamp=timestamp,
                             spell=spell['spell'],
                             duration=int(spell['duration']))
            dom.revelation.append(obj)
            dom.add_last_op(timestamp)
        else:
            logger.debug(f"Already had Revelation for {dom.code} at {timestamp}")


# ------------------------------------------------------------ Town Crier

TC_FIELDS = 'timestamp,event_type,origin,origin_name,target,target_name,amount,text'

