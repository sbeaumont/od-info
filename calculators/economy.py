from domain.dominion import Dominion
from config import current_player_id


class Economy(object):
    def __init__(self, dom: Dominion):
        self.dom = dom

    @property
    def plat_total_bonus(self):
        bonus = 0
        # Assuming Midas Touch is up
        bonus += 0.10
        bonus += self.dom.castle.science
        bonus += self.dom.tech.value_for_perk('platinum_production') / 100
        return bonus

    @property
    def base_plat_per_tick(self):
        employed_peasants = min(self.dom.cs['peasants'], self.dom.buildings.jobs)
        peasants_income = employed_peasants * PLAT_PER_PEASANT_PER_TICK
        alchemies_income = self.dom.buildings.alchemies * PLAT_PER_ALCHEMY_PER_TICK
        return peasants_income + alchemies_income

    @property
    def platinum_production(self):
        return self.base_plat_per_tick * (1 + self.plat_total_bonus)


if __name__ == '__main__':
    from opsdata.db import Database
    from config import DATABASE, PLAT_PER_ALCHEMY_PER_TICK, PLAT_PER_PEASANT_PER_TICK

    db = Database()
    db.init(DATABASE)
    # dom = Dominion(db, 10792)
    dom = Dominion(db, current_player_id)
    econ = Economy(dom)

    print(econ.base_plat_per_tick)
    print(econ.plat_total_bonus)
    print(econ.platinum_production)

