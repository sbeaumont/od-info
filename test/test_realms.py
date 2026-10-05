import unittest
from datetime import datetime
from unittest.mock import Mock

from odinfo.domain.models import MyDominion, Wonder, War
from odinfo.opsdata.updater import update_realms
from odinfo.repositories.game import GameRepository
from test.fixtures import create_db_session


def war(direction: str, realm_number: int, realm_name: str) -> dict:
    return {'direction': direction, 'realm_number': realm_number, 'realm_name': realm_name, 'status': 'active',
            'declared_at': '2026-09-29T10:00:00Z', 'active_at': '2026-09-30T10:00:00Z', 'inactive_at': None}


REALMS = [
    {'number': 3, 'name': 'Aggressors', 'wonders': [],
     'wars': [war('outgoing', 7, 'Defenders'), war('incoming', 7, 'Defenders')]},
    {'number': 7, 'name': 'Defenders',
     'wonders': [{'key': 'high_clerics_tower', 'name': "High Cleric's Tower", 'power': 230000,
                  'max_power': 250000, 'power_is_approximate': True}],
     'wars': [war('incoming', 3, 'Aggressors'), war('outgoing', 3, 'Aggressors')]},
    {'number': 9, 'name': 'Bystanders', 'wonders': [], 'wars': [war('outgoing', 3, 'Aggressors')]},
]


class UpdateRealmsTest(unittest.TestCase):
    def setUp(self):
        self.repo = GameRepository(create_db_session())
        self.repo.session.add(MyDominion(code=17641, realm=4, round_id=77,
                                         round_start=datetime(2026, 10, 4), round_duration_days=12))
        self.repo.session.commit()
        self.api = Mock(realms=Mock(return_value=REALMS))

    def test_stores_each_wonder_with_its_realm(self):
        update_realms(self.api, self.repo)
        self.api.realms.assert_called_once_with(77)
        wonder = self.repo.session.get(Wonder, 'high_clerics_tower')
        self.assertEqual((7, "High Cleric's Tower", 230000, 250000, True),
                         (wonder.realm, wonder.name, wonder.power, wonder.max_power, wonder.power_is_approximate))

    def test_stores_one_row_per_declaration(self):
        update_realms(self.api, self.repo)
        declarations = {(w.realm, w.target_realm) for w in self.repo.session.query(War)}
        self.assertEqual({(3, 7), (7, 3), (9, 3)}, declarations)
        war_row = self.repo.session.get(War, [3, 7])
        self.assertEqual(('Defenders', 'active', datetime(2026, 9, 29, 10), datetime(2026, 9, 30, 10), None),
                         (war_row.target_realm_name, war_row.status, war_row.declared_at, war_row.active_at,
                          war_row.inactive_at))

    def test_an_update_replaces_the_previous_state(self):
        update_realms(self.api, self.repo)
        self.api.realms.return_value = [{'number': 3, 'name': 'Aggressors', 'wonders': [], 'wars': []}]
        update_realms(self.api, self.repo)
        self.assertEqual(0, self.repo.session.query(Wonder).count())
        self.assertEqual(0, self.repo.session.query(War).count())


if __name__ == '__main__':
    unittest.main()