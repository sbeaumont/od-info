import unittest
from datetime import timedelta

from odinfo.domain.models import Dominion
from test.fixtures import create_db_session, init_db


class MilitaryTestCase(unittest.TestCase):
    def setUp(self):
        self.session = create_db_session()
        init_db(self.session)
        self.dom = self.session.get(Dominion, 1)

    def test_arrived_training_leaves_out_units_arrived_by_from_tick(self):
        military = self.dom.military
        self.assertEqual({'unit3': 199}, military.arrived_training_units(self.dom.last_barracks, 10))
        self.assertEqual({'unit3': 99}, military.arrived_training_units(self.dom.last_barracks, 10, from_tick=5))

    def test_cs_in_the_same_tick_narrows_the_returning_units(self):
        bs = self.dom.last_barracks
        bs.home_unit4 = 331
        bs.returning = {'unit4': {'4': 4665}}
        self.dom.last_cs.military_unit4 = 5483

        home, returning, from_tick = self.dom.military.starting_point([bs])

        self.assertEqual(0, from_tick)
        self.assertAlmostEqual(331 * 0.85, home['unit4'][0])
        self.assertAlmostEqual(331 / 0.85, home['unit4'][1])
        self.assertAlmostEqual(5483 - 331 / 0.85, returning['unit4'][0])
        self.assertAlmostEqual(5483 - 331 * 0.85, returning['unit4'][1])

    def test_newer_cs_holds_the_units_still_away(self):
        bs = self.dom.last_barracks
        bs.returning = {'unit4': {'12': 50}}
        self.dom.last_cs.timestamp = bs.timestamp + timedelta(hours=9)
        self.dom.last_cs.military_unit4 = 60
        military = self.dom.military

        home, returning, from_tick = military.starting_point([bs])
        arrived = military.arrived_returning_units([bs], 12, from_tick, returning)

        self.assertEqual(9, from_tick)
        self.assertAlmostEqual(60, sum(home['unit4'][:2]) / 2 + sum(arrived['unit4'][:2]) / 2)


if __name__ == '__main__':
    unittest.main()