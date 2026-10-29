import os
import tempfile
import unittest

from odinfo.config import write_secrets

SECRETS = """# ODInfo Configuration File
username = me
password = old
api_key = round-51-key

# Optional Discord webhook URL for notifications
#discord_webhook = None
"""


class WriteSecretsTest(unittest.TestCase):
    def setUp(self):
        handle, self.filename = tempfile.mkstemp()
        with os.fdopen(handle, 'w') as f:
            f.write(SECRETS)

    def tearDown(self):
        os.remove(self.filename)

    def written(self) -> str:
        with open(self.filename) as f:
            return f.read()

    def test_replaces_a_value_and_keeps_the_comments(self):
        write_secrets(self.filename, {'api_key': 'round-52-key'})
        self.assertEqual(SECRETS.replace('round-51-key', 'round-52-key'), self.written())

    def test_turns_a_commented_out_key_into_a_value(self):
        write_secrets(self.filename, {'discord_webhook': 'https://discord.example/hook'})
        self.assertIn('\ndiscord_webhook = https://discord.example/hook\n', self.written())
        self.assertNotIn('#discord_webhook', self.written())

    def test_adds_a_key_that_is_not_in_the_file(self):
        write_secrets(self.filename, {'database_name': 'sqlite:///old.sqlite'})
        self.assertTrue(self.written().endswith('#discord_webhook = None\ndatabase_name = sqlite:///old.sqlite\n'))


if __name__ == '__main__':
    unittest.main()