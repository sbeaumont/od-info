import unittest
from datetime import timedelta
from types import SimpleNamespace

from odinfo.domain.domainhelper import Land
from odinfo.domain.models import Dominion, TownCrier
from odinfo.timeutils import current_od_time
from test.fixtures import create_db_session, init_db


class LandIncomingTest(unittest.TestCase):
    def land_spy(self, hours_ago: int) -> Land:
        data = SimpleNamespace(timestamp=current_od_time() - timedelta(hours=hours_ago),
                               incoming={'cavern': {'2': 9, '11': 10}, 'hill': {'12': 5}})
        return Land(None, data)

    def test_counts_all_incoming_of_a_fresh_land_spy(self):
        self.assertEqual(24, self.land_spy(0).incoming)

    def test_leaves_out_acres_that_arrived_since_the_land_spy(self):
        self.assertEqual(5, self.land_spy(11).incoming)

    def test_arriving_by_counts_acres_up_to_the_tick(self):
        land = self.land_spy(0)
        self.assertEqual(0, land.arriving_by(1))
        self.assertEqual(9, land.arriving_by(2))
        self.assertEqual(24, land.arriving_by(12))

    def test_arriving_by_counts_from_now_for_an_older_land_spy(self):
        land = self.land_spy(2)
        self.assertEqual(0, land.arriving_by(8))
        self.assertEqual(10, land.arriving_by(9))
        self.assertEqual(15, land.arriving_by(10))


class LandAtTickTest(unittest.TestCase):
    def setUp(self):
        self.session = create_db_session()
        init_db(self.session)
        self.dom = self.session.get(Dominion, 1)
        self.dom.last_land.timestamp = current_od_time()

    @staticmethod
    def invasion(hours_ago: int, land_lost: int) -> TownCrier:
        return TownCrier(origin=1, target=2, event_type='invasion', amount=land_lost,
                         timestamp=current_od_time() - timedelta(hours=hours_ago))

    def test_land_now_is_the_current_land(self):
        self.assertEqual(self.dom.current_land, self.dom.land_at(0, []))

    def test_land_at_a_tick_adds_the_acres_arrived_by_then(self):
        self.assertEqual(self.dom.current_land + 5, self.dom.land_at(11, []))
        self.assertEqual(self.dom.current_land + 20, self.dom.land_at(17, []))

    def test_land_without_ops_or_invasions_is_the_current_land(self):
        self.dom.land_spy.clear()
        self.assertEqual(self.dom.current_land, self.dom.land_at(12, []))

    def test_an_invasion_brings_double_the_land_lost_after_the_arrival_ticks(self):
        self.dom.land_spy.clear()
        invasions = [self.invasion(hours_ago=2, land_lost=10)]
        self.assertEqual(self.dom.current_land, self.dom.land_at(9, invasions))
        self.assertEqual(self.dom.current_land + 20, self.dom.land_at(10, invasions))

    def test_an_invasion_before_the_land_spy_is_in_the_land_spy(self):
        invasions = [self.invasion(hours_ago=2, land_lost=10)]
        self.assertEqual(self.dom.land_at(12, []), self.dom.land_at(12, invasions))

    def test_an_invasion_after_the_land_spy_adds_to_it(self):
        self.dom.last_land.timestamp = current_od_time() - timedelta(hours=5)
        invasions = [self.invasion(hours_ago=2, land_lost=10)]
        self.assertEqual(self.dom.land_at(12, []) + 20, self.dom.land_at(12, invasions))