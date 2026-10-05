import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from odinfo.domain.models import Dominion, DominionHistory, MyDominion
from odinfo.opsdata.updater import init_my_dominion, update_dom_index
from odinfo.repositories.game import GameRepository
from test.fixtures import create_db_session

ROUND_START = datetime(2026, 10, 4, 0, 0, 0)

ME = {
    'id': 17641,
    'name': 'Boom',
    'realm': {'id': 1176, 'number': 4, 'name': 'Magic'},
    'round': {'id': 77, 'number': 0, 'name': 'Test Round', 'start_date': '2026-10-04T00:00:00Z',
              'end_date': '2026-10-16T00:00:00Z', 'day': 1, 'hour': 21, 'duration_days': 12},
    'server_time': '2026-10-04T20:59:49Z',
}

DOMINIONS = [
    {'id': 17641, 'name': 'Boom', 'race': 'Dark Elf', 'realm_number': 4, 'realm_name': 'Magic',
     'land': 600, 'networth': 30000, 'in_protection': False, 'guard': None, 'locked': False, 'abandoned': False},
    {'id': 17690, 'name': 'Adijee', 'race': 'Orc', 'realm_number': 0, 'realm_name': 'The Graveyard',
     'land': 598, 'networth': 27940, 'in_protection': False, 'guard': None, 'locked': False, 'abandoned': False},
]


def my_dominion() -> MyDominion:
    return MyDominion(code=17641, realm=4, round_id=77, round_start=ROUND_START, round_duration_days=12)


class CurrentDayTest(unittest.TestCase):
    @patch('odinfo.domain.models.current_od_time')
    def test_counts_days_from_the_round_start(self, now):
        for moment, day in ((datetime(2026, 10, 4, 0, 0), 1),
                            (datetime(2026, 10, 4, 23, 59), 1),
                            (datetime(2026, 10, 5, 0, 0), 2),
                            (datetime(2026, 10, 15, 12, 0), 12)):
            with self.subTest(moment=moment):
                now.return_value = moment
                self.assertEqual(day, my_dominion().current_day)

    @patch('odinfo.domain.models.current_od_time', return_value=datetime(2026, 10, 3, 23, 0))
    def test_refuses_a_day_before_the_round_starts(self, now):
        with self.assertRaises(ValueError):
            _ = my_dominion().current_day


class DomIndexTest(unittest.TestCase):
    def setUp(self):
        self.repo = GameRepository(create_db_session())
        self.api = Mock(me=Mock(return_value=ME), dominions=Mock(return_value=DOMINIONS))

    def test_init_stores_my_dominion_and_round(self):
        init_my_dominion(self.api, self.repo)
        my_dom = self.repo.get_my_dominion()
        self.assertEqual((17641, 4, 77, ROUND_START, 12),
                         (my_dom.code, my_dom.realm, my_dom.round_id, my_dom.round_start, my_dom.round_duration_days))

    @patch('odinfo.opsdata.updater.current_od_time', return_value=datetime(2026, 10, 4, 21, 5, 0))
    def test_adds_new_dominions_and_a_history_row_for_each(self, now):
        self.repo.session.add(my_dominion())
        self.repo.session.commit()

        update_dom_index(self.api, self.repo)

        self.api.dominions.assert_called_with(77)
        doms = {d.code: d for d in self.repo.session.query(Dominion)}
        self.assertEqual({17641, 17690}, set(doms))
        self.assertEqual(('Adijee', 0, 'Orc'), (doms[17690].name, doms[17690].realm, doms[17690].race))
        history = self.repo.session.query(DominionHistory).filter_by(dominion_id=17690).all()
        self.assertEqual(1, len(history))
        self.assertEqual((datetime(2026, 10, 4, 21, 5, 0), 598, 27940),
                         (history[0].timestamp, history[0].land, history[0].networth))


if __name__ == '__main__':
    unittest.main()