import json

from opsdata.scrapetools import get_soup_page
from config import OP_CENTER_URL


#
#
# class Buildings(object):
#     def __init__(self, ops):
#         self.ops = ops
#         if self.ops.q_exists('survey.constructed'):
#             self.constructed = self.ops.q('survey.constructed')
#         else:
#             self.constructed = None
#
#     @property
#     def total(self) -> int:
#         return self.homes + self.non_homes
#
#     @property
#     def raw_capacity(self) -> int:
#         homes = self.homes * 30
#         non_homes = self.non_homes * 15
#         constructing = self.constructing * 15
#         barren = self.barren * 5
#         return homes + non_homes + constructing + barren
#
#     @property
#     def total_capacity(self) -> int:
#         return trunc(self.raw_capacity * self.ops.population_bonus)
#
#     @property
#     def homes(self) -> int:
#         return self.ops.q('home', self.constructed) if self.constructed else 0
#
#     @property
#     def non_homes(self) -> int:
#         return sum([int(v) for k, v in self.constructed.items() if k != 'home']) if self.constructed else 0
#
#     @property
#     def constructing(self) -> int:
#         constructing = 0
#         if self.ops.q_exists('survey.constructing'):
#             for b in self.ops.q('survey.constructing').values():
#                 for t in b.values():
#                     constructing += int(t)
#         return constructing
#
#     @property
#     def barren(self) -> int:
#         return self.ops.q('land.totalBarrenLand')
#
#
# class Castle(object):
#     def __init__(self, ops):
#         self.ops = ops
#
#     def exists(self) -> bool:
#         return self.ops.q_exists('castle')
#
#     def imp_formula(self, ops_field: str, imp_name: str) -> float:
#         points = self.ops.q(ops_field)
#         maximum, factor, plus = IMP_FACTORS[imp_name]
#         return round(maximum * (1 - exp(-points/(factor * self.ops.land + plus))) * (1 + self.mason_bonus), 4)
#
#     @property
#     def keep(self):
#         return self.imp_formula('castle.keep.points', 'keep')
#
#     @property
#     def science(self):
#         return self.imp_formula('castle.spires.points', 'spires')
#
#     @property
#     def forges(self):
#         return self.imp_formula('castle.forges.points', 'forges')
#
#     @property
#     def mason_bonus(self):
#         return self.ops.q('survey.constructed.masonry') / self.ops.land * MASONRY_MULTIPLIER
#
#

#
#
#

# Old Ops stuff

#     @property
#     def population_bonus(self):
#         return (1 + self.castle.keep + self.population_tech_bonus + self.wonder_bonus) * (1 + self.prestige_bonus)
#
#     @property
#     def total_spywiz(self):
#         result = 0
#         result += self.q('status.military_spies')
#         result += self.q('status.military_assassins')
#         result += self.q('status.military_wizards')
#         result += self.q('status.military_archmages')
#         return result


class Ops(object):
    def __init__(self, contents):
        self.contents = contents

    def q_exists(self, q_str, start_node=None) -> bool:
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            if path in current_node:
                current_node = current_node[path]
                if not current_node:
                    return False
            else:
                return False
        return True

    def q(self, q_str, start_node=None):
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            current_node = current_node[path]
        return current_node

    @property
    def has_clearsight(self) -> bool:
        return self.q_exists('status.name')

    @property
    def has_vision(self) -> bool:
        return self.q_exists('vision.techs')

    @property
    def has_barracks(self) -> bool:
        return self.q_exists('barracks.units')

    @property
    def has_castle(self) -> bool:
        return self.q_exists('castle.total')

    @property
    def has_land(self) -> bool:
        return self.q_exists('land.totalLand')

    @property
    def has_survey(self) -> bool:
        return self.q_exists('survey.constructed')


def grab_ops(session, dom_code) -> Ops:
    """Grabs the copy_ops JSON file for a specified dominion."""
    soup = get_soup_page(session, f'{OP_CENTER_URL}/{dom_code}')
    ops_json = soup.find('textarea', id='ops_json').string
    return Ops(json.loads(ops_json))
