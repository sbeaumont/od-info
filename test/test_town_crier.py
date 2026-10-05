import unittest
from datetime import datetime
from unittest.mock import Mock

from bs4 import BeautifulSoup

from odinfo.domain.models import MyDominion, TownCrier
from odinfo.facade.towncrier import _parse_event_row
from odinfo.opsdata.updater import town_crier_event, update_town_crier
from odinfo.repositories.game import GameRepository
from odinfo.services.od_api import EVENT_LIMIT
from test.fixtures import create_db_session


def event(event_type: str, data: dict, created_at='2026-10-04T20:46:53Z', **fields) -> dict:
    result = {'id': 'bb0541f0', 'type': event_type, 'source_type': 'dominion', 'source_id': 17633,
              'source_name': 'Attacker', 'source_realm_number': 5, 'target_type': 'dominion', 'target_id': 17767,
              'target_name': 'Defender', 'target_realm_number': 0, 'data': data, 'created_at': created_at}
    result.update(fields)
    return result


INVASION = event('invasion', {'success': True, 'land_lost': 23, 'land_gained': 46})
BOUNCE = event('invasion', {'success': False, 'land_lost': 0, 'land_gained': 0})


class TownCrierEventTest(unittest.TestCase):
    def test_invasion_stores_the_land_taken_from_the_defender(self):
        tc = town_crier_event(INVASION)
        self.assertEqual((datetime(2026, 10, 4, 20, 46, 53), 'invasion', 17633, 'Attacker', 17767, 'Defender', 23),
                         (tc.timestamp, tc.event_type, tc.origin, tc.origin_name, tc.target, tc.target_name,
                          tc.amount))

    def test_bounce_has_the_attacker_as_origin(self):
        tc = town_crier_event(BOUNCE)
        self.assertEqual(('bounce', 17633, 17767, 0), (tc.event_type, tc.origin, tc.target, tc.amount))

    def test_war_uses_realm_numbers(self):
        tc = town_crier_event(event('war_declared', {'source_realm': {'number': 3, 'name': 'Aggressors'},
                                                     'target_realm': {'number': 7, 'name': 'Defenders'}},
                                    source_type='realm', source_id=56, target_type='realm_war', target_id=9))
        self.assertEqual(('war_declare', 3, 'Aggressors', 7, 'Defenders'),
                         (tc.event_type, tc.origin, tc.origin_name, tc.target, tc.target_name))

    def test_abandon_has_the_realm_as_target(self):
        tc = town_crier_event(event('abandoned', {}, target_type=None, target_id=None, target_name=None))
        self.assertEqual(('abandon', 17633, 5), (tc.event_type, tc.origin, tc.target))

    def test_neutral_wonder_attack_has_no_target(self):
        tc = town_crier_event(event('wonder_attacked', {'neutral': True, 'wonder': None, 'realm_number': None},
                                    target_type='round_wonder', target_id=None, target_name=None))
        self.assertEqual(('wonder_attack', 17633, None, None), (tc.event_type, tc.origin, tc.target, tc.target_name))

    def test_raid_has_the_tactic_as_target_name(self):
        tc = town_crier_event(event('raid_attacked', {'tactic': 'Storm the Gates'},
                                    target_type='raid_tactic', target_id=12, target_name=None))
        self.assertEqual(('raid_attack', None, 'Storm the Gates'), (tc.event_type, tc.target, tc.target_name))

    def test_wonder_spawn_names_the_wonder(self):
        tc = town_crier_event(event('wonder_spawned', {'wonder': 'Ivory Tower'}, source_type='round_wonder',
                                    source_id=3, source_name=None, target_type='round_wonder', target_id=3,
                                    target_name=None))
        self.assertEqual(('wonder_spawn', None, None, 'Ivory Tower'),
                         (tc.event_type, tc.origin, tc.target, tc.target_name))


class ScrapedTownCrierTest(unittest.TestCase):
    def test_wonder_spawn_is_recognised(self):
        row = BeautifulSoup(
            '<tr><td><span>2026-10-04 12:00:00</span></td><td>A new Wonder of the World has been discovered, the '
            '<a href="https://www.opendominion.net/dominion/wonders"><span class="text-orange">Ivory Tower</span></a>!'
            '</td></tr>', 'html.parser').tr
        timestamp, event_type, origin, origin_name, target, target_name, amount, _ = _parse_event_row(row)
        self.assertEqual(('wonder_spawn', '', '', 'Ivory Tower'), (event_type, origin, target, target_name))


class UpdateTownCrierTest(unittest.TestCase):
    def setUp(self):
        self.repo = GameRepository(create_db_session())
        self.repo.session.add(MyDominion(code=17641, realm=4, round_id=77,
                                         round_start=datetime(2026, 10, 4), round_duration_days=12))
        self.repo.session.commit()
        self.api = Mock()

    def test_first_update_asks_for_everything(self):
        self.api.events.return_value = [INVASION]
        update_town_crier(self.api, self.repo)
        self.api.events.assert_called_once_with(77, since=None)
        self.assertEqual(1, self.repo.session.query(TownCrier).count())

    def test_next_update_asks_since_the_newest_and_skips_known_events(self):
        self.api.events.return_value = [INVASION]
        update_town_crier(self.api, self.repo)
        later = event('invasion', {'success': True, 'land_lost': 10, 'land_gained': 20},
                      created_at='2026-10-04T21:10:00Z', source_id=1)
        self.api.events.return_value = [later, INVASION]
        update_town_crier(self.api, self.repo)
        self.api.events.assert_called_with(77, since=datetime(2026, 10, 4, 20, 46, 53))
        self.assertEqual(2, self.repo.session.query(TownCrier).count())

    def test_warns_when_the_api_returns_the_maximum(self):
        self.api.events.return_value = [
            event('invasion', {'success': True, 'land_lost': 1, 'land_gained': 2}, source_id=n)
            for n in range(EVENT_LIMIT)]
        with self.assertLogs('od-info.updater', level='WARNING'):
            update_town_crier(self.api, self.repo)
        self.assertEqual(EVENT_LIMIT, self.repo.session.query(TownCrier).count())


if __name__ == '__main__':
    unittest.main()