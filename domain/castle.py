from opsdata.schema import query_castle
from domain.refdata import IMP_FACTORS, MASONRY_MULTIPLIER
from math import exp
from domain.unknown import Unknown


class Castle(object):
    def __init__(self, dom, data):
        self._data = data
        self.dom = dom

    def __str__(self):
        return f"Castle(keep: {self.keep}, science: {self.science}, forges: {self.forges}, walls: {self.walls})"

    @property
    def keep(self) -> float:
        return self._data['keep_rating']

    @property
    def science(self) -> float:
        return self._data['science_rating']

    @property
    def forges(self) -> float:
        return self._data['forges_rating']

    @property
    def walls(self) -> float:
        return self._data['walls_rating']

    @property
    def mason_bonus(self) -> float:
        return self.dom.buildings.masons / self.dom.land.total * MASONRY_MULTIPLIER

    def imp_formula(self, ops_field: str, imp_name: str) -> float:
        points = self._data(ops_field)
        maximum, factor, plus = IMP_FACTORS[imp_name]
        return round(maximum * (1 - exp(-points/(factor * self.dom.land.total + plus))) * (1 + self.mason_bonus), 4)


def castle_for(db, dom) -> Castle | Unknown:
    castle_data = query_castle(db, dom.code, latest=True)
    if castle_data:
        return Castle(dom, castle_data)
    else:
        return Unknown()
