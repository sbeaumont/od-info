import yaml
from collections import defaultdict, namedtuple
from config import REF_DATA_DIR

NON_HOME_CAPACITY = 15
BUILD_TICKS = 12
MASONRY_MULTIPLIER = 2.75

ImpFactor = namedtuple('ImpFactor', 'max factor plus')

IMP_FACTORS = {
    'science': ImpFactor(0.2, 4000, 15000),
    'keep': ImpFactor(0.3, 4000, 15000),
    'spires': ImpFactor(0.6, 5000, 15000),
    'forges': ImpFactor(0.3, 7500, 15000),
    'walls': ImpFactor(0.3, 7500, 15000),
    'harbor': ImpFactor(0.6, 5000, 15000)
}


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
    def __init__(self, yaml_src: dict, ops):
        self.src = yaml_src
        self.ops = ops

    def land_bonus(self, perk_name: str) -> float:
        if self.has_perk(perk_name) and self.ops.has_land:
            land_type, percent_per_point, max_bonus = self.get_perk(perk_name)
            return min(float(max_bonus), self.ops.q(f'land.explored.{land_type}.percentage') / float(percent_per_point))
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
