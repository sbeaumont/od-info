from collections import namedtuple, defaultdict
from math import exp, trunc
from pprint import pprint
import json
import yaml

from scrapetools import get_soup_page, read_tick_time, login
from config import REF_DATA_DIR, SEARCH_PAGE, OP_CENTER_URL

NON_HOME_CAPACITY = 15
BUILD_TICKS = 12

ImpFactor = namedtuple('ImpFactor', 'max factor plus')
IMP_FACTORS = {
    'science': ImpFactor(0.2, 4000, 15000),
    'keep': ImpFactor(0.3, 4000, 15000),
    'spires': ImpFactor(0.6, 5000, 15000),
    'forges': ImpFactor(0.3, 7500, 15000),
    'walls': ImpFactor(0.3, 7500, 15000),
    'harbor': ImpFactor(0.6, 5000, 15000)
}
MASONRY_MULTIPLIER = 2.75

NETWORTH_VALUES = {
    'land': 20,
    'buildings': 5,
    'specs': 5,
    'spywiz': 5
}


class Race(object):
    def __init__(self, name: str):
        with open(f'{REF_DATA_DIR}/races/{name}.yml', 'r') as f:
            self.yaml = yaml.safe_load(f)

    @property
    def def_elite(self):
        return self.yaml['units'][2]

    @property
    def off_elite(self):
        return self.yaml['units'][3]

    def has_perk(self, unit, name):
        return 'perks' in unit and name in unit['perks']

    def get_perk(self, unit, name):
        if self.has_perk(unit, name):
            return unit['perks'][name].split(',')
        else:
            return None

    def elite_unit_networth(self, unit, ops):
        """(1.8 * min(6, max(OP, DP))) + (0.45 * min(6, OP, DP))) + (0.2 * (max((OP - 6), 0) + max((DP - 6), 0)))"""
        def land_bonus(unit, perk_name: str) -> float:
            if self.has_perk(unit, perk_name):
                land_type, percent_per_point, max_bonus = self.get_perk(unit, perk_name)
                return min(float(max_bonus), ops.q(f'land.explored.{land_type}.percentage') / float(percent_per_point))
            else:
                return 0

        dp = unit['power']['defense']
        dp += land_bonus(unit, 'defense_from_land')

        op = unit['power']['offense']
        op += land_bonus(unit, 'offense_from_land')

        return (1.8 * min(6, max(op, dp))) + (0.45 * min(6, op, dp)) + (0.2 * (max((op - 6), 0) + max((dp - 6), 0)))


class Castle(object):
    def __init__(self, ops):
        self.ops = ops

    def imp_formula(self, ops_field: str, imp_name: str) -> int:
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
    def mason_bonus(self):
        return self.ops.q('survey.constructed.masonry') / self.ops.land * MASONRY_MULTIPLIER


class Ops(object):
    def __init__(self, contents, techs):
        self.contents = contents
        self.castle = Castle(self)
        self.race = Race(self.q('status.race_name'))
        self.techs = techs
        self.buildings = Buildings(self)

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
    def population_tech_bonus(self):
        result = 0
        pop_techs = self.techs['max_population']
        for tech in self.q('vision.techs').keys():
            if tech in pop_techs.keys():
                result += pop_techs[tech] / 100
        return result

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

    def dom_networth(self) -> int:
        networth = 0
        networth += self.land * NETWORTH_VALUES['land']
        networth += self.buildings.total * NETWORTH_VALUES['buildings']

        networth += self.q('status.military_unit1') * NETWORTH_VALUES['specs']
        networth += self.q('status.military_unit2') * NETWORTH_VALUES['specs']
        networth += self.q('status.military_unit3') * race.elite_unit_networth(self.race.def_elite, ops)
        networth += self.q('status.military_unit4') * race.elite_unit_networth(self.race.off_elite, ops)

        networth += self.q('status.military_spies') * NETWORTH_VALUES['spywiz']
        networth += self.q('status.military_assassins') * NETWORTH_VALUES['spywiz']
        networth += self.q('status.military_wizards') * NETWORTH_VALUES['spywiz']
        networth += self.q('status.military_archmages') * NETWORTH_VALUES['spywiz']
        return round(networth)

    def spywiz_estimate(self) -> int:
        networth = self.q('status.networth')
        networth -= self.land * NETWORTH_VALUES['land']
        networth -= self.buildings.total * NETWORTH_VALUES['buildings']

        networth -= self.q('status.military_unit1') * NETWORTH_VALUES['specs']
        networth -= self.q('status.military_unit2') * NETWORTH_VALUES['specs']
        networth -= self.q('status.military_unit3') * self.race.elite_unit_networth(ops.race.def_elite, ops)
        networth -= self.q('status.military_unit4') * self.race.elite_unit_networth(ops.race.off_elite, ops)

        return round(networth / NETWORTH_VALUES['spywiz'])


