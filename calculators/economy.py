from math import trunc

from opsdata.schema import *
from domain.castle import castle_for


class Economy(object):
    def __init__(self, domcode, cs, dom, survey, castle):
        self.domcode = domcode
        self.dom = dom
        self.cs = cs
        self.survey = survey
        self.castle = castle

    def base_plat_per_hour(self):
        pass

    @property
    def raw_capacity(self) -> int:
        homes = self.homes * 30
        non_homes = self.non_homes * 15
        constructing = self.constructing * 15
        barren = self.barren * 5
        return homes + non_homes + constructing + barren

    @property
    def total_capacity(self) -> int:
        return trunc(self.raw_capacity * self.castle.keep)

    @property
    def homes(self) -> int:
        return int(self.survey['home'])

    @property
    def non_homes(self) -> int:
        return sum([int(v) for k, v in self.constructed.items() if k != 'home']) if self.constructed else 0

    @property
    def constructing(self) -> int:
        constructing = 0
        if self.ops.q_exists('survey.constructing'):
            for b in self.ops.q('survey.constructing').values():
                for t in b.values():
                    constructing += int(t)
        return constructing

    @property
    def barren(self) -> int:
        return self.ops.q('land.totalBarrenLand')


def economy_for(db, domcode):
    cs = query_clearsight(db, domcode, latest=True)
    survey = query_survey(db, domcode, latest=True)
    castle = castle_for(db, domcode)
    ls = query_land(db, domcode, latest=True)
    dom = query_dominion(db, domcode)
    return Economy(domcode, cs, dom, survey, castle)
