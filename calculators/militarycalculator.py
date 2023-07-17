from calculators.networthcalculator import NETWORTH_VALUES




# class Military(object):
#     def __init__(self, ops):
#         self.ops = ops
#
#     def amount(self, unit_type_nr) -> float:
#         observations = list()
#         observations.append(self.ops.q(f'status.military_unit{unit_type_nr}'))
#         if self.ops.q_exists(f'barracks.units.home.unit{unit_type_nr}'):
#             observations.append(self.ops.q(f'barracks.units.home.unit{unit_type_nr}'))
#         return min(observations) * 1.15
#
#     @property
#     def offense(self) -> int:
#         offense = 0
#
#         offense += self.amount(1) * self.ops.race.def_spec.offense
#         offense += self.amount(2) * self.ops.race.off_spec.offense
#         offense += self.amount(3) * self.ops.race.def_elite.offense
#         offense += self.amount(4) * self.ops.race.off_elite.offense
#
#         offense_bonus = 1 + (float(self.ops.techtree.value_for_perk('offense', self.ops.techs)) / 100)
#         offense *= offense_bonus
#
#         if self.ops.castle.exists():
#             offense *= 1 + self.ops.castle.forges
#         else:
#             print("No Castle Spy")
#
#         return round(offense)


class MilitaryCalculator(object):
    def __init__(self, ops):
        self.ops = ops

    def spywiz_estimate(self) -> int:
        networth = self.ops.q('status.networth')
        networth -= self.ops.land * NETWORTH_VALUES['land']
        networth -= self.ops.buildings.total * NETWORTH_VALUES['buildings']

        networth -= self.ops.military.amount(1) * NETWORTH_VALUES['specs']
        networth -= self.ops.military.amount(2) * NETWORTH_VALUES['specs']
        networth -= self.ops.military.amount(3) * self.ops.race.def_elite.networth
        networth -= self.ops.military.amount(4) * self.ops.race.off_elite.networth

        return round(networth / NETWORTH_VALUES['spywiz'])