class Buildings(object):
    def __init__(self, ops):
        self.ops = ops
        self.constructed = self.ops.q('survey.constructed')

    @property
    def total(self):
        return self.homes + self.non_homes

    @property
    def raw_capacity(self):
        homes = self.homes * 30
        non_homes = self.non_homes * 15
        constructing = self.constructing * 15
        barren = self.barren * 5
        return homes + non_homes + constructing + barren

    @property
    def total_capacity(self):
        return trunc(self.raw_capacity * self.ops.population_bonus)

    @property
    def homes(self):
        return self.ops.q('home', self.constructed)

    @property
    def non_homes(self):
        return sum([int(v) for k, v in self.constructed.items() if k != 'home'])

    @property
    def constructing(self):
        constructing = 0
        for b in self.ops.q('survey.constructing').values():
            for t in b.values():
                constructing += int(t)
        return constructing

    @property
    def barren(self):
        return self.ops.q('land.totalBarrenLand')


def pc(nr, digits=2):
    return round(nr * 100, digits)


def load_techs():
    with open(f'{REF_DATA_DIR}/techs.yaml', 'r') as f:
        tech_yaml = yaml.safe_load(f)
        techs = defaultdict(dict)
        for tech_name, tech in tech_yaml.items():
            for perk, value in tech['perks'].items():
                techs[perk][tech_name] = value
    return techs


def create_ops(ops_json):
    return Ops(ops_json, load_techs())


def load_ops(file_name):
    with open(file_name, 'r') as f:
        return create_ops(json.load(f))


def get_ops(session, dom_code: str):
    soup = get_soup_page(session, f'{OP_CENTER_URL}/{dom_code}')
    ops_json = soup.find('textarea', id='ops_json').string
    return create_ops(json.loads(ops_json))


def print_ops(ops: Ops):
    print(f"Population bonus {pc(ops.population_bonus - 1, digits=3)}% ({ops.population_bonus - 1})")
    print("Total capacity ", ops.buildings.total_capacity)


def grab_search(session) -> list:
    soup = get_soup_page(session, SEARCH_PAGE)
    server_time = read_tick_time(soup)

    search_lines = list()
    for row in soup.find(id='dominions-table').tbody.find_all('tr'):
        cells = row.find_all('td')
        dom_name = cells[0].a.string
        dom_code = cells[0].a['href'].split('/')[-1]
        realm_code = cells[1].a['href'].split('/')[-1]
        dom_race = cells[2].string.strip()
        dom_pop = int(cells[3].string.strip().replace(',', ''))
        dom_networth = int(cells[4].string.strip().replace(',', ''))
        in_range = cells[5].string.strip()
        parsed_row = (str(server_time), dom_name, dom_code, realm_code, dom_race, dom_pop, dom_networth, in_range)
        search_lines.append(parsed_row)
    return search_lines


if __name__ == '__main__':
    session = login()
    ops = get_ops(session, "10551")
    pprint(ops)
    print_ops(ops)
