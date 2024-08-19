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
        bs.draftees = 10
        bs.unit1 = 10
        bs.unit2 = 10
        bs.unit3 = 10
        bs.unit4 = 10

        cs = self.dom.last_cs
        cs.military_draftees = 10
        cs.military_unit1 = 10
        cs.military_unit2 = 10
        cs.military_unit3 = 10
        cs.military_unit4 = 10

        mc = MilitaryCalculator(self.dom)
        fnork = mc.dp
        print(mc.raw_op, mc.op, mc.offense_bonus)
        print(mc.raw_dp, mc.dp, mc.defense_bonus)
        print(mc.flex_unit)
        print([str(unit) for unit in mc.race.units.values()])

        self.assertEqual(144, mc.op)
        self.assertEqual(116, mc.dp)
        self.assertEqual(mc.five_over_four, (122, 98))

    # def test_five_over_four_liz(self):
    #     bs = self.dom.last_barracks
    #     bs.draftees = 10
    #     bs.unit1 = 10
    #     bs.unit2 = 10
    #     bs.unit3 = 10
    #     bs.unit4 = 10
    #
    #     cs = self.dom.last_cs
    #     cs.military_draftees = 10
    #     cs.military_unit1 = 10
    #     cs.military_unit2 = 10
    #     cs.military_unit3 = 10
    #     cs.military_unit4 = 10
    #
    #     unit
    #     1
    #     693
    #     unit
    #     2
    #     3143
    #     unit
    #     3
    #     491
    #     unit
    #     4
    #     1905


if __name__ == '__main__':
    unittest.main()
