import logging

from sqlalchemy import literal_column, func
from domain.models import Dominion, TownCrier


logger = logging.getLogger('od-info.dal')


def all_doms(db):
    return db.session.execute(db.select(Dominion)).scalars()


def dom_by_id(db, domid) -> Dominion:
    return db.session.execute(db.select(Dominion).where(Dominion.code == domid)).scalar()


def realm_of_dom(db, domid) -> int:
    return dom_by_id(db, domid).realm


def realmies(db, domid) -> list[Dominion]:
    realm_number = dom_by_id(db, domid).realm
    return db.session.execute(db.select(Dominion).where(Dominion.realm == realm_number)).scalars()


def query_count(db, query):
    counter = query.with_only_columns(func.count(literal_column("1")))
    counter = counter.order_by(None)
    return db.session.execute(counter).scalar()


def query_town_crier(db):
    return db.session.execute(db.select(TownCrier)).scalars()


def is_database_empty(db):
    is_empty = query_count(db, db.select(Dominion)) == 0
    logger.debug(f'is_database_empty: {is_empty}')
    return is_empty
