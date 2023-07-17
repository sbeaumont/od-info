from config import DATABASE, DB_SCHEMA_FILE
from domain.scrapetools import login
from domain.dominion import update_dom_index, all_doms, name_for_code
from domain.networth import get_networth_deltas
from operator import itemgetter
from opsdata.db import Database
from opsdata.schema import *
from calcapp.discord import send_to_webhook

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

    def dom_list(self, since='-12 hours'):
        doms = all_doms(self._db)
        nw_deltas = get_networth_deltas(self._db, since)
        return sorted(doms, key=itemgetter('land'), reverse=True), nw_deltas

    def dom_status(self, dom_code: int):
        update_ops(self.session, self._db, dom_code)
        return query_clearsight(self._db, dom_code)

    def castle(self, dom_code):
        return query_castle(self._db, dom_code)

    def update_role(self, dom_code, role):
        qry = f'UPDATE Dominions SET role = ? WHERE code = ?'
        self._db.execute(qry, (role, dom_code))

    def name_for_dom_code(self, domcode):
        return name_for_code(self._db, domcode)

    def update_town_crier(self):
        update_town_crier(self.session, self._db)

    def update_dom_index(self):
        update_dom_index(self.session, self._db)

    def get_town_crier(self):
        return query_town_crier(self._db)

    def get_top_bot_nw(self, top=True):
        doms, nw_deltas = self.dom_list()
        sorted_deltas = sorted(nw_deltas.items(), key=lambda x: x[1], reverse=top)[:10]
        selected_doms = [d[0] for d in sorted_deltas]
        relevant_doms = [d for d in doms if d['code'] in selected_doms]
        result = list()
        for row in relevant_doms:
            nw_row = {
                'code': row['code'],
                'name': row['name'],
                'land': row['land'],
                'networth': row['networth'],
                'nwdelta': nw_deltas[row['code']],
                'realm': row['realm']
            }
            result.append(nw_row)
        return sorted(result, key=itemgetter('nwdelta'), reverse=top)

    def send_top_bot_nw_to_discord(self):
        top_nw = self.get_top_bot_nw()
        top10_message = '\n'.join([f"{item['name']}: {item['nwdelta']} ({item['networth']})" for item in top_nw])
        header = '**Top 10 Networth Growers since past 12 hours**'
        webhook_response_top = send_to_webhook(f"{header}\n\n{top10_message}")
        print("Webhook response:", webhook_response_top)
        bot_nw = self.get_top_bot_nw(False)
        bot10_message = '\n'.join([f"{item['name']}: {item['nwdelta']} ({item['networth']})" for item in bot_nw])
        header = '**Top 10 Networth *Sinkers* since past 12 hours**'
        webhook_response_bot = send_to_webhook(f"{header}\n\n{bot10_message}")
        print("Webhook response:", webhook_response_bot)
        return f"Top: {webhook_response_top}, Bot: {webhook_response_bot}"



