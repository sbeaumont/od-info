"""
Higher order update actions.
"""

import logging

from app.towncrier import get_number_of_tc_pages, get_tc_page
from opsdata.schema import *

logger = logging.getLogger('od-info.db')

# ---------------------------------------------------------------------- Updaters Ops => DB


def update_ops(ops, db, dom_code):
    logger.debug("Updating ops for dominion %s", dom_code)
    if ops.has_clearsight:
        update_clearsight(ops, db, dom_code)
    if ops.has_castle:
        update_castle(ops, db, dom_code)
    if ops.has_barracks:
        update_barracks(ops, db, dom_code)
    if ops.has_survey:
        update_survey(ops, db, dom_code)
    if ops.has_land:
        update_land(ops, db, dom_code)
    if ops.has_vision:
        update_vision(ops, db, dom_code)


def update_town_crier(session, db):
    logger.debug("Updating all TC records.")
    tc_replace_qry = f'REPLACE INTO TownCrier ({TC_FIELDS}) VALUES (?,?,?,?,?,?,?,?)'

    for page_nr in range(1, get_number_of_tc_pages(session) + 1):
        events = get_tc_page(session, page_nr)
        db.executemany(tc_replace_qry, events)
