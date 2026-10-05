"""
Client for the read-only OpenDominion JSON API.

See https://www.opendominion.net/api-docs for the endpoints.
"""

import logging
import time
from datetime import datetime
from typing import Callable

import requests

from odinfo.config import API_BASE, Config
from odinfo.exceptions import ODInfoException

logger = logging.getLogger('od-info.api')

EVENT_LIMIT = 500  # the maximum the events endpoint returns, newest first, without paging


class ODApiError(ODInfoException):
    """An error response from the OpenDominion API."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"OpenDominion API error {status} {code}: {message}",
                         {'status': status, 'code': code})
        self.status = status
        self.code = code


class ODApi:
    """Client for the OpenDominion API, authenticated with the API key of one dominion."""

    def __init__(self, api_key: str, on_wait: Callable[[str], None]):
        """
        Args:
            api_key: The key from the Settings page of the dominion.
            on_wait: Receives a message for the user before a wait for the rate limit.
        """
        self._session = requests.Session()
        self._session.headers['X-API-Key'] = api_key
        self._on_wait = on_wait

    def get(self, path: str, **params) -> dict | list:
        """GET an API path and return the decoded JSON. A parameter with value None is left out."""
        url = f'{API_BASE}{path}'
        response = self._session.get(url, params=params)
        if response.status_code == 429:
            seconds = int(response.headers['Retry-After'])
            self._on_wait(f"OpenDominion API rate limit reached, waiting {seconds} s")
            time.sleep(seconds)
            response = self._session.get(url, params=params)
        if not response.ok:
            raise self._error(response)
        logger.debug("GET %s %s", path, params)
        return response.json()

    @staticmethod
    def _error(response: requests.Response) -> ODApiError:
        if response.headers.get('Content-Type', '').startswith('application/json'):
            body = response.json()
            return ODApiError(response.status_code, body['error'], body['message'])
        return ODApiError(response.status_code, 'no_json', response.text[:200])

    def me(self) -> dict:
        """The dominion of the key, with its realm, the round, and the server time."""
        return self.get('/dominions/me')

    def rounds(self) -> list:
        """All rounds, newest first."""
        return self.get('/rounds')

    def dominions(self, round_id: int) -> list:
        """Every dominion in a round."""
        return self.get(f'/rounds/{round_id}/dominions')

    def realms(self, round_id: int) -> list:
        """Every realm in a round, with its wonders and wars."""
        return self.get(f'/rounds/{round_id}/realms')

    def events(self, round_id: int, since: datetime | None = None, limit: int = EVENT_LIMIT) -> list:
        """Town Crier events of a round, newest first, created at or after `since`."""
        since_param = since.strftime('%Y-%m-%dT%H:%M:%SZ') if since else None
        return self.get(f'/rounds/{round_id}/events', since=since_param, limit=limit)

    def advisors(self) -> dict:
        """Current data of the own dominion and of every realmie who shares advisors."""
        return self.get('/dominions/me/advisors')

    def op_center(self, max_age_hours: int = 0, realm: int | None = None) -> dict:
        """The latest op of each type on every dominion the realm targeted."""
        return self.get('/dominions/me/op-center', max_age_hours=max_age_hours, realm=realm)

    def op_overview(self, target: int, max_age_hours: int = 0) -> dict:
        """The latest op of each type on one dominion."""
        return self.get(f'/dominions/me/op-center/{target}', max_age_hours=max_age_hours)

    def op_archive(self, target: int, op_type: str, max_age_hours: int = 0, limit: int = 500) -> dict:
        """Every op of one type that the realm gathered on one dominion, newest first."""
        return self.get(f'/dominions/me/op-center/{target}/{op_type}', max_age_hours=max_age_hours, limit=limit)

    def close(self):
        """Close the HTTP session."""
        self._session.close()


def database_url(config: Config, on_wait: Callable[[str], None]) -> str:
    """The database URL: database_name from secret.txt, or one database per current round."""
    if config.database_name:
        return config.database_name
    od_api = ODApi(config.api_key, on_wait)
    od_round = od_api.me()['round']
    od_api.close()
    return f"sqlite:///odinfo-round-{od_round['number']}-id-{od_round['id']}.sqlite"