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

