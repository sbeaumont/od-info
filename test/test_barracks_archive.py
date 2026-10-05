import unittest
from datetime import datetime
from unittest.mock import Mock

from odinfo.domain.models import Dominion, BarracksSpy
from odinfo.opsdata.updater import update_barracks_archive
from odinfo.repositories.game import GameRepository
from odinfo.services.update_service import UpdateService
from test.fixtures import create_db_session

DOM_CODE = 17602


def barracks_spy(unit2: int, created_at: str) -> dict:
    return {'units': {'home': {'draftees': 0, 'unit1': 0, 'unit2': unit2, 'unit3': 207, 'unit4': 127},
                      'returning': {'unit4': {'8': 1221}},
                      'training': {'unit2': {'1': 72}}},
            'created_at': created_at}


LATEST = barracks_spy(2458, '2026-10-04T20:55:10Z')
EARLIER = barracks_spy(2210, '2026-10-04T20:31:02Z')
OP_CENTER = {'dominions': {str(DOM_CODE): {'id': DOM_CODE, 'name': 'Bowl', 'realm': 3, 'race': 'Lizardfolk',
                                           'ops': {'clear_sight': None, 'revelation': None, 'castle_spy': None,
                                                   'barracks_spy': LATEST, 'survey_dominion': None,
                                                   'land_spy': None, 'vision': None, 'disclosure': None}}}}


class BarracksArchiveTest(unittest.TestCase):
    def setUp(self):
        self.repo = GameRepository(create_db_session())
        self.repo.session.add(Dominion(code=DOM_CODE, name='Bowl', realm=3, race='Lizardfolk'))
        self.repo.session.commit()
        self.api = Mock(op_center=Mock(return_value=OP_CENTER),
                        op_archive=Mock(return_value={'ops': [LATEST, EARLIER]}))

    def stored_unit2(self) -> dict:
        return {bs.timestamp: bs.home_unit2 for bs in self.repo.session.query(BarracksSpy)}

    def test_stores_every_barracks_spy_of_the_archive(self):
        update_barracks_archive(self.api, self.repo, DOM_CODE, max_age_hours=12)
        self.api.op_archive.assert_called_once_with(DOM_CODE, 'barracks_spy', max_age_hours=12)
        self.assertEqual({datetime(2026, 10, 4, 20, 55, 10): 2458, datetime(2026, 10, 4, 20, 31, 2): 2210},
                         self.stored_unit2())

    def test_update_all_fetches_the_archive_only_for_a_new_barracks_spy(self):
        service = UpdateService(Mock(), self.repo, Mock(), lambda: self.api)
        service.update_all()
        service.update_all()
        self.api.op_archive.assert_called_once_with(DOM_CODE, 'barracks_spy', max_age_hours=12)
        self.assertEqual(2, len(self.stored_unit2()))


if __name__ == '__main__':
    unittest.main()