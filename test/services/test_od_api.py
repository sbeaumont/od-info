import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from odinfo.config import API_BASE
from odinfo.services.od_api import ODApi, ODApiError, _Pacer


def response(status: int, body: dict | list | None = None, headers: dict | None = None, text: str = '') -> Mock:
    headers = headers or {}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    return Mock(status_code=status, ok=status < 400, headers=headers, text=text, json=Mock(return_value=body))


def rate_limited(retry_after: int) -> Mock:
    return response(429, {'error': 'rate_limited', 'message': ''}, headers={'Retry-After': str(retry_after)})


class ODApiTest(unittest.TestCase):
    def setUp(self):
        self.clock = 0.0
        self.sleeps = []
        for target, fake in [('odinfo.services.od_api.time.monotonic', lambda: self.clock),
                             ('odinfo.services.od_api.time.sleep', self.sleep),
                             ('odinfo.services.od_api._pacer', _Pacer(1.0))]:
            patcher = patch(target, fake)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.waits = []
        self.api = ODApi('the-key', on_wait=self.waits.append)
        self.api._session.get = Mock()

    def sleep(self, seconds: float):
        self.sleeps.append(seconds)
        self.clock += seconds

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

    def test_spaces_requests_one_second_apart(self):
        self.api._session.get.return_value = response(200, [])
        self.api.rounds()
        self.clock += 0.25
        self.api.rounds()
        self.assertEqual([0.75], self.sleeps)

    def test_waits_on_the_rate_limit_and_tells_the_user(self):
        self.api._session.get.side_effect = [rate_limited(37), response(200, [])]
        self.assertEqual([], self.api.rounds())
        self.assertEqual([37], self.sleeps)
        self.assertEqual(["OpenDominion API rate limit reached, waiting 37 s"], self.waits)

    def test_retries_until_the_rate_limit_lets_the_request_through(self):
        self.api._session.get.side_effect = [rate_limited(5), rate_limited(3), response(200, [])]
        self.assertEqual([], self.api.rounds())
        self.assertEqual([5, 3], self.sleeps)
        self.assertEqual(3, self.api._session.get.call_count)

    def test_events_since_is_utc_iso(self):
        self.api._session.get.return_value = response(200, [])
        self.api.events(77, since=datetime(2026, 10, 4, 20, 46, 53))
        self.api._session.get.assert_called_once_with(f'{API_BASE}/rounds/77/events',
                                                      params={'since': '2026-10-04T20:46:53Z', 'limit': 500})


if __name__ == '__main__':
    unittest.main()