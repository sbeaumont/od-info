"""
OpenDominion session management.

Handles authentication and session lifecycle for communicating with the OpenDominion website.
"""

import logging
import requests
from bs4 import BeautifulSoup

from odinfo.config import Config, LOGIN_URL, SELECT_URL

logger = logging.getLogger('od-info.session')


class ODSession:
    """Manages an authenticated session with the OpenDominion website."""

    def __init__(self, config: Config, player_id: int | None = None):
        """
        Create a new session manager.

        Args:
            config: Application configuration with credentials.
            player_id: If provided, switch to this dominion after login.
                      If None, uses config.current_player_id.
        """
        self._session: requests.Session | None = None
        self._config = config
        self._player_id = player_id if player_id is not None else config.current_player_id

    @property
    def session(self) -> requests.Session:
        """Get the authenticated session, logging in if necessary."""
        if self._session is None:
            self._session = self._login()
        return self._session

    def _login(self) -> requests.Session:
        """Perform login and return authenticated session."""
        session = requests.session()
        session.auth = (self._config.username, self._config.password)

        soup = self._get_soup(session, LOGIN_URL)
        csrf_token = self._pull_csrf_token(soup)

        payload = {
            '_token': csrf_token,
            'email': self._config.username,
            'password': self._config.password
        }
        response = session.post(LOGIN_URL, data=payload)

        if response.status_code != 200:
            raise ConnectionError(f"Login failed: HTTP {response.status_code}")

        if self._player_id:
            soup = BeautifulSoup(response.content, "html.parser")
            csrf_token = self._pull_csrf_token(soup)
            response = self._select_dominion(session, csrf_token, self._player_id)
            if response.status_code != 200:
                raise ConnectionError(f"Could not switch to dominion {self._player_id}")

        logger.debug("Successfully logged in to OpenDominion")
        return session

    def _select_dominion(self, session: requests.Session, csrf_token: str, player_id: int) -> requests.Response:
        """Switch to a specific dominion."""
        payload = {'_token': csrf_token}
        return session.post(SELECT_URL.format(str(player_id)), data=payload)

    def _get_soup(self, session: requests.Session, url: str) -> BeautifulSoup:
        """Fetch a page and return parsed HTML."""
        response = session.get(url)
        if response.status_code >= 400:
            raise ConnectionError(f"Cannot reach OpenDominion: HTTP {response.status_code}")
        return BeautifulSoup(response.content, "html.parser")

    def _pull_csrf_token(self, soup: BeautifulSoup) -> str:
        """Extract CSRF token from page."""
        if soup is None:
            raise ConnectionError("Cannot update data: OpenDominion page did not load")
        csrf_element = soup.select_one('meta[name="csrf-token"]')
        if csrf_element is None:
            raise ConnectionError("Cannot update data: OpenDominion returned unexpected page content")
        return csrf_element['content']

    def close(self):
        """Close the session."""
        if self._session is not None:
            self._session.close()
            self._session = None
            logger.debug("Session closed")

    def __enter__(self):
        """Support context manager usage."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close session when exiting context."""
        self.close()
        return False