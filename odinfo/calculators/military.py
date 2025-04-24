import time
import logging
from math import trunc

from odinfo.domain.models import Dominion
from odinfo.domain.refdata import Race
from odinfo.domain.refdata import GT_DEFENSE_FACTOR, GN_OFFENSE_BONUS, Unit, Spells
from odinfo.domain.refdata import NETWORTH_VALUES, ARES_BONUS

logger = logging.getLogger('od-info.military')


class MilitaryCalculator(object):
    def __init__(self, dom: Dominion):
        self.dom = dom
        self.race = Race(dom, dom.race)
        self.army = dom.military
        self.navy = dom.navy
        self.spells = None
        self._five_four_op = None
        self._five_four_dp = None

    def __str__(self):
        unit_txt = [f"{self.amount(i)} {self.unit_type(i).name} {self.unit_type(i).offense}/{self.unit_type(i).defense}" for i in range(1, 5)]
        return f"Military({'|'.join(unit_txt)}, {self.op}OP, {self.dp}DP)"

    def unit_type(self, unit_nr: int) -> Unit:
        return self.race.unit(unit_nr)

    def amount(self, unit_nr: int) -> int:
        if self.army:
            return trunc(self.army[f'unit{unit_nr}'])
        else:
            return 0

    @property
    def hittable_75_percent(self):
        return trunc(self.dom.current_land * 3 / 4)

    def op_of(self, unit_nr: int, with_bonus=False, partial_amount=None):
        assert isinstance(unit_nr, int)
        amount = partial_amount if partial_amount else self.amount(unit_nr)
        op = amount * self.unit_type(unit_nr).offense

        # Pairing perk (e.g. kobold)
        if self.unit_type(unit_nr).has_perk('offense_from_pairing'):
            slot, op_buff, num_required = self.unit_type(unit_nr).get_perk('offense_from_pairing')
            pairable_amount = min(self.amount(int(slot)) // int(num_required), amount)
            op += pairable_amount * int(op_buff)

        return (op * (1 + self.offense_bonus)) if with_bonus else op

    def dp_of(self, unit_nr: int, with_bonus=False, partial_amount=None):
        amount = partial_amount if partial_amount else self.amount(unit_nr)
        dp = amount * self.unit_type(unit_nr).defense

        # Pairing perk (e.g. kobold)
        if self.unit_type(unit_nr).has_perk('defense_from_pairing'):
            slot, buff, num_required = self.unit_type(unit_nr).get_perk('defense_from_pairing')
            pairable_amount = min(self.amount(int(slot)) // int(num_required), amount)
            dp += pairable_amount * int(buff)

        return (dp * (1 + self.defense_bonus)) if with_bonus else dp

    def boats(self, current_day: int):
        """Return [boats, docks (protected boats), sendable units, total boat capacity]"""
        if self.navy:
            protected_boats = self.navy['docks'] * (2.25 + current_day * 0.05)
            units_per_boat = 30 + self.race.get_perk('boat_capacity', 0)
            total_sendable_units = sum([self.amount(self.race.nr_of_unit(u)) for u in self.race.sendable_units if u.need_boat])
            return (round(self.navy['boats'], 1),
                    round(protected_boats, 1),
                    trunc(total_sendable_units),
                    trunc(self.navy['boats'] * units_per_boat))
        else:
            return 0, 0, 0, 0

    def spell_bonus(self, race: str, perk_name: str):
        if not self.spells:
            self.spells = Spells()
        return self.spells.value_for_perk(race.lower(), perk_name)

    @property
    def temple_bonus(self) -> float:
        if self.dom.buildings:
            return self.dom.buildings.ratio_of('temple')
        else:
            return 0

    @property
    def five_four_op_with_temples(self) -> float:
        """The effective OP that a defender has to compare their DP with to see if they're safe."""
        logger.debug(f"Calculating five four op with temples: {self.five_over_four[0] / (1 - self.temple_bonus)}")
        return round(self.five_over_four[0] / (1 - self.temple_bonus))

    @property
    def gryphon_nest_bonus(self) -> float:
        if self.dom.buildings:
            return self.dom.buildings.ratio_of('gryphon_nest') * GN_OFFENSE_BONUS
        else:
            return 0

    @property
    def guard_tower_bonus(self) -> float:
        if self.dom.buildings:
            return self.dom.buildings.ratio_of('guard_tower') * GT_DEFENSE_FACTOR
        else:
            return 0

    @property
    def racial_offense_bonus(self) -> float:
        """Racial offense bonus as a decimal"""
        return self.race.get_perk('offense', 0) / 100

    @property
    def spell_offense_bonus(self) -> float:
        """Spell offense bonus as a decimal"""
        return self.spell_bonus(self.dom.race, 'offense') / 100

    @property
    def tech_offense_bonus(self) -> float:
        """Tech offense bonus as a decimal"""
        return float(self.dom.tech.value_for_perk('offense')) / 100

    @property
    def forges_bonus(self) -> float | None:
        """Forges bonus as a decimal"""
        return self.dom.last_castle.forges_rating if self.dom.last_castle else 0

    @property
    def prestige_bonus(self) -> float | None:
        """Prestige bonus as a decimal"""
        return (self.dom.last_cs.prestige / 10000) if self.dom.last_cs else 0

    @property
    def offense_bonus(self) -> float:
        bonus = 0
        bonus += self.racial_offense_bonus
        bonus += self.spell_offense_bonus
        # bonus += self.spell_bonus(self.dom.race.name, 'offense_from_barren_land') / 100
        bonus += self.tech_offense_bonus
        bonus += self.forges_bonus
        bonus += self.gryphon_nest_bonus
        bonus += self.prestige_bonus
        return bonus

    @property
    def racial_defense_bonus(self):
        return self.race.get_perk('defense', 0) / 100

    @property
    def spell_defense_bonus(self):
        """Spell defense bonus as a decimal, assuming Ares is up as well."""
        return (self.spell_bonus(self.race.name, 'defense') / 100) + ARES_BONUS

    @property
    def tech_defense_bonus(self):
        return float(self.dom.tech.value_for_perk('defense')) / 100

    @property
    def walls_bonus(self) -> float | None:
        """Walls bonus as a decimal"""
        return self.dom.last_castle.walls_rating if self.dom.last_castle else 0

    @property
    def defense_bonus(self) -> float:
        """Defense bonus as a decimal"""
        bonus = 0
        bonus += self.racial_defense_bonus
        bonus += self.spell_defense_bonus
        bonus += self.tech_defense_bonus
        bonus += self.walls_bonus
        bonus += self.guard_tower_bonus
        return bonus

    @property
    def raw_op(self) -> int:
        return sum([self.op_of(i) for i in range(1, 5)])

    @property
    def op(self) -> int:
        return round(self.raw_op * (1 + self.offense_bonus))

    @property
    def draftees(self) -> int:
        return self.dom.last_cs.military_draftees if self.dom.last_cs else 0

    @property
    def total_units(self) -> int:
        return sum([self.amount(i) for i in range(1, 5)]) + self.draftees

    @property
    def raw_dp(self) -> int:
        defense = 0
        defense += sum([self.dp_of(i) for i in range(1, 5)])
        defense += self.draftees
        return defense

    @property
    def dp(self) -> int:
        return round(self.raw_dp * (1 + self.defense_bonus))

    @property
    def max_sendable_op(self) -> int:
        return min((self.safe_op, self.five_over_four[0]))

    @property
    def safe_op(self) -> int:
        """Only calc based on attack units (types 1 & 4)"""
        # Correct for weird races like Troll
        if self.race.name in ('Troll', ):
            return self.five_over_four[0]

        offense = self.op_of(1)
        offense += self.op_of(4)
        offense *= 1 + self.offense_bonus
        return round(offense)

    @property
    def safe_dp(self) -> int:
        """Only calc based on defense units (types 2 & 3)"""
        # Correct for weird races like Troll
        if self.race.name in ('Troll', ):
            return self.five_over_four[1]

        defense = self.dp_of(2)
        defense += self.dp_of(3)
        defense *= 1 + self.defense_bonus
        return round(defense)

    def safe_op_versus(self, enemy_op: int) -> tuple[int, int]:
        start = time.time()
        # First subtract power of all pure DP units
        dp_at_home = sum([self.dp_of(self.race.nr_of_unit(u), with_bonus=True) for u in self.race.pure_defense_units])
        dp_at_home += self.army['draftees'] * (1 + self.defense_bonus)
        op_to_defend = int(enemy_op) - dp_at_home

        # Pure offense units don't contribute to defense, can always send
        safe_op = sum([self.op_of(self.race.nr_of_unit(u), with_bonus=True) for u in self.race.pure_offense_units])

        # Check the hybrid units
        # Most defensive hybrids first
        for unit_type in self.race.hybrids_by_dp:
            unit_nr = self.race.nr_of_unit(unit_type)
            if op_to_defend <= 0:
                # Can use all these units to attack
                units_needed = 0
                dp_of_units_needed = 0
                can_send_op = self.op_of(unit_nr, with_bonus=True)
            else:
                units_needed = (op_to_defend // (unit_type.defense * (1 + self.defense_bonus))) + 1
                if units_needed < self.amount(unit_nr):
                    # Only need part of these hybrid units
                    dp_of_units_needed = self.dp_of(unit_nr, partial_amount=units_needed, with_bonus=True)
                    # Can attack with the rest
                    remaining_units = self.amount(unit_nr) - units_needed
                    can_send_op = self.op_of(unit_nr, with_bonus=True, partial_amount=remaining_units)
                else:
                    # Need all these units to contribute to DP
                    dp_of_units_needed = self.dp_of(unit_nr, with_bonus=True)
                    can_send_op = 0
            op_to_defend -= dp_of_units_needed
            dp_at_home += dp_of_units_needed
            safe_op += can_send_op
        end = time.time()
        logger.debug(f"Execution time of safe_op_versus: {end - start} for dom {self.dom.code}")
        return trunc(safe_op), round(dp_at_home)

    @property
    def flex_unit(self) -> Unit | None:
        if not hasattr(self, '_flex_unit'):
            fu = None
            pure_offense = sum([self.op_of(self.race.nr_of_unit(u)) for u in self.race.pure_offense_units])
            sendable_offense = pure_offense
            home_defense = self.dp
            hybrid_units_sendable = dict()
            for unit_type in self.race.hybrid_units:
                unit_nr = self.race.nr_of_unit(unit_type)
                if self.amount(unit_nr) > 0:
                    new_op = sendable_offense + self.op_of(unit_nr, True)
                    new_dp = home_defense - self.dp_of(unit_nr, True)
                    if new_op <= (1.25 * new_dp):
                        # Can send all of these units
                        hybrid_units_sendable[unit_type] = self.amount(unit_nr)
                        sendable_offense += self.op_of(unit_nr, True)
                        home_defense -= self.dp_of(unit_nr, True)
                    else:
                        # Found the flex units
                        fu = unit_type
                        break
            self._flex_unit = fu
        return self._flex_unit

    @property
    def five_over_four(self) -> tuple:
        if not self._five_four_dp:
            logger.debug(f"Starting five_over_four for dom {self.dom.code} {self.dom.race} {self.dom.name}")
            if self.flex_unit:
                flex_unit_nr = self.race.nr_of_unit(self.flex_unit)
                total_flex = self.amount(flex_unit_nr)
                non_flex_op = self.op - self.op_of(flex_unit_nr, with_bonus=True)
                alpha_op = self.flex_unit.offense
                alpha_dp = self.flex_unit.defense
                flex_to_send = trunc(((5/4 * self.dp) - non_flex_op) / (alpha_op + (5/4 * alpha_dp)))
                logger.debug(f"Flex unit is {self.flex_unit.name}: can send {flex_to_send} of {total_flex}")
                if flex_to_send < 0:
                    flex_to_send = 0
                self._five_four_dp = round(self.dp - self.dp_of(flex_unit_nr, with_bonus=True, partial_amount=flex_to_send))
                self._five_four_op = round(non_flex_op + self.op_of(flex_unit_nr, with_bonus=True ,partial_amount=flex_to_send))
            else:
                logger.debug(f"No flex unit available for {self}")
                self._five_four_op = trunc(self.op)
                dp = self.dp
                for unit_type in self.race.hybrid_units:
                    dp -= self.dp_of(self.race.nr_of_unit(unit_type), True)
                self._five_four_dp = trunc(dp)
            logger.debug(f"op: {self._five_four_op}, 5/4 dp: {self._five_four_dp * 5 / 4}")
            if self._five_four_op > (round(self._five_four_dp * 5/4, 2)):
                logger.warning(f"op: {self._five_four_op}, 5/4 dp: {round(self._five_four_dp * 5/4, 2)}, correcting OP to {self._five_four_dp * 5/4}")
                self._five_four_op = round(self._five_four_dp * 5/4)
        return round(self._five_four_op), round(self._five_four_dp)


class RatioCalculator(object):
    def __init__(self, dom: Dominion):
        self.dom = dom
        self.race = Race(dom, dom.race)
        self.army = dom.military

    @property
    def can_calculate(self) -> bool:
        return ((self.army is not None) and
                (self.dom.buildings is not None))

    def amount(self, unit_nr: int) -> int:
        # return self.army.get(f'unit{unit_nr}', 0) * BS_UNCERTAINTY
        return self.army.get(f'unit{unit_nr}', 0)

    @property
    def land(self) -> int:
        return self.dom.current_land

    @property
    def buildings(self) -> int:
        return self.dom.buildings.total

    @property
    def spywiz_networth(self) -> float:
        networth = self.dom.current_networth
        networth -= self.land * NETWORTH_VALUES['land']
        networth -= self.buildings * NETWORTH_VALUES['buildings']

        networth -= self.amount(1) * NETWORTH_VALUES['specs']
        networth -= self.amount(2) * NETWORTH_VALUES['specs']
        networth -= self.amount(3) * self.race.unit(3).networth
        networth -= self.amount(4) * self.race.unit(4).networth
        return round(networth, 1)

    @property
    def spywiz_units(self) -> int:
        return round(self.spywiz_networth / NETWORTH_VALUES['spywiz'])

    @property
    def ratio_estimate(self) -> float:
        return round(self.spywiz_units / (2 * self.land), 3)

    @property
    def max_ratio_estimate(self) -> float:
        return round(self.spywiz_units / self.land, 3)

    @property
    def spy_ratio_estimate(self) -> float:
        return round(self.ratio_estimate + (self.spy_units_equiv / self.land), 3)

    @property
    def max_spy_ratio_estimate(self) -> float:
        return round(self.max_ratio_estimate + (self.spy_units_equiv / self.land), 3)

    @property
    def wiz_ratio_estimate(self) -> float:
        return round(self.ratio_estimate + (self.wiz_units_equiv / self.land), 3)

    @property
    def max_wiz_ratio_estimate(self) -> float:
        return round(self.max_ratio_estimate + (self.wiz_units_equiv / self.land), 3)

    @property
    def spy_units_equiv(self) -> int:
        result = 0
        for i in range(1, 5):
            unit_ratios = self.race.unit(i).ratios
            spy_per_unit = max(unit_ratios['spy_offense'], unit_ratios['spy_defense'])
            result += trunc(self.amount(i) * spy_per_unit)
        return result

    @property
    def wiz_units_equiv(self) -> int:
        result = 0
        for i in range(1, 5):
            unit_ratios = self.race.unit(i).ratios
            wiz_per_unit = max(unit_ratios['wiz_offense'], unit_ratios['wiz_defense'])
            result += trunc(self.amount(i) * wiz_per_unit)
        return result


if __name__ == '__main__':
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite:///instance/odinfo-draft-round-2.sqlite", echo=False)
    with Session(engine) as session:
        stmt = select(Dominion).where(Dominion.code == 14288)
        dom = session.scalars(stmt).one()
        rc = RatioCalculator(dom)
        print("Military Spy Units Equivalent", rc.spy_units_equiv)
        print("Military Wiz Units Equivalent", rc.wiz_units_equiv)
        print("Wiz Ratio Estimate", rc.max_wiz_ratio_estimate)
        for i in range(1, 5):
            print("unit", i, rc.amount(i))
        mc = MilitaryCalculator(dom)
        op54, dp54 = mc.five_over_four
        print("5/4", op54, dp54)
        print("OP/DP", mc.op, mc.dp)
        print("5/4 of 5/4 DP", (5/4)*dp54)
        print("5/4 with Temples", mc.op_with_temples)

