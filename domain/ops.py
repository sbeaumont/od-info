from math import exp, trunc
import json
import yaml

from domain.reference import TechTree, IMP_FACTORS, MASONRY_MULTIPLIER
from domain.scrapetools import get_soup_page, login
from config import REF_DATA_DIR, OP_CENTER_URL


class Unit(object):
    def __init__(self, yaml_src: dict, ops):
        self.src = yaml_src
        self.ops = ops

    def land_bonus(self, perk_name: str) -> float:
        if self.has_perk(perk_name):
            land_type, percent_per_point, max_bonus = self.get_perk(perk_name)
            return min(float(max_bonus), self.ops.q(f'land.explored.{land_type}.percentage') / float(percent_per_point))
        else:
            return 0

    def has_perk(self, name) -> bool:
        return 'perks' in self.src and name in self.src['perks']

    def get_perk(self, name):
        if self.has_perk(name):
            return self.src['perks'][name].split(',')
        else:
            return None

    @property
    def cost(self) -> dict:
        return self.src['cost']

    @property
    def offense(self) -> float:
        op = self.src['power']['offense']
        op += self.land_bonus('offense_from_land')
        return op

    @property
    def defense(self) -> float:
        dp = self.src['power']['defense']
        dp += self.land_bonus('defense_from_land')
        return dp

    @property
    def networth(self) -> int:
        op = self.offense
        dp = self.defense
        return round(1.8 * min(6, max(op, dp))) + (0.45 * min(6, op, dp)) + (0.2 * (max((op - 6), 0) + max((dp - 6), 0)))


class Buildings(object):
    def __init__(self, ops):
        self.ops = ops
        if self.ops.q_exists('survey.constructed'):
            self.constructed = self.ops.q('survey.constructed')
        else:
            self.constructed = None

    @property
    def total(self) -> int:
        return self.homes + self.non_homes

    @property
    def raw_capacity(self) -> int:
        homes = self.homes * 30
        non_homes = self.non_homes * 15
        constructing = self.constructing * 15
        barren = self.barren * 5
        return homes + non_homes + constructing + barren

    @property
    def total_capacity(self) -> int:
        return trunc(self.raw_capacity * self.ops.population_bonus)

    @property
    def homes(self) -> int:
        return self.ops.q('home', self.constructed) if self.constructed else 0

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


class Castle(object):
    def __init__(self, ops):
        self.ops = ops

    def exists(self) -> bool:
        return self.ops.q_exists('castle')

    def imp_formula(self, ops_field: str, imp_name: str) -> float:
        points = self.ops.q(ops_field)
        maximum, factor, plus = IMP_FACTORS[imp_name]
        return round(maximum * (1 - exp(-points/(factor * self.ops.land + plus))) * (1 + self.mason_bonus), 4)

    @property
    def keep(self):
        return self.imp_formula('castle.keep.points', 'keep')

    @property
    def science(self):
        return self.imp_formula('castle.spires.points', 'spires')

    @property
    def forges(self):
        return self.imp_formula('castle.forges.points', 'forges')

    @property
    def mason_bonus(self):
        return self.ops.q('survey.constructed.masonry') / self.ops.land * MASONRY_MULTIPLIER


class Military(object):
    def __init__(self, ops):
        self.ops = ops

    def amount(self, unit_type_nr) -> float:
        observations = list()
        observations.append(self.ops.q(f'status.military_unit{unit_type_nr}'))
        if self.ops.q_exists(f'barracks.units.home.unit{unit_type_nr}'):
            observations.append(self.ops.q(f'barracks.units.home.unit{unit_type_nr}'))
        return min(observations) * 1.15

    @property
    def offense(self) -> int:
        offense = 0

        offense += self.amount(1) * self.ops.race.def_spec.offense
        offense += self.amount(2) * self.ops.race.off_spec.offense
        offense += self.amount(3) * self.ops.race.def_elite.offense
        offense += self.amount(4) * self.ops.race.off_elite.offense

        offense_bonus = 1 + (float(self.ops.techtree.value_for_perk('offense', self.ops.techs)) / 100)
        offense *= offense_bonus

        if self.ops.castle.exists():
            offense *= 1 + self.ops.castle.forges
        else:
            print("No Castle Spy")

        return round(offense)


class Race(object):
    def __init__(self, ops):
        self.ops = ops
        name = self.ops.q('status.race_name').replace(' ', '').lower()
        with open(f'{REF_DATA_DIR}/races/{name}.yml', 'r') as f:
            self.yaml = yaml.safe_load(f)

    def unit(self, nr) -> Unit:
        return Unit(self.yaml['units'][nr - 1], self.ops)

    @property
    def off_spec(self) -> Unit:
        return self.unit(1)

    @property
    def def_spec(self) -> Unit:
        return self.unit(2)

    @property
    def def_elite(self) -> Unit:
        return self.unit(3)

    @property
    def off_elite(self) -> Unit:
        return self.unit(4)


class Ops(object):
    def __init__(self, contents, techtree):
        self.techtree = techtree
        self.contents = contents
        self.buildings = Buildings(self)
        self.castle = Castle(self)
        self.military = Military(self)
        self.race = Race(self)

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
    def land(self):
        return self.q('status.land')

    @property
    def prestige_bonus(self):
        return self.q('status.prestige') / 10000

    @property
    def wonder_bonus(self):
        return 0.03

    @property
    def techs(self):
        if self.q_exists('vision.techs'):
            return self.q('vision.techs').keys()
        else:
            print("No Vision")
            return []

    @property
    def population_tech_bonus(self):
        return self.techtree.value_for_perk('max_population', self.techs) / 100

    @property
    def population_bonus(self):
        return (1 + self.castle.keep + self.population_tech_bonus + self.wonder_bonus) * (1 + self.prestige_bonus)

    @property
    def total_spywiz(self):
        result = 0
        result += self.q('status.military_spies')
        result += self.q('status.military_assassins')
        result += self.q('status.military_wizards')
        result += self.q('status.military_archmages')
        return result


def create_ops(ops_json) -> Ops:
    return Ops(ops_json, TechTree())


def load_ops(file_name: str) -> Ops:
    with open(file_name, 'r') as f:
        return create_ops(json.load(f))


def get_ops(session, dom_code: str) -> Ops:
    soup = get_soup_page(session, f'{OP_CENTER_URL}/{dom_code}')
    ops_json = soup.find('textarea', id='ops_json').string
    return create_ops(json.loads(ops_json))
