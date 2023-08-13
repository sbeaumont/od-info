from config import DATABASE, DB_SCHEMA_FILE
from opsdata.scrapetools import login
from domain.dominion import all_doms, name_for_code, Dominion
from calculators.networthcalculator import get_networth_deltas
from opsdata.ops import grab_ops, grab_my_ops, update_dom_index, get_last_scans
from operator import itemgetter
from opsdata.db import Database
from opsdata.schema import *
from app.discord import send_to_webhook
from opsdata.updater import update_ops, update_town_crier
from secret import current_player_id

logger = logging.getLogger('od-info.facade')


class ODInfoFacade(object):
    def __init__(self):
        self._session = None
        self._db = Database()
        if self._db.init(DATABASE, DB_SCHEMA_FILE):
            update_dom_index(self.session, self._db)

    @property
    def session(self):
        if not self._session:
            self._session = login(current_player_id)
        return self._session

    def teardown(self):
        self.session.close()
        self._db.teardown()
        self._db = None

    # ---------------------------------------- COMMANDS

    def update_dom_index(self):
        update_dom_index(self.session, self._db)

    def update_ops(self, dom_code):
        logger.debug("Updating ops for dominion %s", dom_code)
        if int(dom_code) == int(current_player_id):
            ops = grab_my_ops(self.session)
        else:
            ops = grab_ops(self.session, dom_code)
        update_ops(ops, self._db, dom_code)

    def update_role(self, dom_code, role):
        logger.debug("Updated dominion %s role to %s", dom_code, role)
        qry = f'UPDATE Dominions SET role = ? WHERE code = ?'
        self._db.execute(qry, (role, dom_code))

    def update_town_crier(self):
        update_town_crier(self.session, self._db)

    def send_top_bot_nw_to_discord(self):
        def create_message(header, nw_list):
            msg_content = '\n'.join([f"{item['name']}: {item['nwdelta']} ({item['networth']}) @ {item['land']}" for item in nw_list])
            return f"{header}\n\n{msg_content}"

        header_top = '**Top 10 Networth Growers since past 12 hours**'
        top10_message = create_message(header_top, self.get_top_bot_nw())
        header_bot = '**Top 10 Networth *Sinkers* since past 12 hours**'
        bot10_message = create_message(header_bot, self.get_top_bot_nw(False))
        discord_message = f"{top10_message}\n\n{bot10_message}"

        logger.debug("Sending to Discord webhook: %s", discord_message)
        webhook_response = send_to_webhook(discord_message)
        logger.debug("Webhook response: %s", webhook_response)

        return webhook_response

    def update_all(self):
        last_scans = get_last_scans(self.session)
        for dom in all_doms(self._db):
            domcode = dom['code']
            if (domcode in last_scans) and (
                    (dom['last_op'] is None) or
                    (dom['last_op'] < last_scans[domcode])):
                self.update_ops(domcode)

    # ---------------------------------------- QUERIES

    def dom_status(self, dom_code: int, update=False):
        logger.debug("Getting dom status for %s", dom_code)
        if update:
            self.update_ops(dom_code)
        return query_clearsight(self._db, dom_code)

    def dom_list(self, since='-12 hours'):
        logger.debug("Getting dom list with NW since %s", since)
        doms = all_doms(self._db)
        nw_deltas = get_networth_deltas(self._db, since)
        return sorted(doms, key=itemgetter('land'), reverse=True), nw_deltas

    def castle(self, dom_code):
        logger.debug("Getting Castle for %s", dom_code)
        return query_castle(self._db, dom_code)

    def barracks(self, dom_code):
        logger.debug("Getting Barracks for %s", dom_code)
        return query_barracks(self._db, dom_code)

    def survey(self, dom_code, latest=False):
        logger.debug("Getting survey for %s", dom_code)
        return query_survey(self._db, dom_code, latest)

    def name_for_dom_code(self, domcode):
        logger.debug("Getting name for %s", domcode)
        return name_for_code(self._db, domcode)

    def nw_history(self, dom_code):
        logger.debug("Getting NW history for %s", dom_code)
        return query_dom_history(self._db, dom_code)

    def get_town_crier(self):
        logger.debug("Getting Town Crier")
        return query_town_crier(self._db)

    def get_top_bot_nw(self, top=True):
        logger.debug("Getting Top and Bot NW changes")
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

    def economy(self):
        self.update_ops(current_player_id)
        survey = self.survey(current_player_id, latest=True)
        return {
            'homes': survey['home'],
            'population': row_s_to_dict(survey),
            'jobs': 30,
            'plat_per_tick': 40
        }

    def doms_with_ratios(self):
        all_dom_codes = [d['code'] for d in all_doms(self._db)]
        result = list()
        for domcode in all_dom_codes:
            dom = Dominion(self._db, domcode)
            if str(dom.military.ratio_estimate) != 'Unknown':
                result.append(dom)
        return sorted(result, key=lambda d: d.military.ratio_estimate, reverse=True)

    def all_doms_as_objects(self):
        all_dom_codes = [d['code'] for d in all_doms(self._db)]
        result = list()
        for domcode in all_dom_codes:
            dom = Dominion(self._db, domcode)
            if (str(dom.military.op) != 'Unknown') or (str(dom.military.dp) != 'Unknown'):
                result.append(dom)
        return sorted(result, key=lambda d: d.total_land, reverse=True)

    def all_doms_ops_age(self):
        last_ops = query_last_ops(self._db)
        return {op['code']: hours_since(op['last_op']) for op in last_ops}


