from config import DATABASE, DB_SCHEMA_FILE
from domain.scrapetools import login
from domain.dominion import update_dom_index, all_doms
from operator import itemgetter
from domain.ops import get_ops
from opsdata.db import Database
from opsdata.updater import update_ops, query_castle


class OpsWrapper(object):
    def __init__(self, ops):
        self.ops = ops

    @property
    def name(self) -> str:
        return self.ops.q('status.name')

    @property
    def source(self) -> str:
        return self.ops.contents


class CalcFacade(object):
    def __init__(self):
        self._session = None
        self._db = Database()
        if self._db.init(DATABASE, DB_SCHEMA_FILE):
            update_dom_index(self.session, self._db)

    def teardown(self):
        self._db.teardown()
        self._db = None

    @property
    def session(self):
        if not self._session:
            self._session = login()
        return self._session

    def dom_list(self):
        doms = all_doms(self._db)
        return sorted(doms, key=itemgetter('land'), reverse=True)

    def dom_status(self, dom_code: int):
        update_ops(self.session, self._db, dom_code)
        qry = 'SELECT dominion, timestamp, land, peasants FROM ClearSight WHERE dominion = :dom_code ORDER BY timestamp DESC'
        return self._db.query(qry, {'dom_code': dom_code})

    def castle(self, dom_code):
        return query_castle(self._db, dom_code)

    def update_role(self, dom_code, role):
        qry = f'UPDATE Dominions SET role = ? WHERE code = ?'
        self._db.execute(qry, (role, dom_code))

