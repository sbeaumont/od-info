import math
import logging
from operator import attrgetter

import yaml
from math import erf
from enum import Enum
from collections import defaultdict, namedtuple
from odinfo.config import REF_DATA_DIR
from functools import lru_cache


logger = logging.getLogger('od-info.refdata')


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


class SendableType(Enum):
    PURE_DEFENSE = 1
    PURE_OFFENSE = 2
    HYBRID = 3


def infamy_bonus(infamy, maxbonus) -> float:
    """Max plat bonus 0.075, Gems, Ore and Lumber 0.03"""
    return 0.5 * (1 + erf(0.00452 * (infamy - 385))) * maxbonus


class Spells(object):
    SPELL_REGISTRY: dict | None = None

    """Loads the offense and defense perks only."""
    def __init__(self):
        self.spells = self._load_spells()

    def value_for_perk(self, race: str, perk_name: str):
        return self.spells[perk_name].get(race, 0)

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_spells() -> dict:
        if not Spells.SPELL_REGISTRY:
            with open(f'{REF_DATA_DIR}/spells.yml', 'r') as f:
                spell_yaml = yaml.safe_load(f)
                spells = defaultdict(dict)
                for spell_name, spell in spell_yaml.items():
                    for perk, value in spell['perks'].items():
                        for race in spell.get('races', ['all']):
                            spells[perk][race] = spells[perk].get(race, 0) + value
            Spells.SPELL_REGISTRY = spells
        return Spells.SPELL_REGISTRY


class TechTree(object):
    TECHS_REGISTRY: dict | None = None

    def __init__(self):
        self.techs = self._load_techs()

    def value_for_perk(self, perk_name: str, techs: list):
        perk_techs = self.techs[perk_name]
        return sum([perk_techs[tech] for tech in techs if tech in perk_techs.keys()])

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_techs() -> dict:
        if not TechTree.TECHS_REGISTRY:
            with open(f'{REF_DATA_DIR}/techs.yml', 'r') as f:
                tech_yaml = yaml.safe_load(f)
                techs = defaultdict(dict)
                for tech_name, tech in tech_yaml['techs'].items():
                    for perk, value in tech['perks'].items():
                        techs[perk][tech_name] = value
            TechTree.TECHS_REGISTRY = techs
        return TechTree.TECHS_REGISTRY


class Unit(object):
    def __init__(self, yaml_src: dict, dom):
        self._data = yaml_src
        self.dom = dom

    def __str__(self):
        return f"Unit({self.name}, {self.offense}OP, {self.defense}DP)"

    def land_bonus(self, perk_name: str) -> float:
        if self.dom.land and self.has_perk(perk_name):
            land_type, percent_per_point, max_bonus = self.get_perk(perk_name)
            return min(float(max_bonus), self.dom.land.ratio_of(land_type) / float(percent_per_point))
        else:
            return 0

    @property
    def name(self) -> str:
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
    def need_boat(self):
        return self._data.get('need_boat', True)

    @property
    def sendable_type(self) -> SendableType:
        if (self.offense != 0) and (self.defense != 0):
            return SendableType.HYBRID
        elif self.offense == 0:
            return SendableType.PURE_DEFENSE
        elif self.defense == 0:
            return SendableType.PURE_OFFENSE

    @property
    def op_over_dp(self) -> float:
        if self.offense == 0:
            return 0
        elif self.defense == 0:
            return math.inf
        else:
            return self.offense / self.defense

    @property
    def cost(self) -> dict:
        return self._data['cost']

    @property
    def offense(self) -> float:
        op = self._data['power']['offense']
        op += self.land_bonus('offense_from_land')
        if self.has_perk('offense_raw_wizard_ratio'):
            per_percent, max_bonus = self.get_perk('offense_raw_wizard_ratio')
            if self.dom.last_cs and self.dom.last_cs.wpa:
                wpa = float(self.dom.last_cs.wpa)
                wpa_bonus = wpa * float(per_percent)
                if wpa_bonus > float(max_bonus):
                    wpa_bonus = float(max_bonus)
                op += wpa_bonus
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
    RACE_REGISTRY: dict = dict()

    def __init__(self, dom, name: str):
        assert isinstance(name, str)
        self.name = name
        self.dom = dom
        self.yaml = self._load_race_data(self.name)
        self.units = dict()
        self.reverse_units = dict()
        for i in range(1, 5):
            unit = Unit(self.yaml['units'][i - 1], dom)
            self.units[i] = unit
            self.reverse_units[unit] = i

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_race_data(name) -> dict:
        if name not in Race.RACE_REGISTRY:
            logger.debug(f'Cache miss for race {name}')
            name = name.replace(' ', '').lower()
            with open(f'{REF_DATA_DIR}/races/{name}.yml', 'r') as f:
                Race.RACE_REGISTRY[name] = yaml.safe_load(f)
        return Race.RACE_REGISTRY[name]

    def unit(self, nr: int) -> Unit:
        return self.units[nr]

    def nr_of_unit(self, unit) -> int:
        if isinstance(unit, int):
            return unit
        return self.reverse_units[unit]

    def has_perk(self, name) -> bool:
        return 'perks' in self.yaml and name in self.yaml['perks']

    def get_perk(self, name, default=None):
        if self.has_perk(name):
            return self.yaml['perks'][name]
        else:
            return default

    @property
    def hybrid_units(self) -> list[Unit]:
        return sorted([u for u in self.units.values() if u.sendable_type == SendableType.HYBRID], key=attrgetter('op_over_dp'), reverse=True)

    @property
    def hybrids_by_dp(self) -> list[Unit]:
        assert len(self.hybrid_units) + len(self.pure_offense_units) + len(self.pure_defense_units) == len(self.units)
        return sorted(self.hybrid_units, key=attrgetter('defense'), reverse=True)

    @property
    def pure_offense_units(self) -> list[Unit]:
        return [u for u in self.units.values() if u.sendable_type == SendableType.PURE_OFFENSE]

    @property
    def sendable_units(self) -> list[Unit]:
        return self.pure_offense_units + self.hybrids_by_dp

    @property
    def pure_defense_units(self) -> list[Unit]:
        return [u for u in self.units.values() if u.sendable_type == SendableType.PURE_DEFENSE]


if __name__ == '__main__':
    sp = Spells()
    print(sp.spells)
    print(sp.value_for_perk('orc', 'offense'))