import unittest

from odinfoweb.user import User

ENTRY = {"id": "1", "name": "test", "password": "boink", "active": "true"}


class UserTest(unittest.TestCase):
    def test_a_user_without_the_admin_flag_is_no_admin(self):
        self.assertFalse(User(ENTRY).is_admin)

    def test_a_user_with_the_admin_flag_is_admin(self):
        self.assertTrue(User(dict(ENTRY, admin="true")).is_admin)


if __name__ == '__main__':
    unittest.main()