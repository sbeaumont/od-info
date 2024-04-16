from domain.models import Dominion
from config import *
from math import trunc


class Economy(object):
    def __init__(self, dom: Dominion):
        self.dom = dom

    @property
    def plat_total_bonus(self):
        bonus = 0
        # Assuming Midas Touch is up
        bonus += 0.10
        bonus += self.dom.last_castle.science
        bonus += self.dom.tech.value_for_perk('platinum_production') / 100
        return bonus

    @property
    def employed_peasants(self):
        return min(self.dom.cs['peasants'], self.dom.buildings.jobs)

    @property
    def free_jobs(self):
        return self.dom.buildings.jobs - self.dom.cs['peasants']

    @property
    def peasant_income(self):
        return trunc(self.employed_peasants * PLAT_PER_PEASANT_PER_TICK)

    @property
    def plat_per_home(self):
        return (PEASANTS_PER_HOME * (1 + self.dom.castle.keep)) * PLAT_PER_PEASANT_PER_TICK

    @property
    def alchemy_income(self):
        return trunc(self.dom.buildings.alchemies * PLAT_PER_ALCHEMY_PER_TICK)

    @property
    def guard_towers(self):
        gt_ratio = self.dom.buildings.ratio_of('guard_tower') * 1.75
        new_ratio = (self.dom.buildings.guard_towers + 1) / self.dom.total_land * 1.75
        extra_dp_percentage = new_ratio - gt_ratio
        extra_dp = self.dom.military.dp * extra_dp_percentage
        return extra_dp

    @property
    def base_plat_per_tick(self):
        return trunc(self.peasant_income + self.alchemy_income)

    @property
    def platinum_production(self):
        return trunc(self.base_plat_per_tick * (1 + self.plat_total_bonus))


if __name__ == '__main__':
    from opsdata.db import Database

    db = Database()
    db.init(DATABASE)
    # dom = Dominion(db, 10792)
    dom = Dominion(db, current_player_id)
    econ = Economy(dom)

    print(econ.base_plat_per_tick)
    print(econ.plat_total_bonus)
    print(econ.platinum_production)

