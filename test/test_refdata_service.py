import json
import os
import shutil
import tempfile
import unittest

from odinfo.config import REF_DATA_STAMP_FILE, refdata_sync_time
from odinfo.services.refdata_service import RefDataService, diff_perks, extract_perks

SPELLS = {
    'ares_call': {'name': 'Ares Call', 'perks': {'defense': 10}},
    'howling': {'name': 'Howling', 'races': ['lycanthrope'], 'perks': {'offense': 10}},
}

RACE = {
    'name': 'Orc',
    'perks': {'offense': 5},
    'units': [
        {'name': 'Voyeur', 'power': {'offense': 0, 'defense': 3}, 'perks': {'counts_as_spy': 0.15}},
        {'name': 'Basher', 'power': {'offense': 5, 'defense': 0}},
    ],
}


class PerkExtractionTest(unittest.TestCase):
    def test_finds_perks_at_every_level(self):
        records = extract_perks('races/orc.yml', RACE)
        self.assertEqual(
            {('races/orc.yml', 'offense'), ('races/orc.yml:units.Voyeur', 'counts_as_spy')},
            {(record.entity, record.perk) for record in records})

    def test_labels_entities_by_name_not_position(self):
        records = extract_perks('spells.yml', SPELLS)
        self.assertIn('spells.yml:ares_call', [record.entity for record in records])


class PerkDiffTest(unittest.TestCase):
    def setUp(self):
        self.current = {'spells.yml': SPELLS, 'races/orc.yml': RACE}

    def diff_against(self, new_spells=None, new_race=None, ignored=None):
        new = {'spells.yml': new_spells if new_spells else SPELLS,
               'races/orc.yml': new_race if new_race else RACE}
        return diff_perks(self.current, new, ignored if ignored else dict())

    def test_unchanged_data_has_no_changes(self):
        diff = self.diff_against()
        self.assertFalse(diff.needs_attention)
        self.assertEqual([], diff.new_perks)
        self.assertEqual([], diff.changed_perks)

    def test_new_perk_name_needs_attention(self):
        spells = dict(SPELLS, mystic_aura={'name': 'Mystic Aura', 'perks': {'spell_reflect': 1}})
        diff = self.diff_against(new_spells=spells)

        self.assertTrue(diff.needs_attention)
        self.assertEqual(['spell_reflect'], [perk.name for perk in diff.new_perks])
        self.assertEqual(['spells.yml:mystic_aura'], diff.new_perks[0].entities)

    def test_reviewed_perk_does_not_need_attention(self):
        spells = dict(SPELLS, mystic_aura={'name': 'Mystic Aura', 'perks': {'spell_reflect': 1}})
        diff = self.diff_against(new_spells=spells, ignored={'spell_reflect': 'Not modelled.'})

        self.assertFalse(diff.needs_attention)
        self.assertEqual('Not modelled.', diff.new_perks[0].ignored_because)

    def test_retired_perk_name_needs_attention(self):
        """Only when the name is gone everywhere, since perk names are global. Dropping
        Howling leaves 'offense' alive on the race, dropping Ares Call retires 'defense'."""
        diff = self.diff_against(new_spells={'howling': SPELLS['howling']})

        self.assertTrue(diff.needs_attention)
        self.assertEqual(['defense'], [perk.name for perk in diff.retired_perks])

    def test_perk_still_used_elsewhere_is_not_retired(self):
        diff = self.diff_against(new_spells={'ares_call': SPELLS['ares_call']})

        self.assertFalse(diff.needs_attention)
        self.assertEqual([], diff.retired_perks)

    def test_known_perk_on_another_entity_is_not_attention_worthy(self):
        """A perk moving around is fine, the calculators read that from the files."""
        spells = dict(SPELLS, warsong={'name': 'Warsong', 'perks': {'offense': 5}})
        diff = self.diff_against(new_spells=spells)

        self.assertFalse(diff.needs_attention)
        self.assertEqual(['offense'], [change.name for change in diff.changed_perks])
        self.assertEqual(['spells.yml:warsong'],
                         [record.entity for record in diff.changed_perks[0].added])

    def test_changed_value_is_reported_with_both_values(self):
        spells = dict(SPELLS, ares_call={'name': 'Ares Call', 'perks': {'defense': 15}})
        diff = self.diff_against(new_spells=spells)

        self.assertFalse(diff.needs_attention)
        old, new = diff.changed_perks[0].changed_values[0]
        self.assertEqual((10, 15), (old.value, new.value))


class RefDataPrecedenceTest(unittest.TestCase):
    """Which of the two copies of the reference data the application reads."""

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.baseline = os.path.join(self.tempdir, 'baseline')
        self.override = os.path.join(self.tempdir, 'override')
        os.makedirs(self.baseline)
        os.makedirs(self.override)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def stamp(self, directory: str, synced_at: str):
        with open(os.path.join(directory, REF_DATA_STAMP_FILE), 'w') as f:
            json.dump({'synced_at': synced_at, 'branch': 'develop', 'tree': 'abc'}, f)

    def test_unstamped_copy_is_the_oldest(self):
        self.stamp(self.baseline, '2026-08-09T12:00:00')
        self.assertEqual('', refdata_sync_time(self.override))
        self.assertLess(refdata_sync_time(self.override), refdata_sync_time(self.baseline))

    def test_younger_override_wins(self):
        self.stamp(self.baseline, '2026-08-09T12:00:00')
        self.stamp(self.override, '2026-08-10T09:00:00')
        self.assertGreater(refdata_sync_time(self.override), refdata_sync_time(self.baseline))


class IgnoredPerksTest(unittest.TestCase):
    def test_every_ignored_perk_says_why(self):
        """The reason is what the report shows when the perk turns up again."""
        for perk, reason in RefDataService().ignored_perks().items():
            self.assertIsInstance(reason, str, f"{perk} has no reason")
            self.assertTrue(reason.strip(), f"{perk} has an empty reason")


if __name__ == '__main__':
    unittest.main()