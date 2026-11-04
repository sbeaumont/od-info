import unittest
from dataclasses import replace

from odinfo.calculators.threats import Battlefield, contenders_at, safe_send, threats_to
from odinfo.domain.domainhelper import in_range, range_limit
from odinfo.domain.models import ClearSight, Dominion, DominionHistory
from odinfo.timeutils import current_od_time
from test.fixtures import create_db_session

MIN_RANGE = 75
MAX_RANGE = 250
MAX_TRIGGERS = 2


def make_dominion(session, code: int, realm: int, land: int, miners: int = 0, warriors: int = 0) -> Dominion:
    """A Dwarf dominion with only a CS, so its military is the same at every tick."""
    timestamp = current_od_time()
    dom = Dominion(code=code, name=f'Dom {code}', realm=realm, race='Dwarf')
    session.add(dom)
    dom.history.append(DominionHistory(land=land, networth=land * 40, timestamp=timestamp))
    dom.clear_sight.append(ClearSight(
        land=land, peasants=0, networth=land * 40, prestige=0,
        resource_platinum=0, resource_food=0, resource_lumber=0, resource_mana=0, resource_ore=0,
        resource_gems=0, resource_boats=0,
        military_draftees=0, military_unit1=0, military_unit2=miners, military_unit3=0, military_unit4=warriors,
        military_spies=0, military_assassins=0, military_wizards=0, military_archmages=0,
        timestamp=timestamp))
    return dom


