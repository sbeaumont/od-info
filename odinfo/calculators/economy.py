from math import trunc

from sqlalchemy.orm import Session

from odinfo.domain.models import Dominion
from odinfo.config import PLAT_PER_ALCHEMY_PER_TICK, PLAT_PER_PEASANT_PER_TICK, PEASANTS_PER_HOME
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
    def base_plat_per_tick(self):
        return trunc(self.peasant_income + self.alchemy_income)

    @property
    def platinum_production(self):
        return trunc(self.base_plat_per_tick * (1 + self.plat_total_bonus))


if __name__ == '__main__':
    from sqlalchemy import create_engine, select
    from odinfo.config import get_config

    config = get_config()
    db_name = config.database_name[:10] + 'instance/' + config.database_name[10:]
    print(db_name)
    with Session(create_engine(db_name)) as session:
        dom = session.execute(select(Dominion).where(Dominion.code == config.current_player_id)).scalar()
        econ = Economy(dom)

        print("Base plat per tick", econ.base_plat_per_tick)
        print("Plat total bonus", econ.plat_total_bonus)
        print("Platinum production", econ.platinum_production)

