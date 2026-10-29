import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from odinfo.calculators.military import MilitaryCalculator
from odinfo.domain.models import ClearSight, Dominion, DominionHistory, TownCrier
from odinfoweb.viewmodels.targets import build_targets_vm
from test.fixtures import create_db_session

NOW = datetime(2026, 10, 28, 12, 0, 0)
ATTACKER_LAND = 1000


class TargetsTest(unittest.TestCase):
    """The rows of the targets page, built from the dominion index and the Town Crier."""

    def setUp(self):
        self.session = create_db_session()
        self.addCleanup(self.session.close)
        self.next_code = 1
        # The ages are measured back from current_od_time(), which reads the wall clock.
        # Pin it so the readings below stay where the tests put them.
        for target in ('odinfo.timeutils.current_od_time', 'odinfoweb.viewmodels.targets.current_od_time'):
            clock = patch(target, return_value=NOW)
            clock.start()
            self.addCleanup(clock.stop)

    def add_dom(self, readings, race='Dwarf'):
        """A dominion seen at each (hours_ago, land, networth) in readings."""
        code = self.next_code
        self.next_code += 1
        dom = Dominion(code=code, name=f"Dominion {code}", realm=3, race=race)
        self.session.add(dom)
        for hours_ago, land, networth in readings:
            dom.history.append(DominionHistory(land=land, networth=networth,
                                               timestamp=NOW - timedelta(hours=hours_ago)))
        self.session.commit()
        return dom

    @staticmethod
    def invasion(hours_ago, origin, target, amount, event_type='invasion'):
        return TownCrier(timestamp=NOW - timedelta(hours=hours_ago), origin=origin, target=target,
                         event_type=event_type, amount=amount)

    def rows(self, doms, events=()):
        return {row.code: row for row in build_targets_vm(doms, ATTACKER_LAND, list(events))}

    def test_nw_per_acre_against_race_median(self):
        doms = [self.add_dom([(0, 1000, nw)]) for nw in (40000, 50000, 60000)]
        rows = self.rows(doms)
        self.assertEqual([-20.0, 0.0, 20.0], [rows[d.code].nw_vs_race for d in doms])

    def test_each_race_has_its_own_median(self):
        dwarf = self.add_dom([(0, 1000, 40000)], race='Dwarf')
        nomad = self.add_dom([(0, 1000, 80000)], race='Nomad')
        rows = self.rows([dwarf, nomad])
        self.assertEqual(0.0, rows[dwarf.code].nw_vs_race)
        self.assertEqual(0.0, rows[nomad.code].nw_vs_race)

    def test_out_of_range_is_left_out(self):
        small = self.add_dom([(0, 749, 10000)])
        large = self.add_dom([(0, 2501, 100000)])
        edge = self.add_dom([(0, 750, 10000)])
        self.assertEqual({edge.code}, set(self.rows([small, large, edge])))

    def test_sent_shows_the_last_invasion_by_the_dominion(self):
        dom = self.add_dom([(0, 1000, 50000)])
        rows = self.rows([dom], [self.invasion(20, dom.code, 99, 30),
                                 self.invasion(5, dom.code, 99, 0, 'bounce')])
        self.assertEqual(5, rows[dom.code].sent_age)
        self.assertTrue(rows[dom.code].sent_bounced)

    def test_hit_by_shows_the_last_invasion_on_the_dominion(self):
        dom = self.add_dom([(0, 1000, 50000)])
        rows = self.rows([dom], [self.invasion(3, 99, dom.code, 40)])
        self.assertEqual(3, rows[dom.code].hit_age)
        self.assertEqual(40, rows[dom.code].hit_land)
        self.assertIsNone(rows[dom.code].sent_age)

    def test_dp_is_unknown_without_ops(self):
        dom = self.add_dom([(0, 1000, 50000)])
        self.assertIsNone(self.rows([dom])[dom.code].dp)

    def test_dp_comes_from_the_ops(self):
        dom = self.add_dom([(0, 1000, 50000)])
        dom.clear_sight.append(ClearSight(land=1000, peasants=0, networth=50000, prestige=250,
                                          resource_platinum=0, military_draftees=1000,
                                          timestamp=NOW - timedelta(hours=2)))
        self.session.commit()
        row = self.rows([dom])[dom.code]
        self.assertEqual(MilitaryCalculator(dom).paid_dp, row.dp)
        self.assertLessEqual(1000, row.dp)
        self.assertFalse(row.dp_incomplete)

    def test_explored_adds_back_land_lost_to_hits(self):
        dom = self.add_dom([(23, 1000, 50000), (0, 1060, 52000)])
        rows = self.rows([dom], [self.invasion(10, 99, dom.code, 40)])
        self.assertEqual(100, rows[dom.code].explored)

    def test_explored_is_unknown_while_own_invasions_can_add_land(self):
        dom = self.add_dom([(23, 1000, 50000), (0, 1060, 52000)])
        rows = self.rows([dom], [self.invasion(30, dom.code, 99, 40)])
        self.assertIsNone(rows[dom.code].explored)


if __name__ == '__main__':
    unittest.main()