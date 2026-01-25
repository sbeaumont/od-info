"""
Facade object to ensure that all "business and data logic" doesn't get mixed into user interface code.

This class is intentionally the smorgasbord of queries and actions that the UI (flask_app) needs
so that any ugliness is contained in this class.

The facade coordinates between services and handles cross-cutting concerns like caching.
Domain-specific operations are delegated to specialized services.
"""

import logging

from odinfo.calculators.military import MilitaryCalculator
from odinfo.calculators.networthcalculator import get_networth_deltas
from odinfo.config import Config, SEARCH_PAGE
from odinfo.repositories.game import GameRepository
from odinfo.domain.models import Dominion
from odinfo.timeutils import hours_since, add_duration, current_od_time
from odinfo.facade.awardstats import AwardStats
from odinfo.facade.cache import FacadeCache
from odinfo.opsdata.scrapetools import read_tick_time, get_soup_page
from odinfo.opsdata.updater import query_stealables
from odinfo.services.od_session import ODSession
from odinfo.services.military_service import MilitaryService
from odinfo.services.report_service import ReportService
from odinfo.services.update_service import UpdateService
from odinfoweb.viewmodels.overview import build_overview_list_vm
from odinfoweb.viewmodels.ratios import build_ratio_list_vm

logger = logging.getLogger('od-info.facade')


