import unittest
from datetime import timedelta
from types import SimpleNamespace

from odinfo.domain.domainhelper import Land
from odinfo.timeutils import current_od_time


class LandIncomingTest(unittest.TestCase):
    def land_spy(self, hours_ago: int) -> Land:
        data = SimpleNamespace(timestamp=current_od_time() - timedelta(hours=hours_ago),
                               incoming={'cavern': {'2': 9, '11': 10}, 'hill': {'12': 5}})
        return Land(None, data)

    def test_counts_all_incoming_of_a_fresh_land_spy(self):
        self.assertEqual(24, self.land_spy(0).incoming)

    def test_leaves_out_acres_that_arrived_since_the_land_spy(self):
        self.assertEqual(5, self.land_spy(11).incoming)