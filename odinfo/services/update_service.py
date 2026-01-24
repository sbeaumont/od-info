"""
Update service for synchronizing data from OpenDominion.

This service handles all operations that fetch data from the OpenDominion website
and update the local database. It centralizes update logic that was previously
spread across the facade.

Design principles:
- Single Responsibility: Only handles data synchronization from OpenDominion
- Dependency Injection: Receives repository and session provider, doesn't create them
- Separation of Concerns: Keeps update logic separate from query logic and presentation
"""

import logging
from typing import Callable

import requests

from odinfo.config import Config
from odinfo.repositories.game import GameRepository
from odinfo.opsdata.ops import grab_ops, grab_my_ops, get_last_scans
from odinfo.opsdata.updater import update_ops, update_town_crier, update_dom_index

logger = logging.getLogger('od-info.update_service')


class UpdateService:
    """
    Service for updating local data from OpenDominion.

    This service encapsulates all operations that:
    1. Fetch data from the OpenDominion website
    2. Parse and transform the data
    3. Store it in the local database

    It does not handle caching - that responsibility remains with the facade
    which coordinates between services and manages cross-cutting concerns.
    """

    def __init__(self, config: Config, repo: GameRepository, session_provider: Callable[[], requests.Session]):
        """
        Create the update service.

        Args:
            config: Application configuration.
            repo: Database repository for storing updates.
            session_provider: Callable that returns an authenticated requests.Session
                             for the OpenDominion website. Using a callable allows
                             lazy initialization of the session.
        """
        self._config = config
        self._repo = repo
        self._session_provider = session_provider

    @property
    def _od_session(self) -> requests.Session:
        """Get the OpenDominion session (lazily initialized via provider)."""
        return self._session_provider()

    def update_dom_index(self):
        """Update the dominion index from OpenDominion search page."""
        update_dom_index(self._od_session, self._repo)

    def update_ops(self, dom_code: int):
        """
        Update ops data for a single dominion.

        Fetches the latest intelligence data for the specified dominion
        from OpenDominion and stores it in the database.

        Args:
            dom_code: The dominion code to update.
        """
        logger.debug("Updating ops for dominion %s", dom_code)
        if int(dom_code) == int(self._config.current_player_id):
            ops = grab_my_ops(self._od_session)
        else:
            ops = grab_ops(self._od_session, dom_code)
        if ops:
            update_ops(ops, self._repo, dom_code)
        else:
            logger.warning(f"Can't get ops for dominion {dom_code}")

    def update_town_crier(self):
        """Update all Town Crier events from OpenDominion."""
        update_town_crier(self._od_session, self._repo)

    def update_realmies(self, realmie_codes: list[int]):
        """
        Update ops for all dominions in the player's realm.

        Args:
            realmie_codes: List of dominion codes for realm members.
        """
        for dom_code in realmie_codes:
            self.update_ops(dom_code)

    def update_all(self):
        """
        Update ops for all dominions that have newer scans available.

        Compares local data timestamps with the OP Center to find
        dominions with newer intelligence, then updates only those.
        """
        last_scans = get_last_scans(self._od_session)
        for dom in self._repo.all_dominions():
            domcode = dom.code
            if (domcode in last_scans) and (
                    (dom.last_op is None) or
                    (dom.last_op < last_scans[domcode])):
                self.update_ops(domcode)

    def initialize_if_empty(self):
        """
        Initialize the dominion index if the database is empty.

        Called during startup to ensure we have dominion data.
        """
        if self._repo.is_empty():
            self.update_dom_index()