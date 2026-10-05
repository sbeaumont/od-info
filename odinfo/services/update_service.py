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
from odinfo.opsdata.ops import Ops
from odinfo.domain.models import BarracksSpy
from odinfo.domain.refdata import BUILD_TICKS
from odinfo.opsdata.updater import (update_ops, update_town_crier, reload_town_crier, update_dom_index,
                                    init_my_dominion, update_realms, update_barracks_archive)
from odinfo.timeutils import cleanup_timestamp
from odinfo.services.od_api import ODApi

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

    def __init__(self, config: Config, repo: GameRepository, session_provider: Callable[[], requests.Session],
                 api_provider: Callable[[], ODApi]):
        """
        Create the update service.

        Args:
            config: Application configuration.
            repo: Database repository for storing updates.
            session_provider: Callable that returns an authenticated requests.Session
                             for the OpenDominion website. Using a callable allows
                             lazy initialization of the session.
            api_provider: Callable that returns the OpenDominion API client.
        """
        self._config = config
        self._repo = repo
        self._session_provider = session_provider
        self._api_provider = api_provider

    @property
    def _od_session(self) -> requests.Session:
        """Get the OpenDominion session (lazily initialized via provider)."""
        return self._session_provider()

    @property
    def _od_api(self) -> ODApi:
        """Get the OpenDominion API client (lazily initialized via provider)."""
        return self._api_provider()

    def update_dom_index(self):
        """Update the dominion index from the OpenDominion API."""
        update_dom_index(self._od_api, self._repo)

    def update_ops(self, dom_code: int):
        """
        Update ops data for a single dominion.

        Fetches the latest intelligence data for the specified dominion
        from OpenDominion and stores it in the database.

        Args:
            dom_code: The dominion code to update.
        """
        logger.debug("Updating ops for dominion %s", dom_code)
        dom_code = int(dom_code)
        if self._repo.get_dominion(dom_code).realm == self._repo.get_my_dominion().realm:
            advisors = self._od_api.advisors()['dominions']
            if str(dom_code) not in advisors:
                logger.warning("Realmie %s does not share advisors, no ops to update", dom_code)
                return
            dom_ops = advisors[str(dom_code)]['ops']
        else:
            dom_ops = self._od_api.op_overview(dom_code)['dominion']['ops']
        update_ops(Ops(dom_ops, dom_code), self._repo, dom_code)

    def update_realms(self):
        """Update the wonders and wars from the OpenDominion API."""
        update_realms(self._od_api, self._repo)

    def update_town_crier(self):
        """Add the new Town Crier events from the OpenDominion API."""
        update_town_crier(self._od_api, self._repo)

    def reload_town_crier(self):
        """Replace all Town Crier events with every page scraped from OpenDominion."""
        reload_town_crier(self._od_session, self._repo)

    def update_realmies(self):
        """Update ops for my dominion and every realmie who shares advisors."""
        for code, dom in self._od_api.advisors()['dominions'].items():
            update_ops(Ops(dom['ops'], int(code)), self._repo, int(code))

    def update_all(self):
        """Update ops for every dominion in the OP Center of my realm, with the BS archive on a new BS."""
        for code, dom in self._od_api.op_center()['dominions'].items():
            dom_code = int(code)
            barracks_spy = dom['ops']['barracks_spy']
            new_barracks_spy = barracks_spy is not None and not self._repo.session.get(
                BarracksSpy, [dom_code, cleanup_timestamp(barracks_spy['created_at'])])
            update_ops(Ops(dom['ops'], dom_code), self._repo, dom_code)
            if new_barracks_spy:
                update_barracks_archive(self._od_api, self._repo, dom_code, max_age_hours=BUILD_TICKS)

    def initialize_if_empty(self):
        """
        Initialize the dominion index if the database is empty.

        Called during startup to ensure we have dominion data.
        """
        if self._repo.get_my_dominion() is None:
            init_my_dominion(self._od_api, self._repo)
        if self._repo.is_empty():
            self.update_dom_index()