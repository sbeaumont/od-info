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
MIN_RANGE = 75
MAX_RANGE = 250
POTENTIAL_MARGIN = 10


def make_strike(five_four_op: int, safe_send_op: int, triggers=(), triggered_op=None, triggered_dp=None) -> Strike:
    return Strike(attacker=2, defender_dp=10000, five_four_op=five_four_op, safe_send_op=safe_send_op,
                  held_by=[3, 4], triggers=list(triggers), triggered_op=triggered_op, triggered_dp=triggered_dp)


class ThreatCellTest(unittest.TestCase):
    def test_safe_send_that_breaks_is_now(self):
        cell = threat_cell(make_strike(14000, 12000), NAMES, POTENTIAL_MARGIN)
        self.assertEqual(('now', 2000), (cell.status, cell.margin))

    def test_safe_send_after_triggers_is_triggered(self):
        cell = threat_cell(make_strike(14000, 9000, [Trigger(3, True)], 11000, 10000), NAMES, POTENTIAL_MARGIN)
        self.assertEqual(('triggered', 1000), (cell.status, cell.margin))
        self.assertIn('after Vex (free)', cell.tooltip)

    def test_only_a_5_4_send_that_breaks_is_five_four(self):
        cell = threat_cell(make_strike(14000, 9000), NAMES, POTENTIAL_MARGIN)
        self.assertEqual(('five_four', 4000), (cell.status, cell.margin))
        self.assertIn('held: Vex, Kragg', cell.tooltip)

    def test_a_5_4_send_within_the_potential_margin_is_potential(self):
        cell = threat_cell(make_strike(9000, 8000), NAMES, POTENTIAL_MARGIN)
        self.assertEqual(('potential', -1000), (cell.status, cell.margin))

    def test_a_5_4_send_below_the_potential_margin_is_none(self):
        cell = threat_cell(make_strike(8999, 8000), NAMES, POTENTIAL_MARGIN)
        self.assertEqual(('none', -1001), (cell.status, cell.margin))


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
            build_threats_vm([defender, attacker], [], 1, MIN_RANGE, MAX_RANGE, 2, POTENTIAL_MARGIN, None)


class ArmyOutTest(unittest.TestCase):
    def test_the_tooltip_says_the_army_is_out_until_the_returning_units_arrive(self):
        session = create_db_session()
        defender = make_dominion(session, 1, realm=1, land=1000, miners=5000)
        attacker = make_dominion(session, 2, realm=2, land=1000, warriors=2000, miners=2000)
        attacker.barracks_spy.append(BarracksSpy(
            draftees=0, home_unit1=0, home_unit2=2000, home_unit3=0, home_unit4=1000,
            training={}, returning={'unit4': {'6': 1000}}, timestamp=attacker.last_cs.timestamp))
        session.flush()

        row = build_threats_vm([defender, attacker], [], 1, MIN_RANGE, MAX_RANGE, 2, POTENTIAL_MARGIN, None)[0]

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

        row = build_threats_vm([defender, attacker], [hit], 1, MIN_RANGE, MAX_RANGE, 2, POTENTIAL_MARGIN, None)[0]

        self.assertTrue(row.sent_after_bs)
        self.assertIn('sent 2h ago, after the last BS: take a BS', row.cells[9].tooltip)
        self.assertNotIn('take a BS', row.cells[10].tooltip)


class RowSelectionTest(unittest.TestCase):
    def setUp(self):
        self.session = create_db_session()

    def rows(self, *doms):
        self.session.flush()
        return {row.code: row
                for row in build_threats_vm(list(doms), [], 1, MIN_RANGE, MAX_RANGE, 2, POTENTIAL_MARGIN, None)}

    def test_a_5_4_send_more_than_the_potential_margin_below_the_dp_is_no_threat(self):
        rows = self.rows(make_dominion(self.session, 1, realm=1, land=1000, miners=5000),
                         make_dominion(self.session, 2, realm=2, land=1000, warriors=2000, miners=50000))
        self.assertEqual(14000 - 16500, rows[2].cells[0].margin)
        self.assertTrue(rows[2].in_range)
        self.assertFalse(rows[2].threat)

    def test_a_5_4_send_within_the_potential_margin_of_the_dp_is_a_potential_threat(self):
        rows = self.rows(make_dominion(self.session, 1, realm=1, land=1000, miners=5000),
                         make_dominion(self.session, 2, realm=2, land=1000, warriors=2200, miners=50000))
        cell = rows[2].cells[0]
        self.assertEqual(('potential', 15400 - 16500), (cell.status, cell.margin))
        self.assertTrue(rows[2].threat)
        self.assertIn('75% at 750 acres, defender +250', cell.tooltip)

    def test_a_threat_with_the_defender_below_its_range_is_out_of_range_with_its_limit(self):
        rows = self.rows(make_dominion(self.session, 1, realm=1, land=700, miners=5000),
                         make_dominion(self.session, 2, realm=2, land=1000, warriors=9000, miners=50000))
        self.assertFalse(rows[2].in_range)
        self.assertEqual(750, rows[2].limit)
        self.assertEqual('now', rows[2].cells[0].status)
        self.assertTrue(rows[2].threat)
        self.assertIn('75% at 750 acres, defender -50', rows[2].cells[0].tooltip)

    def test_an_out_of_range_dominion_that_cannot_break_the_defender_is_no_threat(self):
        rows = self.rows(make_dominion(self.session, 1, realm=1, land=700, miners=5000),
                         make_dominion(self.session, 2, realm=2, land=1000, warriors=100, miners=5000))
        self.assertFalse(rows[2].in_range)
        self.assertFalse(rows[2].threat)

    def test_out_of_range_rows_come_before_in_range_rows(self):
        doms = [make_dominion(self.session, 1, realm=1, land=700, miners=5000),
                make_dominion(self.session, 2, realm=2, land=1000, warriors=9000, miners=50000),
                make_dominion(self.session, 3, realm=2, land=800, warriors=100, miners=5000)]
        self.session.flush()
        rows = build_threats_vm(doms, [], 1, MIN_RANGE, MAX_RANGE, 2, POTENTIAL_MARGIN, None)
        self.assertEqual([(2, False), (3, True)], [(row.code, row.in_range) for row in rows])

    def test_each_table_starts_with_the_largest_range_limit(self):
        doms = [make_dominion(self.session, 1, realm=1, land=700, miners=5000),
                make_dominion(self.session, 2, realm=2, land=800, warriors=100),
                make_dominion(self.session, 3, realm=2, land=900, warriors=100),
                make_dominion(self.session, 4, realm=2, land=1000, warriors=100),
                make_dominion(self.session, 5, realm=2, land=1100, warriors=100)]
        self.session.flush()
        rows = build_threats_vm(doms, [], 1, MIN_RANGE, MAX_RANGE, 2, POTENTIAL_MARGIN, None)
        self.assertEqual([(5, False), (4, False), (3, True), (2, True)], [(row.code, row.in_range) for row in rows])

    def test_a_dominion_with_the_defender_far_below_its_range_is_out_of_range(self):
        rows = self.rows(make_dominion(self.session, 1, realm=1, land=700, miners=5000),
                         make_dominion(self.session, 2, realm=2, land=3000, warriors=9000, miners=50000))
        self.assertFalse(rows[2].in_range)
        self.assertTrue(rows[2].threat)


if __name__ == '__main__':
    unittest.main()
