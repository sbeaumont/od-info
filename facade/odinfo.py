"""
Facade object to ensure that all "business and data logic" doesn't get mixed into user interface code.

This class is intentianally the smorgasbord of queries and actions that the UI (flask_app) needs
so that any ugliness is contained in this class.
"""

import logging
from operator import itemgetter

from calculators.economy import Economy
from calculators.military import MilitaryCalculator, RatioCalculator
from calculators.networthcalculator import get_networth_deltas
from config import SEARCH_PAGE
from config import current_player_id
from domain.dataaccesslayer import all_doms, dom_by_id, is_database_empty, realmies, query_town_crier, realm_of_dom
from domain.models import Dominion
from domain.timeutils import hours_since, add_duration, current_od_time
from facade.awardstats import AwardStats
from facade.discord import send_to_webhook
from opsdata.ops import grab_ops, grab_my_ops, get_last_scans
from opsdata.scrapetools import login, read_tick_time, get_soup_page
from opsdata.updater import update_ops, update_town_crier, update_dom_index, query_stealables
from sqlalchemy import text

logger = logging.getLogger('od-info.facade')


class ODInfoFacade(object):
    def __init__(self, db):
        self._session = None
        self._db = db
        if is_database_empty(self._db):
            update_dom_index(self.session, self._db)

    @property
    def session(self):
        if not self._session:
            self._session = login(current_player_id)
        return self._session

    def teardown(self):
        self.session.close()

    def update_all(self):
        last_scans = get_last_scans(self.session)
        for dom in all_doms(self._db):
            domcode = dom.code
            if (domcode in last_scans) and (
                    (dom.last_op is None) or
                    (dom.last_op < last_scans[domcode])):
                self.update_ops(domcode)

    # ---------------------------------------- COMMANDS - Update from OpenDominion.net

    def update_dom_index(self):
        update_dom_index(self.session, self._db)

    def update_ops(self, dom_code):
        logger.debug("Updating ops for dominion %s", dom_code)
        if int(dom_code) == int(current_player_id):
            ops = grab_my_ops(self.session)
        else:
            ops = grab_ops(self.session, dom_code)
        if ops:
            update_ops(ops, self._db, dom_code)
            # TODO Calculate the expensive stuff like military calcs and cache them.
        else:
            logger.warning(f"Can't get ops for dominion {dom_code}")

    def update_town_crier(self):
        update_town_crier(self.session, self._db)

    def update_realmies(self):
        for dom_code in self.realmie_codes():
            self.update_ops(dom_code)

    # ---------------------------------------- COMMANDS - Change directly

    def update_role(self, dom_code, role):
        logger.debug("Updating dominion %s role to %s", dom_code, role)
        qry = text(f'UPDATE Dominions SET role = :role WHERE code = :code')
        self._db.session.execute(qry, {'role': role, 'code': dom_code})
        self._db.session.commit()

    def update_player(self, dom_code, player_name):
        logger.debug("Updating dominion player name from %s to %s", dom_code, player_name)
        qry = text(f'UPDATE Dominions SET player = ? WHERE code = ?')
        self._db.session.execute(qry, (player_name, dom_code))
        self._db.session.commit()

    # ---------------------------------------- COMMANDS - Send out information

    def send_top_bot_nw_to_discord(self):
        def create_message(header, nw_list):
            msg_content = '\n'.join([f"{item['name']:<50} {item['realm']:>5} {item['nwdelta']:>9} {item['networth']:>9} {item['land']:>5}" for item in nw_list])
            return f"{header}\n```{'Dominion':<50} {'Realm':>5} {'Delta':>9} {'Networth':>9} {'Land':>5}\n\n{msg_content}```"

        header_top = '**Top 10 Networth Growers since past 12 hours**'
        top10_message = create_message(header_top, self.get_top_bot_nw(filter_zeroes=True))
        header_bot = '**Top 10 Networth *Sinkers* since past 12 hours**'
        bot10_message = create_message(header_bot, self.get_top_bot_nw(top=False, filter_zeroes=True))
        nr_networth_unchanged = 10
        header_unchanged = f'**Top {nr_networth_unchanged} largest Networth *Unchanged* since past 12 hours**'
        unchanged_message = create_message(header_unchanged, self.get_unchanged_nw(top=nr_networth_unchanged))
        discord_message = f"{top10_message}\n{bot10_message}"

        logger.debug("Sending to Discord webhook: %s", discord_message)
        webhook_response = send_to_webhook(discord_message)
        logger.debug("Webhook response: %s", webhook_response)

        logger.debug("Sending to Discord webhook: %s", unchanged_message)
        webhook_response = send_to_webhook(unchanged_message)
        logger.debug("Webhook response: %s", webhook_response)

        return webhook_response

    # ---------------------------------------- QUERIES - Single Dominion

    def dominion(self, dom_code):
        return dom_by_id(self._db, dom_code)
        # return Dominion(self._db, dom_code)

    def military(self, dom: Dominion):
        return MilitaryCalculator(dom)

    def ratios(self, dom: Dominion):
        return RatioCalculator(dom)

    def ops_age(self, dom: Dominion):
        return hours_since(dom.last_op)

    def dom_status(self, dom_code: int, update=False):
        """Get information of a specific dominion."""
        logger.debug("Getting dom status for %s", dom_code)
        if update:
            self.update_ops(dom_code)
        return dom_by_id(self._db, dom_code).last_cs
        # return query_clearsight(self._db, dom_code)

    def nw_history(self, dom_code):
        """Get the networth history of a specific dominion."""
        logger.debug("Getting NW history for %s", dom_code)
        return dom_by_id(self._db, dom_code).history
        # return query_dom_history(self._db, dom_code)

    # ---------------------------------------- QUERIES - Lists

    def dom_list(self, since='-12 hours'):
        """Get overview information of all dominions."""
        logger.debug("Getting dom list since %s", since)
        doms = all_doms(self._db)
        return sorted(doms, key=lambda x: x.current_land, reverse=True)

    def nw_deltas(self):
        """Get overview information of all dominions."""
        logger.debug("Getting NW deltas")
        return get_networth_deltas(self._db)

    def get_town_crier(self):
        logger.debug("Getting Town Crier")
        return query_town_crier(self._db)

    def ratio_list(self):
        """Overview of the ratios of all dominions."""
        rc_list = [RatioCalculator(dom) for dom in all_doms(self._db)]
        rc_list = [rc for rc in rc_list if rc.can_calculate and (hours_since(rc.dom.last_op) < 100)]
        result = list()
        for rc in rc_list:
            result.append({
                'code': rc.dom.code,
                'name': rc.dom.name,
                'realm': rc.dom.realm,
                'land': rc.dom.current_land,
                'race': rc.dom.race,
                'networth': rc.dom.current_networth,
                'spy_units_equiv': rc.spy_units_equiv,
                'wiz_units_equiv': rc.wiz_units_equiv,
                'spywiz_networth': rc.spywiz_networth,
                'spywiz_units': rc.spywiz_units,
                'ratio_estimate': rc.ratio_estimate,
                'spy_ratio_estimate': rc.spy_ratio_estimate,
                'max_spy_ratio_estimate': rc.max_spy_ratio_estimate,
                'wiz_ratio_estimate': rc.wiz_ratio_estimate,
                'max_wiz_ratio_estimate': rc.max_wiz_ratio_estimate,
                'ops_age': hours_since(rc.dom.last_op)
            })
        return sorted(result, key=lambda d: d['ratio_estimate'], reverse=True)

    def all_doms_ops_age(self):
        return {dom.code: hours_since(dom.last_op) for dom in all_doms(self._db)}

    def doms_as_mil_calcs(self, dom_list: list) -> list:
        mil_calcs = [MilitaryCalculator(dom) for dom in dom_list]
        return sorted(mil_calcs, key=lambda d: d.dom.current_networth, reverse=True)

    def military_list(self, versus_op=0, top=20):
        mc_list = [d for d in self.doms_as_mil_calcs(all_doms(self._db).all()[:top]) if d.army]
        result_list = list()
        current_day = self.current_tick.day
        for mc in mc_list:
            five_four_op, five_four_dp = mc.five_over_four
            boat_stuff = mc.boats(current_day)
            dom_result = {
                'code': mc.dom.code,
                'name': mc.dom.name,
                'realm': mc.dom.realm,
                'race': mc.dom.race,
                'ops_age': hours_since(mc.dom.last_op),
                'land': mc.dom.current_land,
                'hittable_75_percent': mc.hittable_75_percent,
                'five_over_four_op': five_four_op,
                'five_over_four_dp': five_four_dp,
                'temples': mc.temple_bonus,
                'boats_amount': boat_stuff[0],
                'boats_prt': boat_stuff[1],
                'boats_sendable': boat_stuff[2],
                'boats_capacity': boat_stuff[3],
                'paid_until': mc.army.get('paid_until', '?'),
                'raw_op': mc.raw_op,
                'op': mc.op,
                'raw_dp': mc.raw_dp,
                'dp': mc.dp,
                'safe_op': mc.safe_op if versus_op == 0 else mc.safe_op_versus(versus_op),
                'safe_dp': mc.safe_dp if versus_op == 0 else mc.safe_dp_versus(versus_op),
                'networth': mc.dom.current_networth
            }
            result_list.append(dom_result)
        return result_list

    def top_op(self, mil_calc_result: list):
        topop = mil_calc_result[0]
        for mc in mil_calc_result[1:]:
            if mc['five_over_four_op'] > topop['five_over_four_op']:
                topop = mc
        return topop

    def realmie_codes(self) -> list[int]:
        logger.debug("Getting Realmies")
        return [dom.code for dom in self.realmies()]

    def realmies(self) -> list[Dominion]:
        logger.debug("Getting Realmies")
        return realmies(self._db, current_player_id)

    def stealables(self) -> list:
        logger.debug("Listing stealables")
        since = add_duration(current_od_time(as_str=True), -12, True)
        result = query_stealables(self._db, since, realm_of_dom(self._db, current_player_id))
        return result

    # ---------------------------------------- QUERIES - Utility

    def name_for_dom_code(self, domcode):
        """Get the name connected with a dominion code."""
        logger.debug("Getting name for %s", domcode)
        return dom_by_id(self._db, domcode).name

    @property
    def current_tick(self):
        soup = get_soup_page(self.session, SEARCH_PAGE)
        return read_tick_time(soup)

    # ---------------------------------------- QUERIES - Reports

    def get_unchanged_nw(self, top: int = 50):
        logger.debug("Getting Unchanged NW")
        doms = self.dom_list()
        nw_deltas = self.nw_deltas()
        selected_doms = [d for d, nwd in nw_deltas.items() if nwd == 0]
        relevant_doms = [d for d in doms if d.code in selected_doms]
        result = list()
        for row in relevant_doms:
            nw_row = {
                'code': row.code,
                'name': row.name,
                'land': row.current_land,
                'networth': row.current_networth,
                'nwdelta': nw_deltas[row.code],
                'realm': row.realm
            }
            result.append(nw_row)
        return sorted(result, key=itemgetter('land'), reverse=True)[:top]

    def get_top_bot_nw(self, top=True, filter_zeroes=False):
        logger.debug("Getting Top and Bot NW changes")
        doms = self.dom_list()
        nw_deltas = self.nw_deltas()
        sorted_deltas = sorted(nw_deltas.items(), key=lambda x: x[1], reverse=top)[:10]
        selected_doms = [d[0] for d in sorted_deltas]
        relevant_doms = [d for d in doms if d.code in selected_doms]
        result = list()
        for row in relevant_doms:
            nw_row = {
                'code': row.code,
                'name': row.name,
                'land': row.current_land,
                'networth': row.current_networth,
                'nwdelta': nw_deltas[row.code],
                'realm': row.realm
            }
            result.append(nw_row)
        if filter_zeroes:
            result = [dom for dom in result if dom['nwdelta'] != 0]
        return sorted(result, key=itemgetter('nwdelta'), reverse=top)

    def economy(self):
        self.update_ops(current_player_id)
        return Economy(self.dominion(current_player_id))

    def award_stats(self):
        # self.update_town_crier()
        return AwardStats(self._db)
