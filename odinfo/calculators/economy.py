from sqlalchemy.orm import Session

from odinfo.domain.models import Dominion
from odinfo.config import *
from math import trunc

from odinfo.domain.refdata import GT_DEFENSE_FACTOR


class Economy(object):
    def __init__(self, dom: Dominion):
        self.dom = dom

    @property
    def plat_total_bonus(self):
        bonus = 0
        # Assuming Midas Touch is up
        bonus += 0.10
        bonus += self.dom.last_castle.science_rating
        bonus += self.dom.tech.value_for_perk('platinum_production') / 100
        return bonus

    @property
    def employed_peasants(self):
        return min(self.dom.last_cs.peasants, self.dom.buildings.jobs)

    @property
    def free_jobs(self):
        return self.dom.buildings.jobs - self.dom.cs['peasants']

    @property
    def peasant_income(self):
        return trunc(self.employed_peasants * PLAT_PER_PEASANT_PER_TICK)

    @property
    def plat_per_home(self):
        if self.dom.last_castle:
            return (PEASANTS_PER_HOME * (1 + self.dom.last_castle.keep_rating)) * PLAT_PER_PEASANT_PER_TICK
        else:
            return -1

    @property
    def alchemy_income(self):
        return trunc(self.dom.last_survey.alchemy * PLAT_PER_ALCHEMY_PER_TICK)

    @property
    def guard_towers(self):
        gt_ratio = self.dom.buildings.ratio_of('guard_tower') * GT_DEFENSE_FACTOR
        new_ratio = (self.dom.buildings.ratio_of('guard_tower') + 1) / self.dom.land.total * GT_DEFENSE_FACTOR
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
    from sqlalchemy import create_engine, select

    db_name = DATABASE_NAME[:10] + 'instance/' + DATABASE_NAME[10:]
    print(db_name)
    with Session(create_engine(db_name)) as session:
        dom = session.execute(select(Dominion).where(Dominion.code == current_player_id)).scalar()
        econ = Economy(dom)

        print("Base plat per tick", econ.base_plat_per_tick)
        print("Plat total bonus", econ.plat_total_bonus)
        print("Platinum production", econ.platinum_production)

