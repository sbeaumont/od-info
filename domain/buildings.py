import json
from math import trunc
from collections import defaultdict

from domain.unknown import Unknown
from opsdata.schema import query_survey

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
    'forest_haven',
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
        if self._data['constructing']:
            cons = json.loads(self._data['constructing'])
            for name, ticks in cons.items():
                self._constructing[name] = sum(ticks.values())

    def __str__(self):
        buildings = [f"{t}:{self._data[t]}" for t in NON_HOME_TYPES]
        buildings.append(f"home:{self.homes}")
        return f"Buildings({'|'.join(buildings)})"

    @property
    def alchemies(self):
        return self._data['alchemy']

    @property
    def barren(self):
        return self._data['barren_land']

    @property
    def homes(self) -> int:
        return self._data['home']

    @property
    def masons(self) -> int:
        return self._data['masonry']

    @property
    def guard_towers(self) -> int:
        return self._data['guard_tower']

    @property
    def temples(self) -> int:
        return self._data['temple']

    @property
    def non_homes(self) -> int:
        return sum([int(self._data[n]) for n in NON_HOME_TYPES])

    @property
    def jobs(self) -> int:
        return sum([int(self._data[n]) for n in JOB_TYPES]) * JOBS_PER_BUILDING

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

    def perc_of(self, building_type: str) -> float:
        return self._data[building_type] / self.dom.total_land


def buildings_for(db, dom):
    data = query_survey(db, dom.code, latest=True)
    if data:
        return Buildings(dom, data)
    else:
        return Unknown()
