import unittest
from datetime import timedelta

from odinfo.calculators.threats import Strike, Trigger
from odinfo.domain.models import BarracksSpy, Dominion, DominionHistory, TownCrier
from odinfo.exceptions import ODInfoException
from odinfo.timeutils import current_od_time
from odinfoweb.viewmodels.threats import ThreatCellVM, ThreatRowVM, build_threats_vm, name_list, threat_cell
from test.calculators.test_threats import make_dominion
from test.fixtures import create_db_session

NAMES = {1: 'Defender', 2: 'Attacker', 3: 'Vex', 4: 'Kragg'}


def make_strike(five_four_op: int, safe_send_op: int, triggers=(), triggered_op=None, triggered_dp=None) -> Strike:
    return Strike(attacker=2, defender_dp=10000, five_four_op=five_four_op, safe_send_op=safe_send_op,
                  held_by=[3, 4], triggers=list(triggers), triggered_op=triggered_op, triggered_dp=triggered_dp)


class ThreatCellTest(unittest.TestCase):
    def test_safe_send_that_breaks_is_now(self):
        cell = threat_cell(make_strike(14000, 12000), NAMES)
        self.assertEqual(('now', 2000), (cell.status, cell.margin))

    def test_safe_send_after_triggers_is_triggered(self):
        cell = threat_cell(make_strike(14000, 9000, [Trigger(3, True)], 11000, 10000), NAMES)
        self.assertEqual(('triggered', 1000), (cell.status, cell.margin))
        self.assertIn('after Vex (free)', cell.tooltip)

    def test_only_a_5_4_send_that_breaks_is_five_four(self):
        cell = threat_cell(make_strike(14000, 9000), NAMES)
        self.assertEqual(('five_four', 4000), (cell.status, cell.margin))
        self.assertIn('held: Vex, Kragg', cell.tooltip)

    def test_no_send_that_breaks_is_none(self):
        cell = threat_cell(make_strike(9000, 8000), NAMES)
        self.assertEqual(('none', -1000), (cell.status, cell.margin))


class NameListTest(unittest.TestCase):
    def test_a_short_list_shows_every_name(self):
        self.assertEqual('A, B, C', name_list(['A', 'B', 'C']))

    def test_a_long_list_shows_three_names_and_the_rest_as_a_count(self):
        self.assertEqual('A, B, C +2 more', name_list(['A', 'B', 'C', 'D', 'E']))


class DefenderWithoutOpsTest(unittest.TestCase):
    def test_a_defender_without_a_military_gives_a_clear_error(self):
        session = create_db_session()
        defender = Dominion(code=1, name='No Advisors', realm=1, race='Dwarf')
        session.add(defender)
        defender.history.append(DominionHistory(land=1000, networth=40000, timestamp=current_od_time()))
        attacker = make_dominion(session, 2, realm=2, land=1000, warriors=1000)
        session.flush()

        with self.assertRaisesRegex(ODInfoException, 'No Advisors has no CS or BS'):
            build_threats_vm([defender, attacker], [], 1, 75, 250, 2, None)


class ArmyOutTest(unittest.TestCase):
    def test_the_tooltip_says_the_army_is_out_until_the_returning_units_arrive(self):
        session = create_db_session()
        defender = make_dominion(session, 1, realm=1, land=1000, miners=5000)
        attacker = make_dominion(session, 2, realm=2, land=1000, warriors=2000, miners=2000)
        attacker.barracks_spy.append(BarracksSpy(
            draftees=0, home_unit1=0, home_unit2=2000, home_unit3=0, home_unit4=1000,
            training={}, returning={'unit4': {'6': 1000}}, timestamp=attacker.last_cs.timestamp))
        session.flush()

        row = build_threats_vm([defender, attacker], [], 1, 75, 250, 2, None)[0]

        self.assertIn('army out, back at +6', row.cells[5].tooltip)
        self.assertNotIn('army out', row.cells[6].tooltip)
        self.assertIn('±15%', row.cells[0].tooltip)


class SentAfterBarracksSpyTest(unittest.TestCase):
    def test_a_hit_after_the_last_bs_dims_the_row_and_asks_for_a_bs(self):
        session = create_db_session()
        defender = make_dominion(session, 1, realm=1, land=1000, miners=5000)
        attacker = make_dominion(session, 2, realm=2, land=1000, warriors=2000, miners=2000)
        session.flush()
        hit = TownCrier(origin=2, target=3, event_type='invasion', amount=10,
                        timestamp=current_od_time() - timedelta(hours=2))

        row = build_threats_vm([defender, attacker], [hit], 1, 75, 250, 2, None)[0]

        self.assertTrue(row.sent_after_bs)
        self.assertIn('sent 2h ago, after the last BS: take a BS', row.cells[9].tooltip)
        self.assertNotIn('take a BS', row.cells[10].tooltip)


class ThreatRowOrderTest(unittest.TestCase):
    def row(self, *cells: ThreatCellVM) -> ThreatRowVM:
        return ThreatRowVM(2, 'Attacker', 2, 'Dwarf', 0, list(cells))

    def test_a_red_cell_comes_before_an_earlier_orange_cell(self):
        red_later = self.row(ThreatCellVM(-1, 'none', ''), ThreatCellVM(500, 'now', ''))
        orange_now = self.row(ThreatCellVM(9000, 'triggered', ''), ThreatCellVM(9000, 'triggered', ''))
        self.assertLess(red_later.sort_key, orange_now.sort_key)

    def test_the_earlier_tick_comes_first_for_the_same_status(self):
        red_now = self.row(ThreatCellVM(100, 'now', ''), ThreatCellVM(100, 'now', ''))
        red_later = self.row(ThreatCellVM(None, 'out', ''), ThreatCellVM(9000, 'now', ''))
        self.assertLess(red_now.sort_key, red_later.sort_key)


if __name__ == '__main__':
    unittest.main()
