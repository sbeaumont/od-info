import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from odinfo.config import API_BASE
from odinfo.services.od_api import ODApi, ODApiError


def response(status: int, body: dict | list | None = None, headers: dict | None = None, text: str = '') -> Mock:
    headers = headers or {}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    return Mock(status_code=status, ok=status < 400, headers=headers, text=text, json=Mock(return_value=body))


class ODApiTest(unittest.TestCase):
    def setUp(self):
        self.waits = []
        self.api = ODApi('the-key', on_wait=self.waits.append)
        self.api._session.get = Mock()

    def test_sends_the_key(self):
        self.assertEqual('the-key', self.api._session.headers['X-API-Key'])

    def test_returns_the_json(self):
        self.api._session.get.return_value = response(200, {'id': 1})
        self.assertEqual({'id': 1}, self.api.me())
        self.api._session.get.assert_called_once_with(f'{API_BASE}/dominions/me', params={})

    def test_raises_the_api_error_code(self):
        self.api._session.get.return_value = response(422, {'error': 'same_realm', 'message': 'Realmie'})
        with self.assertRaises(ODApiError) as raised:
            self.api.op_overview(5)
        self.assertEqual(422, raised.exception.status)
        self.assertEqual('same_realm', raised.exception.code)

    def test_raises_on_an_error_without_json(self):
        self.api._session.get.return_value = response(502, text='<html>Bad Gateway</html>')
        with self.assertRaises(ODApiError) as raised:
            self.api.rounds()
        self.assertEqual('no_json', raised.exception.code)

    @patch('odinfo.services.od_api.time.sleep')
    def test_waits_once_on_the_rate_limit_and_tells_the_user(self, sleep):
        self.api._session.get.side_effect = [response(429, {'error': 'rate_limited', 'message': ''},
                                                      headers={'Retry-After': '37'}),
                                             response(200, [])]
        self.assertEqual([], self.api.rounds())
        sleep.assert_called_once_with(37)
        self.assertEqual(["OpenDominion API rate limit reached, waiting 37 s"], self.waits)

    @patch('odinfo.services.od_api.time.sleep')
    def test_raises_when_still_rate_limited_after_the_wait(self, sleep):
        limited = response(429, {'error': 'rate_limited', 'message': 'Slow down'}, headers={'Retry-After': '1'})
        self.api._session.get.side_effect = [limited, limited]
        with self.assertRaises(ODApiError) as raised:
            self.api.rounds()
        self.assertEqual('rate_limited', raised.exception.code)

    def test_events_since_is_utc_iso(self):
        self.api._session.get.return_value = response(200, [])
        self.api.events(77, since=datetime(2026, 10, 4, 20, 46, 53))
        self.api._session.get.assert_called_once_with(f'{API_BASE}/rounds/77/events',
                                                      params={'since': '2026-10-04T20:46:53Z', 'limit': 500})


if __name__ == '__main__':
    unittest.main()