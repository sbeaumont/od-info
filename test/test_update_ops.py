import copy
import unittest
from datetime import datetime

from odinfo.domain.models import (Dominion, ClearSight, BarracksSpy, CastleSpy, LandSpy,
                                  SurveyDominion, Revelation)
from odinfo.opsdata.ops import Ops
from odinfo.opsdata.updater import update_ops
from odinfo.repositories.game import GameRepository
from test.fixtures import create_db_session

DOM_CODE = 17602

BUILDINGS = ['home', 'alchemy', 'farm', 'smithy', 'masonry', 'ore_mine', 'gryphon_nest', 'tower', 'wizard_guild',
             'temple', 'diamond_mine', 'school', 'lumberyard', 'factory', 'guard_tower', 'shrine', 'barracks', 'dock']
LAND_TYPES = ['plain', 'mountain', 'swamp', 'cavern', 'forest', 'hill', 'water']

OPS = {
    'clear_sight': {
        'land': 600, 'peasants': 7391, 'networth': 36646, 'prestige': 250,
        'resource_platinum': 57520, 'resource_food': 14045, 'resource_lumber': 3349, 'resource_mana': 7299,
        'resource_ore': 0, 'resource_gems': 0, 'resource_boats': 0,
        'military_draftees': 75, 'military_unit1': 88, 'military_unit2': 1704, 'military_unit3': 195,
        'military_unit4': 923, 'military_spies': None, 'military_assassins': None, 'military_wizards': None,
        'military_archmages': None, 'clear_sight_accuracy': None, 'spa': 0.0367, 'wpa': 0.0167,
        'race_name': 'Lizardfolk', 'realm': 3, 'name': 'Bowl', 'created_at': '2026-10-04T08:02:28Z',
    },
    'revelation': {
        'spells': [{'spell': 'ares_call', 'duration': 12}, {'spell': 'midas_touch', 'duration': 2}],
        'created_at': '2026-10-04T00:14:49Z',
    },
    'castle_spy': {
        **{part: {'points': 0, 'rating': 0, 'incoming': 0} for part in ['science', 'spires', 'forges', 'walls', 'harbor']},
        'keep': {'points': 403416, 'rating': 0.0309, 'incoming': 0},
        'total': 403416, 'created_at': '2026-10-04T16:58:27Z',
    },
    'barracks_spy': {
        'units': {
            'home': {'draftees': 0, 'unit1': 0, 'unit2': 2458, 'unit3': 207, 'unit4': 127},
            'returning': {'unit4': {'8': 1221}},
            'training': {'unit2': {'1': 72, '9': 111}},
        },
        'created_at': '2026-10-04T20:55:10Z',
    },
    'survey_dominion': {
        'constructed': {**{b: 0 for b in BUILDINGS}, 'home': 86, 'alchemy': 202},
        'constructing': {'farm': {'8': 10}},
        'barren_land': 0, 'total_land': 820, 'created_at': '2026-10-04T20:55:18Z',
    },
    'land_spy': {
        'totalLand': 782, 'totalBarrenLand': 16, 'totalConstructedLand': 666,
        'explored': {**{t: {'amount': 0, 'constructed': 0} for t in LAND_TYPES},
                     'plain': {'amount': 403, 'constructed': 376}},
        'created_at': '2026-10-04T16:58:27Z',
    },
    'vision': None,
    'disclosure': None,
}


class UpdateOpsTest(unittest.TestCase):
    def setUp(self):
        self.repo = GameRepository(create_db_session())
        self.repo.session.add(Dominion(code=DOM_CODE, name='Bowl', realm=3, race='Lizardfolk'))
        self.repo.session.commit()

    def query(self, model):
        return self.repo.session.query(model).filter_by(dominion_id=DOM_CODE).all()

    def test_stores_each_op_type_from_the_api(self):
        update_ops(Ops(OPS, DOM_CODE), self.repo, DOM_CODE)

        cs = self.query(ClearSight)[0]
        self.assertEqual((datetime(2026, 10, 4, 8, 2, 28), 600, 1704, None, 1.0),
                         (cs.timestamp, cs.land, cs.military_unit2, cs.military_spies, cs.clear_sight_accuracy))
        bs = self.query(BarracksSpy)[0]
        self.assertEqual((2458, {'unit2': {'1': 72, '9': 111}}, {'unit4': {'8': 1221}}),
                         (bs.home_unit2, bs.training, bs.returning))
        self.assertEqual(403416, self.query(CastleSpy)[0].keep_points)
        survey = self.query(SurveyDominion)[0]
        self.assertEqual((86, 202, {'farm': {'8': 10}}), (survey.home, survey.alchemy, survey.constructing))
        land = self.query(LandSpy)[0]
        self.assertEqual((782, 403, 376), (land.total, land.plain, land.plain_constructed))

    def test_revelation_has_its_own_timestamp(self):
        update_ops(Ops(OPS, DOM_CODE), self.repo, DOM_CODE)
        spells = self.query(Revelation)
        self.assertEqual({'ares_call', 'midas_touch'}, {s.spell for s in spells})
        self.assertEqual({datetime(2026, 10, 4, 0, 14, 49)}, {s.timestamp for s in spells})

    def test_keeps_the_accuracy_of_a_fuzzed_clear_sight(self):
        ops = copy.deepcopy(OPS)
        ops['clear_sight']['clear_sight_accuracy'] = 0.85
        update_ops(Ops(ops, DOM_CODE), self.repo, DOM_CODE)
        self.assertEqual(0.85, self.query(ClearSight)[0].clear_sight_accuracy)

    def test_a_second_poll_adds_nothing(self):
        update_ops(Ops(OPS, DOM_CODE), self.repo, DOM_CODE)
        update_ops(Ops(OPS, DOM_CODE), self.repo, DOM_CODE)
        for model in (ClearSight, BarracksSpy, CastleSpy, SurveyDominion, LandSpy):
            with self.subTest(model=model.__name__):
                self.assertEqual(1, len(self.query(model)))
        self.assertEqual(2, len(self.query(Revelation)))


if __name__ == '__main__':
    unittest.main()