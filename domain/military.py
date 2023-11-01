import json
import logging
from math import trunc

from opsdata.schema import query_barracks, hours_since
from domain.unknown import Unknown
from domain.refdata import GT_DEFENSE_FACTOR, GN_OFFENSE_BONUS, Unit
from domain.refdata import NETWORTH_VALUES, BS_UNCERTAINTY, ARES_BONUS

logger = logging.getLogger('od-info.military')


class Military(object):
    def __init__(self, dom, data):
        self.dom = dom
        self._data = data

    def __str__(self):
        unit_txt = [f"{self.amount(i)} {self.unit_type(i).name} {self.unit_type(i).offense}/{self.unit_type(i).defense}" for i in range(1, 5)]
        return f"Military({'|'.join(unit_txt)}, {self.op}OP, {self.dp}DP)"

    def unit_type(self, unit_or_nr) -> Unit:
        if isinstance(unit_or_nr, Unit):
            return unit_or_nr
        else:
            return self.dom.race.unit(unit_or_nr)

    def amount(self, unit_or_nr, include_paid=True) -> int:
        unit_type_nr = self.dom.race.nr_of_unit(unit_or_nr)
        total = 0
        if not isinstance(self.dom.cs, Unknown):
            total += trunc(self.dom.cs[f'military_unit{unit_type_nr}'])
        else:
            total += trunc(self._data[f'home_unit{unit_type_nr}'] * BS_UNCERTAINTY)
            total += self.coming_home(unit_type_nr)
        if include_paid:
            total += self.in_training(unit_type_nr)
        return total

    def in_training(self, unit_type_nr: int) -> int:
        tr = json.loads(self._data['training'])
        key = f'unit{unit_type_nr}'
        if key in tr:
            return sum(tr[key].values())
        else:
            return 0

    @property
    def paid_until(self) -> int:
        age = hours_since(self._data['timestamp'])
        training = json.loads(self._data['training'])
        max_ticks = 0
        for i in range(1, 5):
            key = f'unit{i}'
            if key in training:
                max_ticks = max(max_ticks, max([int(t) for t in training[key]]))
        return max(0, max_ticks - age)

    @property
    def hittable_75_percent(self):
        return trunc(self.dom.total_land * 3 / 4)

    def coming_home(self, unit_type_nr: int) -> int:
        tr = json.loads(self._data['return'])
        key = f'unit{unit_type_nr}'
        if key in tr:
            return sum(tr[key].values())
        else:
            return 0

    def op_of(self, unit_type_or_nr, with_bonus=False, partial_amount=None):
        amount = partial_amount if partial_amount else self.amount(unit_type_or_nr)
        op = amount * self.unit_type(unit_type_or_nr).offense
        return (op * (1 + self.offense_bonus)) if with_bonus else op

    def dp_of(self, unit_type_or_nr, with_bonus=False, partial_amount=None):
        amount = partial_amount if partial_amount else self.amount(unit_type_or_nr)
        dp = amount * self.unit_type(unit_type_or_nr).defense
        return (dp * (1 + self.defense_bonus)) if with_bonus else dp

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
    def offense_bonus(self):
        bonus = 0
        # Racial offense bonus
        bonus += self.dom.race.get_perk('offense', 0) / 100
        # Tech bonus
        bonus += float(self.dom.tech.value_for_perk('offense')) / 100
        # Forges bonus
        bonus += self.dom.castle.forges
        # Gryphon Nest bonus
        bonus += self.dom.buildings.ratio_of('gryphon_nest') * GN_OFFENSE_BONUS
        # Prestige Bonus
        bonus += self.dom.cs['prestige'] / 10000
        return bonus

    @property
    def max_sendable_op(self) -> int:
        return min((self.safe_op, self.five_over_four_op[0]))

    @property
    def op(self) -> int:
        offense = sum([self.op_of(i) for i in range(1, 5)])
        offense *= 1 + self.offense_bonus
        return round(offense)

    @property
    def safe_op(self) -> int:
        """Only calc based on attack units (types 1 & 4)"""
        offense = self.op_of(1)
        offense += self.op_of(4)
        offense *= 1 + self.offense_bonus
        return round(offense)

    @property
    def safe_dp(self) -> int:
        """Only calc based on defense units (types 2 & 3)"""
        defense = self.dp_of(2)
        defense += self.dp_of(3)
        defense *= 1 + self.defense_bonus
        return round(defense)

    def safe_op_versus(self, enemy_op: int) -> tuple[int, int]:
        # logger.debug(f'Checking safe OP/DP for {self.dom.name} ({self.dp} DP) vs {enemy_op} OP')
        # First subtract power of all pure DP units
        # logger.debug(f'Pure defense units: {[(str(u), self.amount(u)) for u in self.dom.race.pure_defense_units]}, {self.defense_bonus}')
        dp_at_home = sum([self.dp_of(u, with_bonus=True) for u in self.dom.race.pure_defense_units])
        dp_at_home += self.dom.cs['military_draftees'] * (1 + self.defense_bonus)
        op_to_defend = enemy_op - dp_at_home

        # Pure offense units don't contribute to defense, can always send
        # logger.debug(f'Pure offense units: {[str(u) for u in self.dom.race.pure_offense_units]}')
        safe_op = sum([self.op_of(u, with_bonus=True) for u in self.dom.race.pure_offense_units])

        # logger.debug(f'Pure defense and attack: {round(safe_op)} OP / {round(dp_at_home)} DP, remaining {round(op_to_defend)}')

        # Check the hybrid units
        # logger.debug(f'Hybrid units: {[str(u) for u in self.dom.race.hybrids_by_dp]}')
        # Most defensive hybrids first
        for unit_type in self.dom.race.hybrids_by_dp:
            if op_to_defend <= 0:
                # Can use all these units to attack
                units_needed = 0
                dp_of_units_needed = 0
                can_send_op = self.op_of(unit_type, with_bonus=True)
            else:
                units_needed = (op_to_defend // (unit_type.defense * (1 + self.defense_bonus))) + 1
                if units_needed < self.amount(unit_type):
                    # Only need part of these hybrid units
                    dp_of_units_needed = self.dp_of(unit_type, partial_amount=units_needed, with_bonus=True)
                    # Can attack with the rest
                    remaining_units = self.amount(unit_type) - units_needed
                    can_send_op = self.op_of(unit_type, with_bonus=True, partial_amount=remaining_units)
                    # logger.debug(f"Only need {round(units_needed)} units for {round(dp_of_units_needed)} DP, can send {round(can_send_op)} OP")
                else:
                    # Need all these units to contribute to DP
                    dp_of_units_needed = self.dp_of(unit_type, with_bonus=True)
                    can_send_op = 0
                    # logger.debug(f"Needed all ({self.amount(unit_type)}) of {unit_type} for {round(dp_of_units_needed)} DP, can send {round(can_send_op)} OP")
            op_to_defend -= dp_of_units_needed
            dp_at_home += dp_of_units_needed
            safe_op += can_send_op
            # logger.debug(f'Hybrid unit {unit_type}: needed {round(units_needed)} @ {round(dp_of_units_needed)}DP for {round(safe_op)} OP / {round(dp_at_home)} DP, remaining {round(op_to_defend)}')
        return trunc(safe_op), round(dp_at_home)

    @property
    def five_over_four_op(self) -> tuple:
        pure_offense = sum([self.op_of(u) for u in self.dom.race.pure_offense_units])
        sendable_offense = pure_offense
        home_defense = self.dp
        hybrid_units_sendable = dict()
        for unit_type in self.dom.race.hybrid_units:
            new_op = sendable_offense + self.op_of(unit_type, True)
            new_dp = home_defense - self.dp_of(unit_type, True)
            if new_op <= (1.25 * new_dp):
                # Can send all of these units
                hybrid_units_sendable[unit_type] = self.amount(unit_type)
                sendable_offense += self.op_of(unit_type, True)
                home_defense -= self.dp_of(unit_type, True)
            else:
                # Can only send part
                for i in range(1, self.amount(unit_type)):
                    new_op = sendable_offense + self.op_of(unit_type, with_bonus=True, partial_amount=i)
                    new_dp = home_defense - self.dp_of(unit_type, with_bonus=True, partial_amount=i)
                    if new_op > (1.25 * new_dp):
                        sendable = i - 1
                        hybrid_units_sendable[unit_type] = sendable
                        break
                break
        hybrid_op = sum([self.op_of(u, partial_amount=a) for u, a in hybrid_units_sendable.items()])
        total_op = trunc((pure_offense + hybrid_op) * (1 + self.offense_bonus))
        hybrid_dp = sum([self.dp_of(u, partial_amount=a) for u, a in hybrid_units_sendable.items()])
        total_dp = trunc(self.dp - (hybrid_dp * (1 + self.defense_bonus)))
        return total_op, total_dp

    @property
    def defense_bonus(self) -> float:
        """Defense bonus as a decimal"""
        bonus = 0
        # Racial bonus
        bonus += self.dom.race.get_perk('defense', 0) / 100
        # Tech bonus
        bonus += float(self.dom.tech.value_for_perk('defense')) / 100
        # Walls bonus
        bonus += self.dom.castle.walls
        # Guard Tower bonus
        bonus += self.dom.buildings.ratio_of('guard_tower') * GT_DEFENSE_FACTOR
        # Ares Bonus (assume it's up unless proven not to be)
        # if not isinstance(self.dom.magic, Unknown) and not self.dom.magic.ares:
        #     # Proven not to be up
        #     pass
        # else:
        #     # Assume it's up
        bonus += ARES_BONUS
        return bonus

    @property
    def dp(self) -> int:
        defense = 0
        defense += sum([self.dp_of(i) for i in range(1, 5)])
        defense += self.dom.cs['military_draftees']
        defense *= 1 + self.defense_bonus
        return round(defense)

    @property
    def spywiz_networth(self) -> float:
        networth = self.dom.networth
        networth -= self.dom.total_land * NETWORTH_VALUES['land']
        networth -= self.dom.buildings.total * NETWORTH_VALUES['buildings']

        networth -= self.amount(1, include_paid=False) * NETWORTH_VALUES['specs']
        networth -= self.amount(2, include_paid=False) * NETWORTH_VALUES['specs']
        networth -= self.amount(3, include_paid=False) * self.dom.race.unit(3).networth
        networth -= self.amount(4, include_paid=False) * self.dom.race.unit(4).networth
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

    @property
    def spy_ratio_estimate(self) -> float:
        return round(self.ratio_estimate + (self.spy_units_equiv / self.dom.total_land), 3)

    @property
    def max_spy_ratio_estimate(self) -> float:
        return round(self.max_ratio_estimate + (self.spy_units_equiv / self.dom.total_land), 3)

    @property
    def wiz_ratio_estimate(self) -> float:
        return round(self.ratio_estimate + (self.wiz_units_equiv / self.dom.total_land), 3)

    @property
    def max_wiz_ratio_estimate(self) -> float:
        return round(self.max_ratio_estimate + (self.wiz_units_equiv / self.dom.total_land), 3)

    @property
    def spy_units_equiv(self):
        spy_units_equiv = 0
        for i in range(1, 5):
            unit_ratios = self.unit_type(i).ratios
            spy_per_unit = max(unit_ratios['spy_offense'], unit_ratios['spy_defense'])
            spy_units_equiv += trunc(self.amount(i, include_paid=False) * spy_per_unit)
        return spy_units_equiv

    @property
    def wiz_units_equiv(self) -> int:
        wiz_units_equiv = 0
        for i in range(1, 5):
            unit_ratios = self.unit_type(i).ratios
            wiz_per_unit = max(unit_ratios['wiz_offense'], unit_ratios['wiz_defense'])
            wiz_units_equiv += trunc(self.amount(i, include_paid=False) * wiz_per_unit)
        return wiz_units_equiv


def military_for(db, dom) -> Military | Unknown:
    data = query_barracks(db, dom.code, latest=True)
    if data:
        return Military(dom, data)
    else:
        return Unknown()
