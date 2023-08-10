import unittest
from opsdata.db import Database
from config import DATABASE
from opsdata.schema import row_s_to_dict
from domain.dominion import Dominion


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Database()
        self.db.init(DATABASE)
        # dom = Dominion(db, 10792)
        self.dom = Dominion(self.db, 10793)

    def test_something(self):
        print("Barracks:", self.dom.barracks)
        print("Castle:", self.dom.castle)
        print("Land:", self.dom.land)
        print("Race:", self.dom.race)
        print("CS:", row_s_to_dict(self.dom.cs))
        print("OP:", self.dom.barracks.op)
        print("DP:", self.dom.barracks.dp)
        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
