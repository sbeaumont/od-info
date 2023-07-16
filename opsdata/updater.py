from domain.scrapetools import get_soup_page
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


def update_clearsight(ops, db, dom_code):
    timestamp = ops.q('status.created_at')
    if check_exists(db, 'ClearSight', dom_code, timestamp):
        return

    qry = """INSERT INTO ClearSight (
                dominion, 
                timestamp, 
                land, 
                peasants, 
                networth, 
                prestige, 
                resource_platinum, 
                resource_food, 
                resource_mana, 
                resource_ore, 
                resource_gems, 
                resource_boats, 
                military_draftees, 
                military_unit1, 
                military_unit2, 
                military_unit3, 
                military_unit4) 
            VALUES (
                :dominion, 
                :timestamp, 
                :land, 
                :peasants, 
                :networth, 
                :prestige, 
                :resource_platinum, 
                :resource_food, 
                :resource_mana, 
                :resource_ore, 
                :resource_gems, 
                :resource_boats, 
                :military_draftees, 
                :military_unit1, 
                :military_unit2, 
                :military_unit3, 
                :military_unit4)"""

    params = {
        'dominion': dom_code,
        'timestamp': timestamp,
        'land': ops.q('status.land'),
        'peasants': ops.q('status.peasants'),
        'networth': ops.q('status.networth'),
        'prestige': ops.q('status.prestige'),
        'resource_platinum': ops.q('status.resource_platinum'),
        'resource_food': ops.q('status.resource_food'),
        'resource_mana': ops.q('status.resource_mana'),
        'resource_ore': ops.q('status.resource_ore'),
        'resource_gems': ops.q('status.resource_gems'),
        'resource_boats': ops.q('status.resource_boats'),
        'military_draftees': ops.q('status.military_draftees'),
        'military_unit1': ops.q('status.military_unit1'),
        'military_unit2': ops.q('status.military_unit2'),
        'military_unit3': ops.q('status.military_unit3'),
        'military_unit4': ops.q('status.military_unit4')
    }

    db.execute(qry, params)


def query_castle(db, dom_code):
    qry = """SELECT
                dominion,
                timestamp,
                science_points,
                science_rating,
                keep_points,
                keep_rating,
                spires_points,
                spires_rating,
                forges_points,
                forges_rating,
                walls_points,
                walls_rating,
                harbor_points,
                harbor_rating
            FROM
                CastleSpy
            WHERE
                dominion = :dom_code"""

    return db.query(qry, {'dom_code': dom_code})


def update_castle(ops, db, dom_code):
    timestamp = ops.q('castle.created_at')
    if check_exists(db, 'CastleSpy', dom_code, timestamp):
        return

    qry = """INSERT INTO CastleSpy (
                dominion,
                timestamp,
                science_points,
                science_rating,
                keep_points,
                keep_rating,
                spires_points,
                spires_rating,
                forges_points,
                forges_rating,
                walls_points,
                walls_rating,
                harbor_points,
                harbor_rating) 
            VALUES (
                :dominion,
                :timestamp,
                :science_points,
                :science_rating,
                :keep_points,
                :keep_rating,
                :spires_points,
                :spires_rating,
                :forges_points,
                :forges_rating,
                :walls_points,
                :walls_rating,
                :harbor_points,
                :harbor_rating)"""

    params = {
        'dominion': dom_code,
        'timestamp': timestamp,
        'science_points': ops.q('castle.science.points'),
        'science_rating': ops.q('castle.science.rating'),
        'keep_points':    ops.q('castle.keep.points'),
        'keep_rating':    ops.q('castle.keep.rating'),
        'spires_points':  ops.q('castle.spires.points'),
        'spires_rating':  ops.q('castle.spires.rating'),
        'forges_points':  ops.q('castle.forges.points'),
        'forges_rating':  ops.q('castle.forges.rating'),
        'walls_points':   ops.q('castle.walls.points'),
        'walls_rating':   ops.q('castle.walls.rating'),
        'harbor_points':  ops.q('castle.harbor.points'),
        'harbor_rating':  ops.q('castle.harbor.rating'),
    }

    db.execute(qry, params)
