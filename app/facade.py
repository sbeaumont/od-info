from config import DATABASE, DB_SCHEMA_FILE
from opsdata.scrapetools import login
from domain.dominion import update_dom_index, all_doms, name_for_code
from calculators.networthcalculator import get_networth_deltas
from domain.ops import grab_ops
from operator import itemgetter
from opsdata.db import Database
from opsdata.schema import *
from app.discord import send_to_webhook
from opsdata.updater import update_ops, update_town_crier


class ODInfoFacade(object):
    def __init__(self):
        self._session = None
        self._db = Database()
        if self._db.init(DATABASE, DB_SCHEMA_FILE):
            update_dom_index(self.session, self._db)

    @property
    def session(self):
        if not self._session:
            self._session = login()
        return self._session

    def teardown(self):
        self._db.teardown()
        self._db = None

    # ---------------------------------------- COMMANDS

    def update_dom_index(self):
        update_dom_index(self.session, self._db)

    def update_ops(self, dom_code):
        ops = grab_ops(self.session, dom_code)
        update_ops(ops, self._db, dom_code)

    def update_role(self, dom_code, role):
        qry = f'UPDATE Dominions SET role = ? WHERE code = ?'
        self._db.execute(qry, (role, dom_code))

    def update_town_crier(self):
        update_town_crier(self.session, self._db)

    def send_top_bot_nw_to_discord(self):
        def create_message(header, nw_list):
            msg_content = '\n'.join([f"{item['name']}: {item['nwdelta']} ({item['networth']})" for item in nw_list])
            return f"{header}\n\n{msg_content}"

        header_top = '**Top 10 Networth Growers since past 12 hours**'
        top10_message = create_message(header_top, self.get_top_bot_nw())
        header_bot = '**Top 10 Networth *Sinkers* since past 12 hours**'
        bot10_message = create_message(header_bot, self.get_top_bot_nw(False))

        webhook_response = send_to_webhook(f"{top10_message}\n\n{bot10_message}")
        print("Webhook response:", webhook_response)

        return webhook_response

    # ---------------------------------------- QUERIES

    def dom_status(self, dom_code: int, update=False):
        if update:
            self.update_ops(dom_code)
        return query_clearsight(self._db, dom_code)

    def dom_list(self, since='-12 hours'):
        doms = all_doms(self._db)
        nw_deltas = get_networth_deltas(self._db, since)
        return sorted(doms, key=itemgetter('land'), reverse=True), nw_deltas

    def castle(self, dom_code):
        return query_castle(self._db, dom_code)

    def barracks(self, dom_code):
        return query_barracks(self._db, dom_code)

    def name_for_dom_code(self, domcode):
        return name_for_code(self._db, domcode)

    def nw_history(self, dom_code):
        return query_dom_history(self._db, dom_code)

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

