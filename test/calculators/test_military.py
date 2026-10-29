import unittest
from datetime import datetime, timedelta

from odinfo.calculators.military import MilitaryCalculator
from odinfo.domain.models import ClearSight, Dominion, DominionHistory
from odinfo.domain.refdata import Spells
from odinfo.repositories.game import GameRepository
from odinfo.services.military_service import MilitaryService
from test.fixtures import create_db_session, init_db

NOW = datetime(2026, 10, 28, 12, 0, 0)


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

    def test_arrived_training_leaves_out_units_arrived_by_from_tick(self):
        mc = MilitaryCalculator(self.dom)
        self.assertEqual({'unit3': 199}, mc.arrived_training_units(self.dom.last_barracks, 10))
        self.assertEqual({'unit3': 99}, mc.arrived_training_units(self.dom.last_barracks, 10, from_tick=5))

    def test_current_strength_starts_from_a_newer_cs(self):
        bs = self.dom.last_barracks
        self.dom.last_cs.timestamp = bs.timestamp + timedelta(hours=9)
        bs.home_unit3 = 0
        mc = MilitaryCalculator(self.dom)

        _, current_dp, confidence = MilitaryService(GameRepository(self.session)).calculate_current_strength(self.dom)

        self.assertEqual(mc.paid_dp, current_dp)
        self.assertEqual('locked', confidence)

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


class EstimatedDPTestCase(unittest.TestCase):
    """DP estimated from NW, for a Dark Elf: Gargoyle 0/3 at 5 NW gives the best 0.6 DP per NW."""

    def setUp(self):
        self.session = create_db_session()
        self.addCleanup(self.session.close)
        self.dom = Dominion(code=1, name="Dominion", realm=3, race="Dark Elf")
        self.session.add(self.dom)

    def add_history(self, hours_ago, land, networth):
        self.dom.history.append(DominionHistory(land=land, networth=networth,
                                                timestamp=NOW - timedelta(hours=hours_ago)))
        self.session.commit()

    def add_cs(self, hours_ago, draftees, land=1000, networth=50000):
        self.dom.clear_sight.append(ClearSight(land=land, peasants=0, networth=networth, prestige=250,
                                               resource_platinum=0, military_draftees=draftees,
                                               timestamp=NOW - timedelta(hours=hours_ago)))
        self.session.commit()

    def test_unit_networth(self):
        units = MilitaryCalculator(self.dom).race.units
        self.assertEqual([5, 5, 12, 13], [units[i].networth for i in range(1, 5)])

    def test_without_ops_all_networth_above_land_counts_as_dp(self):
        self.add_history(0, 1000, 55000)
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(round(18000 * (1 + mc.defense_bonus)), mc.estimated_dp)

    def test_networth_growth_since_the_ops_counts_as_dp(self):
        self.add_history(3, 1000, 50000)
        self.add_cs(2, 1000)
        self.add_history(0, 1010, 52000)
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(round((1000 + 1750 * 0.6) * (1 + mc.defense_bonus)), mc.estimated_dp)

    def test_growth_since_a_cs_older_than_the_history(self):
        self.add_cs(72, 1000, land=900, networth=40000)
        self.add_history(0, 1000, 70000)
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(round((1000 + 27500 * 0.6) * (1 + mc.defense_bonus)), mc.estimated_dp)

    def test_networth_drop_keeps_the_dp_of_the_ops(self):
        self.add_history(3, 1000, 50000)
        self.add_cs(2, 1000)
        self.add_history(0, 1000, 45000)
        mc = MilitaryCalculator(self.dom)
        self.assertEqual(mc.paid_dp, mc.estimated_dp)


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
