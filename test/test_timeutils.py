import unittest
from datetime import datetime

from odinfo.exceptions import ODInfoException
from odinfo.timeutils import cleanup_timestamp, ticks_between


class CleanupTimestampTest(unittest.TestCase):
    def test_accepts_both_separators(self):
        expected = datetime(2026, 3, 22, 0, 42, 58)
        self.assertEqual(expected, cleanup_timestamp('2026-03-22 00:42:58'))
        self.assertEqual(expected, cleanup_timestamp('2026-03-22T00:42:58'))

    def test_ignores_trailing_fractions(self):
        self.assertEqual(datetime(2026, 3, 22, 0, 42, 58),
                         cleanup_timestamp('2026-03-22 00:42:58.123456'))

    def test_accepts_a_scraped_cell_with_its_padding(self):
        self.assertEqual(datetime(2026, 8, 13, 13, 59, 51),
                         cleanup_timestamp('\n                2026-08-13 13:59:51\n            '))

    def test_refuses_to_guess(self):
        for junk in ('None', '', 'yesterday', '2026-03-22'):
            with self.subTest(junk=junk):
                with self.assertRaises(ODInfoException):
                    cleanup_timestamp(junk)


class TicksBetweenTest(unittest.TestCase):
    def test_counts_hour_boundaries(self):
        self.assertEqual(4, ticks_between(datetime(2026, 10, 29, 18, 26), datetime(2026, 10, 29, 22, 10)))

    def test_same_tick_is_zero(self):
        self.assertEqual(0, ticks_between(datetime(2026, 10, 29, 18, 26), datetime(2026, 10, 29, 18, 59)))

    def test_one_boundary_under_an_hour_apart(self):
        self.assertEqual(1, ticks_between(datetime(2026, 10, 29, 18, 59), datetime(2026, 10, 29, 19, 1)))


if __name__ == '__main__':
    unittest.main()