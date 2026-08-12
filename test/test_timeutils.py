import unittest
from datetime import datetime

from odinfo.exceptions import ODInfoException
from odinfo.timeutils import cleanup_timestamp


class CleanupTimestampTest(unittest.TestCase):
    def test_accepts_both_separators(self):
        expected = datetime(2026, 3, 22, 0, 42, 58)
        self.assertEqual(expected, cleanup_timestamp('2026-03-22 00:42:58'))
        self.assertEqual(expected, cleanup_timestamp('2026-03-22T00:42:58'))

    def test_ignores_trailing_fractions(self):
        self.assertEqual(datetime(2026, 3, 22, 0, 42, 58),
                         cleanup_timestamp('2026-03-22 00:42:58.123456'))

    def test_refuses_to_guess(self):
        for junk in ('None', '', 'yesterday', '2026-03-22'):
            with self.subTest(junk=junk):
                with self.assertRaises(ODInfoException):
                    cleanup_timestamp(junk)


if __name__ == '__main__':
    unittest.main()