class ODInfoFacade(object):
    def __init__(self, config: Config, repo: GameRepository, cache: FacadeCache):
        self._config = config
        self._od_session = None
        self._repo = repo
        self._cache = cache
        self._update_service = UpdateService(config, repo, lambda: self.od_session)
        self._report_service = ReportService(repo)
        self._military_service = MilitaryService(repo)
        self._update_service.initialize_if_empty()

    def clear_cache(self):
        logger.debug("Cache cleared (had %d entries)", len(self._cache))
        self._cache.clear()

    def invalidate_cache(self, prefix: str):
        removed = self._cache.invalidate_prefix(prefix)
        logger.debug("Cache invalidated for prefix '%s' (%d entries removed)", prefix, removed)

    @property
    def od_session(self):
        """Session for OpenDominion website (not database)."""
        if not self._od_session:
            self._od_session = ODSession(self._config)
        return self._od_session.session

    def teardown(self):
        if self._od_session is not None:
            self._od_session.close()

    def update_all(self):
        """Update ops for all dominions that have newer scans available."""
        self._update_service.update_all()
        self.clear_cache()

    # ---------------------------------------- COMMANDS - Update from OpenDominion.net

    def update_dom_index(self):
        """Update the dominion index from OpenDominion search page."""
        self._update_service.update_dom_index()

    def update_ops(self, dom_code: int):
        """Update ops data for a single dominion."""
        self._update_service.update_ops(dom_code)

    def update_single_dom(self, dom_code: int):
        """Update ops for a single dominion and clear cache."""
        self._update_service.update_ops(dom_code)
        self.clear_cache()

    def update_town_crier(self):
        """Update all Town Crier events from OpenDominion."""
        self._update_service.update_town_crier()

    def update_realmies(self):
        """Update ops for all dominions in the player's realm."""
        self._update_service.update_realmies(self.realmie_codes())

    # ---------------------------------------- COMMANDS - Change directly

    def update_role(self, dom_code, role):
        logger.debug("Updating dominion %s role to %s", dom_code, role)
        self._repo.update_dominion_role(dom_code, role)
        self.invalidate_cache('dom_list')

    def update_player(self, dom_code, player_name):
        logger.debug("Updating dominion player of dominion %s to %s", dom_code, player_name)
        self._repo.update_dominion_player(dom_code, player_name)
        self.invalidate_cache('dom_list')

    # ---------------------------------------- COMMANDS - Send out information

    def send_top_bot_nw_to_discord(self):
        """Send networth change reports to Discord."""
        return self._report_service.send_top_bot_nw_to_discord()

    # ---------------------------------------- QUERIES - Single Dominion

    def dominion(self, dom_code):
        return self._repo.get_dominion(dom_code)

    def current_player_dominion(self) -> Dominion:
        """Get the current player's dominion."""
        return self._repo.get_dominion(self._config.current_player_id)

    def ops_age(self, dom: Dominion):
        return hours_since(dom.last_op)

    def dom_status(self, dom_code: int, update=False):
        """Get information of a specific dominion."""
        logger.debug("Getting dom status for %s", dom_code)
        if update:
            self.update_ops(dom_code)
        return self._repo.get_dominion(dom_code).last_cs

    def nw_history(self, dom_code):
        """Get the networth history of a specific dominion."""
        logger.debug("Getting NW history for %s", dom_code)
        return self._repo.get_dominion(dom_code).history

    # ---------------------------------------- QUERIES - Lists

    def dom_list(self, since='-12 hours'):
        """Get overview information of all dominions."""
        cache_key = f'dom_list_{since}'
        if cache_key in self._cache:
            logger.debug("Returning cached dom_list for %s", cache_key)
            return self._cache[cache_key]

        logger.debug("Computing dom_list for %s", cache_key)
        dominions = list(self._repo.all_dominions())
        nw_deltas = get_networth_deltas(self._repo)
        result = build_overview_list_vm(dominions, nw_deltas)
        self._cache[cache_key] = result
        return result

    def get_town_crier(self):
        logger.debug("Getting Town Crier")
        return self._repo.all_town_crier_events()

    def ratio_list(self):
        """Overview of the ratios of all dominions."""
        cache_key = 'ratio_list'
        if cache_key in self._cache:
            logger.debug("Returning cached ratio_list")
            return self._cache[cache_key]

        logger.debug("Computing ratio_list")
        result = build_ratio_list_vm(list(self._repo.all_dominions()))
        self._cache[cache_key] = result
        return result

    def all_doms_ops_age(self):
        cache_key = 'all_doms_ops_age'
        if cache_key in self._cache:
            logger.debug("Returning cached all_doms_ops_age")
            return self._cache[cache_key]

        logger.debug("Computing all_doms_ops_age")
        result = {dom.code: hours_since(dom.last_op) for dom in self._repo.all_dominions()}
        self._cache[cache_key] = result
        return result

    def military_list(self, versus_op=0, top=20, include_current_strength=False):
        """Get military overview for top dominions."""
        cache_key = f'military_list_{versus_op}_{top}_{include_current_strength}'
        if cache_key in self._cache:
            logger.debug("Returning cached military_list for %s", cache_key)
            return self._cache[cache_key]

        current_day = self.current_tick.day
        result_list = self._military_service.military_list(
            current_day, versus_op, top, include_current_strength)
        self._cache[cache_key] = result_list
        return result_list

    def top_op(self, mil_calc_result: list):
        """Find the dominion with highest 5/4 OP from a military list."""
        return self._military_service.top_op(mil_calc_result)

    def current_strength(self, dom: Dominion) -> tuple[int | None, int | None, str | None]:
        """Get current strength (refined) for a single dominion."""
        mc = MilitaryCalculator(dom)
        return self._military_service.calculate_current_strength(mc)

    def realmie_codes(self) -> list[int]:
        logger.debug("Getting Realmies")
        return [dom.code for dom in self.realmies()]

    def realmies(self) -> list[Dominion]:
        logger.debug("Getting Realmies")
        return list(self._repo.get_realmies(self._config.current_player_id))

    def realmies_with_blops_info(self):
        """Get realmies with military calculator info including blops (boats)."""
        current_day = self.current_tick.day
        return self._military_service.realmies_with_blops_info(self.realmies(), current_day)

    def stealables(self) -> list:
        logger.debug("Listing stealables")
        since = add_duration(current_od_time(as_str=True), -12, True)
        result = query_stealables(self._repo, since, self._repo.get_realm_of_dominion(self._config.current_player_id))
        return result

    # ---------------------------------------- QUERIES - Utility

    def name_for_dom_code(self, domcode):
        """Get the name connected with a dominion code."""
        logger.debug("Getting name for %s", domcode)
        return self._repo.get_dominion(domcode).name

    @property
    def current_tick(self):
        soup = get_soup_page(self.od_session, SEARCH_PAGE)
        return read_tick_time(soup)

    # ---------------------------------------- QUERIES - Reports

    def get_unchanged_nw(self, top: int = 50):
        """Get dominions with unchanged networth."""
        return self._report_service.get_unchanged_nw(top)

    def get_top_bot_nw(self, top=True, filter_zeroes=False):
        """Get top or bottom networth changers."""
        return self._report_service.get_top_bot_nw(top, filter_zeroes)

    def award_stats(self):
        # self.update_town_crier()
        return AwardStats(self._repo.session)

    # ---------------------------------------- COMMANDS - Database Maintenance

    def cleanup_old_ops(self, hours: int = 72) -> dict[str, int]:
        """
        Delete ops older than specified hours.

        Preserves DominionHistory (for graphs) and TownCrier.
        Returns dict of table name -> deleted row count.
        """
        cutoff = add_duration(current_od_time(as_str=True), -hours, True)
        logger.info(f"Cleaning up ops older than {cutoff} ({hours} hours)")
        deleted = self._repo.cleanup_old_ops(cutoff)
        self.clear_cache()
        return deleted

    def get_ops_counts(self) -> dict[str, int]:
        """Get current row counts for all ops tables."""
        return self._repo.count_ops()