class ThreatsTestCase(unittest.TestCase):
    def setUp(self):
        self.session = create_db_session()

    def contenders(self, *doms):
        self.session.flush()
        return {c.code: c for c in contenders_at(list(doms), 0, {})}

    @staticmethod
    def strike(attacker, defender, contenders):
        return Battlefield(list(contenders.values()), MIN_RANGE, MAX_RANGE, MAX_TRIGGERS).strike(attacker, defender)

    def test_range_runs_from_the_minimum_to_the_maximum(self):
        self.assertTrue(in_range(75, 100, MIN_RANGE, MAX_RANGE))
        self.assertTrue(in_range(250, 100, MIN_RANGE, MAX_RANGE))
        self.assertFalse(in_range(74, 100, MIN_RANGE, MAX_RANGE))
        self.assertFalse(in_range(251, 100, MIN_RANGE, MAX_RANGE))

    def test_the_range_limit_is_the_smallest_land_in_range(self):
        self.assertEqual(751, range_limit(1001, MIN_RANGE))
        self.assertTrue(in_range(751, 1001, MIN_RANGE, MAX_RANGE))
        self.assertFalse(in_range(750, 1001, MIN_RANGE, MAX_RANGE))
        self.assertEqual(750, range_limit(1000, MIN_RANGE))

    def test_threats_are_other_realms_with_the_attacker_in_range_strongest_first(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, warriors=1000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=1000),
            make_dominion(self.session, 3, realm=3, land=1000, warriors=3000, miners=3000),
            make_dominion(self.session, 4, realm=1, land=1000, warriors=9000, miners=9000),
            make_dominion(self.session, 5, realm=3, land=2000, warriors=9000, miners=9000))

        threats = threats_to(c[1], list(c.values()), MIN_RANGE, MAX_RANGE)

        self.assertEqual([3, 2], [threat.code for threat, _ in threats])

    def test_safe_send_keeps_home_dp_above_the_threat(self):
        c = self.contenders(make_dominion(self.session, 1, realm=1, land=1000, warriors=10000, miners=5000))
        attacker = c[1]
        five_four_op = attacker.mc.five_over_four[0]

        self.assertEqual(five_four_op, safe_send(attacker, 0))
        self.assertLess(safe_send(attacker, round(attacker.mc.five_over_four[1] * 1.2)), five_four_op)
        self.assertEqual(0, safe_send(attacker, attacker.mc.dp))

    def test_safe_send_breaks_the_defender_now(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, miners=5000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=10000, miners=10000))

        result = self.strike(c[2], c[1], c)

        self.assertGreater(result.safe_send_margin, 0)
        self.assertEqual([], result.triggers)

    def test_a_threat_holds_the_attacker_back_until_it_sends(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, miners=12000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=10000, miners=10000),
            make_dominion(self.session, 3, realm=3, land=1000, warriors=14000, miners=30000))

        result = self.strike(c[2], c[1], c)

        self.assertLessEqual(result.safe_send_margin, 0)
        self.assertGreater(result.five_four_margin, 0)
        self.assertEqual([3], [t.code for t in result.triggers])
        self.assertTrue(result.triggers[0].free)
        self.assertEqual(result.defender_dp, result.triggered_dp)
        self.assertGreater(result.triggered_margin, 0)

    def test_only_threats_that_break_a_full_send_hold_the_attacker_back(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, miners=12000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=10000, miners=10000),
            make_dominion(self.session, 3, realm=3, land=1000, warriors=14000, miners=30000),
            make_dominion(self.session, 4, realm=4, land=1000, warriors=100, miners=1000))

        result = self.strike(c[2], c[1], c)

        self.assertEqual([3], result.held_by)

    def test_a_chain_longer_than_the_maximum_gives_no_triggers(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, miners=12000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=10000, miners=10000),
            *[make_dominion(self.session, code, realm=code, land=1000, warriors=14000, miners=30000)
              for code in (3, 4, 5)])
        contenders = list(c.values())

        capped = Battlefield(contenders, MIN_RANGE, MAX_RANGE, 2).strike(c[2], c[1])
        uncapped = Battlefield(contenders, MIN_RANGE, MAX_RANGE, 3).strike(c[2], c[1])

        self.assertEqual([], capped.triggers)
        self.assertIsNone(capped.triggered_margin)
        self.assertGreater(capped.five_four_margin, 0)
        self.assertEqual(3, len(uncapped.triggers))

    def test_a_defender_that_sends_keeps_only_its_home_dp(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, warriors=14000, miners=6000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=10000, miners=10000))
        defender = c[1]

        result = self.strike(c[2], defender, c)

        self.assertEqual([1], result.held_by)
        self.assertLessEqual(result.five_four_margin, 0)
        self.assertEqual([1], [t.code for t in result.triggers])
        self.assertEqual(defender.mc.five_over_four[1], result.triggered_dp)
        self.assertGreater(result.triggered_margin, 0)

    def test_a_defender_that_already_sent_keeps_its_home_dp_and_holds_no_one_back(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, warriors=14000, miners=6000),
            make_dominion(self.session, 2, realm=2, land=1000, warriors=10000, miners=10000))
        c[1] = replace(c[1], home_dp=c[1].mc.five_over_four[1])

        result = self.strike(c[2], c[1], c)

        self.assertEqual([], result.held_by)
        self.assertEqual(c[1].home_dp, result.defender_dp)
        self.assertGreater(result.safe_send_margin, 0)

    def test_a_5_4_send_under_the_lowest_dp_of_the_defender_skips_the_safe_send(self):
        c = self.contenders(make_dominion(self.session, 1, realm=1, land=1000, miners=5000),
                            make_dominion(self.session, 2, realm=2, land=1000, warriors=100, miners=5000))
        strike = self.strike(c[2], c[1], c)
        self.assertIsNone(strike.safe_send_op)
        self.assertEqual([], strike.triggers)

    def test_strikes_out_of_range_come_from_other_realms_with_the_defender_below_their_range(self):
        c = self.contenders(make_dominion(self.session, 1, realm=1, land=700, miners=5000),
                            make_dominion(self.session, 2, realm=2, land=1000, warriors=100),
                            make_dominion(self.session, 3, realm=2, land=900, warriors=100),
                            make_dominion(self.session, 4, realm=1, land=1000, warriors=100))
        battlefield = Battlefield(list(c.values()), MIN_RANGE, MAX_RANGE, MAX_TRIGGERS)
        self.assertEqual([2], [strike.attacker for strike in battlefield.strikes_out_of_range(c[1])])

    def test_strikes_come_from_other_realms_in_range(self):
        c = self.contenders(
            make_dominion(self.session, 1, realm=1, land=1000, miners=5000),
            make_dominion(self.session, 2, realm=1, land=1000, warriors=1000),
            make_dominion(self.session, 3, realm=2, land=1000, warriors=1000),
            make_dominion(self.session, 4, realm=2, land=300, warriors=1000))

        strikes = Battlefield(list(c.values()), MIN_RANGE, MAX_RANGE, MAX_TRIGGERS).strikes_on(c[1])

        self.assertEqual([3], [s.attacker for s in strikes])


if __name__ == '__main__':
    unittest.main()
