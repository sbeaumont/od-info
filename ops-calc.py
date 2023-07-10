from collections import namedtuple, defaultdict
from math import exp, trunc
import json
import yaml

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


class Castle(object):
    def __init__(self, ops):
        self.ops = ops

    def imp_formula(self, ops_field, imp_name):
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
        self.techs = techs

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


class Building(object):
    def __init__(self, built=0, capacity=NON_HOME_CAPACITY):
        self.built = built
        self.constructing = {i: 0 for i in range(1, BUILD_TICKS + 1)}
        self.capacity = capacity

    @property
    def total_capacity(self):
        return (self.built * self.capacity) + (sum(self.constructing.values()) * NON_HOME_CAPACITY)


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
    with open('ref-data/techs.yaml', 'r') as f:
        tech_yaml = yaml.safe_load(f)
        techs = defaultdict(dict)
        for tech_name, tech in tech_yaml.items():
            for perk, value in tech['perks'].items():
                techs[perk][tech_name] = value
    print(techs)
    return techs


def main():
    with open('ops-data/copy_ops.txt', 'r') as f:
        ops = Ops(json.load(f), load_techs())
    buildings = Buildings(ops)

    print(f"Keep bonus       {pc(ops.castle.keep)}% ({ops.castle.keep})")
    print(f"(Mason bonus     {pc(ops.castle.mason_bonus)}% ({ops.castle.mason_bonus}))")
    print(f"Tech bonus       {pc(ops.population_tech_bonus)}% ({ops.population_tech_bonus})")
    print(f"Wonder bonus     {pc(ops.wonder_bonus)}% {ops.wonder_bonus}")
    print()
    print(f"Prestige bonus   {pc(ops.prestige_bonus)}% ({ops.prestige_bonus})")
    print()
    print(f"Population bonus {pc(ops.population_bonus - 1, digits=3)}% ({ops.population_bonus - 1})")
    print()
    print("Non homes    ", buildings.non_homes)
    print("Homes        ", buildings.homes)
    print("Constructing ", buildings.constructing)
    print("Barren       ", buildings.barren)
    print("Total        ", buildings.total)
    print("Land         ", ops.land)
    print()
    print("Raw capacity   ", buildings.raw_capacity)
    print("Total capacity ", buildings.total_capacity)


if __name__ == '__main__':
    main()
