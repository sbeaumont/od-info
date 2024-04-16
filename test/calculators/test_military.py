import unittest

from calculators.military import MilitaryCalculator
from domain.models import Dominion
from test.fixtures import create_db_session, init_db


class MilitaryCalculatorTestCase(unittest.TestCase):
    def setUp(self):
        self.session = create_db_session()
        init_db(self.session)
        self.dom = self.session.get(Dominion, 1)

    def test_five_over_four(self):
        bs = self.dom.last_barracks
        bs.draftees = 1
        bs.unit1 = 1
        bs.unit2 = 1
        bs.unit3 = 1
        bs.unit4 = 1

        cs = self.dom.last_cs
        cs.military_draftees = 1
        cs.military_unit1 = 1
        cs.military_unit2 = 1
        cs.military_unit3 = 1
        cs.military_unit4 = 1

        mc = MilitaryCalculator(self.dom)
        fnork = mc.dp
        print(mc.raw_op, mc.op, mc.offense_bonus)
        print(mc.raw_dp, mc.dp, mc.defense_bonus)
        print(mc.flex_unit)
        print([str(unit) for unit in mc.race.units.values()])

        self.assertEqual(14, mc.op)
        self.assertEqual(11.55, mc.dp)
        self.assertEqual(mc.five_over_four, (100, 100))


if __name__ == '__main__':
    unittest.main()
