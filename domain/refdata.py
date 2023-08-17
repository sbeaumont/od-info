import yaml
from math import erf
from collections import defaultdict, namedtuple
from config import REF_DATA_DIR

NON_HOME_CAPACITY = 15
BUILD_TICKS = 12
MASONRY_MULTIPLIER = 2.75
GT_DEFENSE_FACTOR = 1.75
GN_OFFENSE_BONUS = 1.75
BS_UNCERTAINTY = 1.15
ARES_BONUS = 0.1

ImpFactor = namedtuple('ImpFactor', 'max factor plus')

IMP_FACTORS = {
    'science': ImpFactor(0.2, 4000, 15000),
    'keep': ImpFactor(0.3, 4000, 15000),
    'spires': ImpFactor(0.6, 5000, 15000),
    'forges': ImpFactor(0.3, 7500, 15000),
    'walls': ImpFactor(0.3, 7500, 15000),
    'harbor': ImpFactor(0.6, 5000, 15000)
}

NETWORTH_VALUES = {
    'land': 20,
    'buildings': 5,
    'specs': 5,
    'spywiz': 5
}


def infamy_bonus(infamy, maxbonus):
    """Max plat bonus 0.075, Gems, Ore and Lumber 0.03"""
    return 0.5 * (1 + erf(0.00452 * (infamy - 385))) * maxbonus


class TechTree(object):
    def __init__(self):
        self.techs = self._load_techs()

    def value_for_perk(self, perk_name: str, techs: list):
        perk_techs = self.techs[perk_name]
        return sum([perk_techs[tech] for tech in techs if tech in perk_techs.keys()])

    @staticmethod
    def _load_techs() -> dict:
        with open(f'{REF_DATA_DIR}/techs.yaml', 'r') as f:
            tech_yaml = yaml.safe_load(f)
            techs = defaultdict(dict)
            for tech_name, tech in tech_yaml.items():
                for perk, value in tech['perks'].items():
                    techs[perk][tech_name] = value
        return techs


class Unit(object):
    def __init__(self, yaml_src: dict, dom):
        self._data = yaml_src
        self.dom = dom

    def __str__(self):
        return f"Unit({self.name}, {self.offense}OP, {self.defense}DP)"

    def land_bonus(self, perk_name: str) -> float:
        if self.has_perk(perk_name):
            land_type, percent_per_point, max_bonus = self.get_perk(perk_name)
            return min(float(max_bonus), self.dom.land.perc_of(land_type) / float(percent_per_point))
        else:
            return 0

    @property
    def name(self):
        return self._data['name']

    def has_perk(self, name) -> bool:
        return 'perks' in self._data and name in self._data['perks']

    def get_perk(self, name, default=None):
        if self.has_perk(name):
            perk_value = self._data['perks'][name]
            if isinstance(perk_value, str) and (',' in perk_value):
                return perk_value.split(',')
            else:
                return perk_value
        else:
            return default

    @property
    def cost(self) -> dict:
        return self._data['cost']

    @property
    def offense(self) -> float:
        op = self._data['power']['offense']
        op += self.land_bonus('offense_from_land')
        return op

    @property
    def defense(self) -> float:
        dp = self._data['power']['defense']
        dp += self.land_bonus('defense_from_land')
        return dp

    @property
    def networth(self) -> int:
        op = self.offense
        dp = self.defense
        return 1.8 * min(6, max(op, dp)) + (0.45 * min(6, op, dp)) + (0.2 * (max((op - 6), 0) + max((dp - 6), 0)))

    @property
    def ratios(self) -> dict:
        return {
            'spy_offense': self.get_perk('counts_as_spy_offense', 0),
            'spy_defense': self.get_perk('counts_as_spy_defense', 0),
            'wiz_offense': self.get_perk('counts_as_wizard_offense', 0),
            'wiz_defense': self.get_perk('counts_as_wizard_defense', 0)
        }


class Race(object):
    def __init__(self, name, dom):
        self.name = name
        self.dom = dom
        self.yaml = self._load_data(self.name)
        self.units = dict()
        for i in range(1, 5):
            self.units[i] = Unit(self.yaml['units'][i - 1], dom)

    def _load_data(self, name):
        name = name.replace(' ', '').lower()
        with open(f'{REF_DATA_DIR}/races/{name}.yml', 'r') as f:
            return yaml.safe_load(f)

    def unit(self, nr) -> Unit:
        return self.units[nr]

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

    def has_perk(self, name) -> bool:
        return 'perks' in self.yaml and name in self.yaml['perks']

    def get_perk(self, name, default=None):
        if self.has_perk(name):
            return self.yaml['perks'][name]
        else:
            return default
