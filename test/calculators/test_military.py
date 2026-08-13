import unittest

from odinfo.calculators.military import MilitaryCalculator
from odinfo.domain.models import Dominion
from odinfo.domain.refdata import Spells
from test.fixtures import create_db_session, init_db


class MilitaryCalculatorTestCase(unittest.TestCase):
    def setUp(self):
        self.session = create_db_session()
        init_db(self.session)
        self.dom = self.session.get(Dominion, 1)

    def test_five_over_four(self):
        bs = self.dom.last_barracks
        bs.draftees = 10
        bs.home_unit1 = 10
        bs.home_unit2 = 10
        bs.home_unit3 = 10
        bs.home_unit4 = 10
        bs.training = {}  # Clear training data from fixtures

        cs = self.dom.last_cs
        cs.military_draftees = 10
        cs.military_unit1 = 10
        cs.military_unit2 = 10
        cs.military_unit3 = 10
        cs.military_unit4 = 10

        mc = MilitaryCalculator(self.dom)

        self.assertEqual(144, mc.paid_op)
        self.assertEqual(116, mc.paid_dp)
        self.assertEqual((107, 89), mc.five_over_four)

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


class BuildingBonusCapTestCase(unittest.TestCase):
    """The game caps all three building bonuses at 20% of land owned.

    A dominion that loses land to an invasion ends up over that ratio, so the cap
    is not just a theoretical case.
    """
    def setUp(self):
        self.session = create_db_session()
        init_db(self.session)
        self.dom = self.session.get(Dominion, 1)
        # 100 land in history, 20 more incoming, so 12 buildings is 10% and 30 is 25%.
        self.survey = self.dom.last_survey

    def test_gryphon_nest_bonus_below_the_cap(self):
        self.survey.gryphon_nest = 12
        self.assertAlmostEqual(0.16, MilitaryCalculator(self.dom).gryphon_nest_bonus)

    def test_gryphon_nest_bonus_caps_at_32_percent(self):
        self.survey.gryphon_nest = 30
        self.assertAlmostEqual(0.32, MilitaryCalculator(self.dom).gryphon_nest_bonus)

    def test_guard_tower_bonus_below_the_cap(self):
        self.survey.guard_tower = 12
        self.assertAlmostEqual(0.16, MilitaryCalculator(self.dom).guard_tower_bonus)

    def test_guard_tower_bonus_caps_at_32_percent(self):
        self.survey.guard_tower = 30
        self.assertAlmostEqual(0.32, MilitaryCalculator(self.dom).guard_tower_bonus)

    def test_temple_bonus_below_the_cap(self):
        self.survey.temple = 12
        self.assertAlmostEqual(0.135, MilitaryCalculator(self.dom).temple_bonus)

    def test_temple_bonus_caps_at_27_percent(self):
        self.survey.temple = 30
        self.assertAlmostEqual(0.27, MilitaryCalculator(self.dom).temple_bonus)


class TempleReductionTestCase(unittest.TestCase):
    """Temples come off the defender's DP multiplier, they don't scale their finished DP.

    The game does max(multiplier - reduction, 1), so how much a target's temples are
    worth depends on the DP bonus of whoever is being hit.
    """
    def setUp(self):
        self.session = create_db_session()
        init_db(self.session)
        self.dom = self.session.get(Dominion, 1)
        self.survey = self.dom.last_survey
        self.survey.temple = 30  # over the cap, so the reduction is a flat 27%

    def test_op_grossed_up_against_a_defence_bonus(self):
        # 10000 * 1.6 / (1.6 - 0.27)
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(12030, mc.op_with_temples(10000, 0.6))

    def test_a_bigger_defence_bonus_dilutes_the_temples(self):
        mc = MilitaryCalculator(self.dom)
        self.assertGreater(mc.op_with_temples(10000, 0.4), mc.op_with_temples(10000, 0.8))

    def test_temples_do_nothing_to_a_defender_without_bonuses(self):
        """The multiplier floors at 1, so there is nothing for the temples to take."""
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(10000, mc.op_with_temples(10000, 0))

    def test_a_defence_bonus_below_the_reduction_only_loses_what_it_has(self):
        # 10000 * 1.1 / max(1.1 - 0.27, 1)
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(11000, mc.op_with_temples(10000, 0.1))

    def test_a_negative_defence_bonus_is_rejected(self):
        mc = MilitaryCalculator(self.dom)
        with self.assertRaises(ValueError):
            mc.op_with_temples(10000, -0.1)


class SpellRaceKeyTestCase(unittest.TestCase):
    """The game names a race 'Dark Elf' where spells.yml keys it 'dark-elf'."""

    def test_race_name_with_a_space_finds_its_spell(self):
        self.assertEqual(1, Spells().value_for_perk('Dark Elf', 'ignore_draftees'))

    def test_single_word_race_finds_its_spell(self):
        self.assertEqual(10, Spells().value_for_perk('Kobold', 'offense'))

    def test_race_without_the_perk_gets_nothing(self):
        self.assertEqual(0, Spells().value_for_perk('Dwarf', 'offense'))


if __name__ == '__main__':
    unittest.main()
