import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from odinfo.domain.models import Base, Dominion, DominionHistory
from odinfo.repositories.game import GameRepository
from odinfo.services.report_service import (BOT_REALM, TOP_BOTTOM_COUNT,
                                            ReportService, format_span)

NOW = datetime(2026, 3, 22, 12, 0, 0)
PLAYER_REALM = 7


class ReportServiceTest(unittest.TestCase):
    """The Networth Tracker's three tables, and what keeps a dominion out of them."""

    def setUp(self):
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        self.session = Session(engine)
        self.service = ReportService(GameRepository(self.session))
        self.next_code = 1
        # The window is measured back from current_od_time(), which reads the wall clock.
        # Pin it so the readings below stay where the tests put them.
        clock = patch('odinfo.calculators.networthcalculator.current_od_time',
                      return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.addCleanup(self.session.close)

    def add_dom(self, readings, realm=PLAYER_REALM, land=500):
        """A dominion seen at each (hours_ago, networth) in readings."""
        code = self.next_code
        self.next_code += 1
        dom = Dominion(code=code, name=f"Dominion {code}", realm=realm, race="Dwarf")
        self.session.add(dom)
        for hours_ago, networth in readings:
            dom.history.append(DominionHistory(land=land,
                                               networth=networth,
                                               timestamp=NOW - timedelta(hours=hours_ago)))
        self.session.commit()
        return code

    @staticmethod
    def codes_in(rows):
        return [row['code'] for row in rows]

    def test_one_reading_is_not_a_delta(self):
        self.add_dom([(2, 10000)])
        self.assertEqual([], self.service.get_unchanged_nw())
        self.assertEqual([], self.service.get_top_bot_nw())
        self.assertEqual([], self.service.get_top_bot_nw(top=False))
        self.assertEqual(1, self.service.count_without_delta())

    def test_readings_outside_the_window_do_not_count(self):
        self.add_dom([(30, 10000), (25, 12000)])
        self.assertEqual(1, self.service.count_without_delta(since=12))
        self.assertEqual(0, self.service.count_without_delta(since=48))

    def test_two_equal_readings_are_unchanged(self):
        code = self.add_dom([(10, 10000), (1, 10000)])
        self.assertEqual([code], self.codes_in(self.service.get_unchanged_nw()))
        self.assertEqual(0, self.service.count_without_delta())

    def test_growers_and_sinkers_land_in_their_own_table(self):
        grower = self.add_dom([(10, 10000), (1, 12000)])
        sinker = self.add_dom([(10, 10000), (1, 9000)])
        self.assertEqual([grower, sinker], self.codes_in(self.service.get_top_bot_nw()))
        self.assertEqual([sinker, grower],
                         self.codes_in(self.service.get_top_bot_nw(top=False)))

    def test_zeroes_never_displace_a_mover(self):
        movers = {self.add_dom([(10, 10000), (1, 10000 + n)])
                  for n in range(1, TOP_BOTTOM_COUNT + 3)}
        for _ in range(20):
            self.add_dom([(10, 10000), (1, 10000)])
        top = self.service.get_top_bot_nw(filter_zeroes=True)
        self.assertEqual(TOP_BOTTOM_COUNT, len(top))
        self.assertTrue(set(self.codes_in(top)) <= movers)

    def test_bots_are_left_out_of_everything(self):
        self.add_dom([(10, 10000), (1, 12000)], realm=BOT_REALM)
        self.add_dom([(10, 10000), (1, 10000)], realm=BOT_REALM)
        self.add_dom([(1, 10000)], realm=BOT_REALM)
        self.assertEqual([], self.service.get_top_bot_nw())
        self.assertEqual([], self.service.get_unchanged_nw())
        self.assertEqual(0, self.service.count_without_delta())

    def test_unchanged_is_sorted_by_land_and_capped_on_request(self):
        big = self.add_dom([(10, 10000), (1, 10000)], land=900)
        mid = self.add_dom([(10, 10000), (1, 10000)], land=600)
        small = self.add_dom([(10, 10000), (1, 10000)], land=300)
        self.assertEqual([big, mid, small], self.codes_in(self.service.get_unchanged_nw()))
        self.assertEqual([big, mid], self.codes_in(self.service.get_unchanged_nw(top=2)))

    def test_span_is_the_gap_between_readings_not_the_period(self):
        self.add_dom([(3, 10000), (1, 10000)])
        self.assertEqual('2h00m', self.service.get_unchanged_nw(since=48)[0]['span'])


class FormatSpanTest(unittest.TestCase):
    def test_renders_hours_and_minutes(self):
        self.assertEqual('0h00m', format_span(timedelta()))
        self.assertEqual('0h06m', format_span(timedelta(minutes=6)))
        self.assertEqual('11h04m', format_span(timedelta(hours=11, minutes=4)))
        self.assertEqual('48h00m', format_span(timedelta(hours=48)))


if __name__ == '__main__':
    unittest.main()