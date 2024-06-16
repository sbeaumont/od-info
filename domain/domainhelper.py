from collections import defaultdict
from datetime import timedelta
from math import trunc, exp

from domain.refdata import TechTree, MASONRY_MULTIPLIER, IMP_FACTORS
from domain.timeutils import hours_until

NON_HOME_TYPES = (
    'alchemy',
    'farm',
    'smithy',
    'masonry',
    'ore_mine',
    'gryphon_nest',
    'tower',
    'wizard_guild',
    'temple',
    'diamond_mine',
    'school',
    'lumberyard',
    'factory',
    'guard_tower',
    'shrine',
    'barracks',
    'dock'
)
JOB_TYPES = [t for t in NON_HOME_TYPES if t != 'barracks']
JOBS_PER_BUILDING = 20
POP_PER_HOME = 30
POP_PER_NON_HOME = 15
POP_PER_BARREN = 5


class Buildings(object):
    def __init__(self, dom, data):
        self.dom = dom
        self._data = data
        self._constructing = defaultdict(int)
        if self._data and self._data.constructing:
            cons = self._data.constructing
            for name, ticks in cons.items():
                self._constructing[name] = sum(ticks.values())

    def __str__(self):
        buildings = [f"{t}:{self._data[t]}" for t in NON_HOME_TYPES]
        buildings.append(f"home:{self.homes}")
        return f"Buildings({'|'.join(buildings)})"

    @property
    def homes(self) -> int:
        return self._data.home

    @property
    def non_homes(self) -> int:
        return sum([getattr(self._data, n) for n in NON_HOME_TYPES])

    @property
    def barren(self) -> int:
        return self._data.barren

    @property
    def jobs(self) -> int:
        return sum([getattr(self._data, n) for n in JOB_TYPES]) * JOBS_PER_BUILDING

    @property
    def total(self) -> int:
        return self.homes + self.non_homes

    @property
    def raw_capacity(self) -> int:
        homes = self.homes * POP_PER_HOME
        non_homes = self.non_homes * POP_PER_NON_HOME
        constructing = self.constructing * POP_PER_NON_HOME
        barren = self.barren * 5
        return homes + non_homes + constructing + barren

    @property
    def total_capacity(self) -> int:
        return trunc(self.raw_capacity * self.dom.population_bonus)

    @property
    def constructing(self) -> int:
        return sum(self._constructing.values())

    def ratio_of(self, building_type: str, include_paid=True) -> float:
        if self._data:
            nr_of_buildings = getattr(self._data, building_type)
            amount_of_land = self.dom.current_land
            if include_paid:
                nr_of_buildings += self._constructing[building_type]
                if self.dom.land:
                    amount_of_land += self.dom.land.incoming
            return nr_of_buildings / amount_of_land
        else:
            return 0


LAND_TYPES = (
    'plain',
    'mountain',
    'swamp',
    'cavern',
    'forest',
    'hill',
    'water'
)


class Land(object):
    def __init__(self, dom, data):
        self.dom = dom
        self._data = data

    def __str__(self):
        lands = [f"{t}:{getattr(self._data, t)}" for t in LAND_TYPES]
        return f"Land({'|'.join(lands)})"

    @property
    def total(self):
        return self._data.total if self._data else 0

    def ratio_of(self, land_type: str) -> float:
        if self._data:
            return getattr(self._data, land_type) / self.dom.current_land * 100
        else:
            return 0

    @property
    def incoming(self) -> int:
        result = 0
        if self._data and self._data.incoming:
            incoming = self._data.incoming
            for landtype in LAND_TYPES:
                if landtype in incoming:
                    result += sum(incoming[landtype].values())
        return result


class Technology(object):
    def __init__(self, dom):
        self.dom = dom
        self.tech_tree = TechTree()

    @property
    def researched(self):
        return self.dom.last_vision.techs if self.dom.last_vision else None

    @property
    def pop_bonus(self):
        return self.value_for_perk('max_population')

    def value_for_perk(self, perk_name):
        if self.researched:
            return self.tech_tree.value_for_perk(perk_name, self.researched)
        else:
            return 0


class Castle(object):
    def __init__(self, dom, data):
        self._data = data
        self.dom = dom

    @property
    def mason_bonus(self) -> float:
        return self.dom.buildings.masons / self.dom.land.total * MASONRY_MULTIPLIER

    def imp_formula(self, ops_field: str, imp_name: str) -> float:
        points = self._data(ops_field)
        maximum, factor, plus = IMP_FACTORS[imp_name]
        return round(maximum * (1 - exp(-points/(factor * self.dom.land.total + plus))) * (1 + self.mason_bonus), 4)


class Magic(object):
    def __init__(self, dom, data):
        self.dom = dom
        self.spells = data

    @property
    def ares(self) -> int | None:
        for spell in self.spells:
            if spell.spell == 'ares_call':
                return hours_until(spell.timestamp + timedelta(hours=spell.duration))
        return None
