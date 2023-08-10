from opsdata.schema import query_barracks
from domain.unknown import Unknown
from domain.refdata import GT_DEFENSE_FACTOR
from domain.refdata import NETWORTH_VALUES


class Military(object):
    def __init__(self, dom, data):
        self.dom = dom
        self._data = data

    def __str__(self):
        unit_txt = [f"{self.amount(i)} {self.unit_type(i).name} {self.unit_type(i).offense}/{self.unit_type(i).defense}" for i in range(1, 5)]
        return f"Military({'|'.join(unit_txt)}, {self.op}OP, {self.dp}DP)"

    def unit_type(self, nr):
        return self.dom.race.unit(nr)

    def amount(self, unit_type_nr) -> float:
        return self.dom.cs[f'military_unit{unit_type_nr}']

    def op_of(self, unit_type_nr):
        return self.amount(unit_type_nr) * self.unit_type(unit_type_nr).offense

    def dp_of(self, unit_type_nr):
        return self.amount(unit_type_nr) * self.unit_type(unit_type_nr).defense

    @property
    def spies(self) -> int:
        return self.dom.cs['military_spies']

    @property
    def assassins(self) -> int:
        return self.dom.cs['military_assassins']

    @property
    def wizards(self) -> int:
        return self.dom.cs['military_wizards']

    @property
    def archmages(self) -> int:
        return self.dom.cs['military_archmages']

    @property
    def op(self):
        offense = 0
        offense += sum([self.op_of(i) for i in range(1, 5)])

        offense_bonus = 1 + (float(self.dom.tech.value_for_perk('offense')) / 100)
        offense *= offense_bonus

        offense *= 1 + self.dom.castle.forges

        return round(offense)

    @property
    def dp(self):
        defense = 0
        defense += sum([self.dp_of(i) for i in range(1, 5)])
        defense += self.dom.cs['military_draftees']

        tech_bonus = 1 + (float(self.dom.tech.value_for_perk('defense')) / 100)
        defense *= tech_bonus

        gt_bonus = 1 + (self.dom.buildings.guard_towers / self.dom.land.total * GT_DEFENSE_FACTOR)
        defense *= gt_bonus

        defense *= 1 + self.dom.castle.walls

        return round(defense)

    @property
    def spywiz_networth(self) -> float:
        networth = self.dom.networth
        networth -= self.dom.total_land * NETWORTH_VALUES['land']
        networth -= self.dom.buildings.total * NETWORTH_VALUES['buildings']

        networth -= self.dom.military.amount(1) * NETWORTH_VALUES['specs']
        networth -= self.dom.military.amount(2) * NETWORTH_VALUES['specs']
        networth -= self.dom.military.amount(3) * self.dom.race.def_elite.networth
        networth -= self.dom.military.amount(4) * self.dom.race.off_elite.networth
        return round(networth, 1)

    @property
    def spywiz_units(self) -> int:
        return round(self.spywiz_networth / NETWORTH_VALUES['spywiz'])

    @property
    def ratio_estimate(self) -> float:
        return round(self.spywiz_units / (2 * self.dom.total_land), 3)

    @property
    def max_ratio_estimate(self) -> float:
        return round(self.spywiz_units / self.dom.total_land, 3)


def military_for(db, dom):
    data = query_barracks(db, dom.code, latest=True)
    if data:
        return Military(dom, data)
    else:
        return Unknown()

