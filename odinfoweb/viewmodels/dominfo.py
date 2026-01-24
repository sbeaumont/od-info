"""
View models for the dominfo (single dominion) page.

These view models flatten the MilitaryCalculator and RatioCalculator
data for template consumption.
"""

from dataclasses import dataclass

from odinfo.calculators.military import MilitaryCalculator, RatioCalculator
from odinfo.domain.models import Dominion
from odinfo.timeutils import hours_since


@dataclass
class UnitRowVM:
    """View model for a single unit row in the military breakdown."""
    name: str
    amount: int
    offense_per_unit: float
    defense_per_unit: float
    raw_op: int
    raw_dp: int
    offense_missing_intel: bool
    defense_missing_intel: bool


@dataclass
class OffenseBonusesVM:
    """View model for offense bonus breakdown."""
    prestige: float
    racial: float
    buildings: float  # Gryphon Nest
    improvements: float  # Forges
    tech: float
    spell: float
    total: float


@dataclass
class DefenseBonusesVM:
    """View model for defense bonus breakdown."""
    racial: float
    buildings: float  # Guard Tower
    improvements: float  # Walls
    tech: float
    spell: float  # +Ares
    total: float


@dataclass
class FiveOverFourUnitVM:
    """View model for a unit in the 5/4 breakdown."""
    unit_name: str
    unit_type: str
    amount_sent: int
    amount_home: int
    op_contribution: int
    dp_lost: int
    dp_contribution: int


@dataclass
class FiveOverFourBreakdownVM:
    """View model for the complete 5/4 attack breakdown."""
    sent_units: list[FiveOverFourUnitVM]
    stayed_home_units: list[FiveOverFourUnitVM]
    sendable_op: int
    remaining_dp: int
    is_valid: bool


@dataclass
class MilitaryInfoVM:
    """View model for military info on dominfo page."""
    # Main stats
    op: int
    raw_op: int
    dp: int
    raw_dp: int
    five_over_four_op: int
    five_over_four_dp: int
    draftees: int
    total_units: int

    # Bonuses
    offense_bonuses: OffenseBonusesVM
    defense_bonuses: DefenseBonusesVM

    # Unit breakdown
    units: list[UnitRowVM]

    # 5/4 breakdown
    five_over_four_breakdown: FiveOverFourBreakdownVM


@dataclass
class RatioInfoVM:
    """View model for ratio info on dominfo page."""
    spy_units_equiv: int | None
    spy_ratio_estimate: float | None
    max_spy_ratio_estimate: float | None
    wiz_units_equiv: int | None
    wiz_ratio_estimate: float | None
    max_wiz_ratio_estimate: float | None
    spywiz_networth: int | None
    spywiz_units: int | None


@dataclass
class DomInfoVM:
    """Combined view model for the dominfo page."""
    # Basic info (from Dominion)
    code: int
    name: str
    realm: int
    race: str
    land: int
    networth: int
    population: int | None
    ops_age: float

    # Castle ratings
    science_rating: float | None
    keep_rating: float | None
    spires_rating: float | None
    forges_rating: float | None

    # Temple ratio
    temple_ratio: float | None

    # Sub view models
    military: MilitaryInfoVM
    ratios: RatioInfoVM


def build_dominfo_vm(dom: Dominion) -> DomInfoVM:
    """
    Build a DomInfoVM from a Dominion object.

    This factory function creates all the necessary calculators internally
    and flattens their data into view models.
    """
    mc = MilitaryCalculator(dom)
    rc = RatioCalculator(dom)

    # Build unit rows
    units = []
    for i in range(1, 5):
        unit_type = mc.unit_type(i)
        missing = mc.unit_missing_intel(i)
        units.append(UnitRowVM(
            name=unit_type.name,
            amount=mc.amount(i),
            offense_per_unit=round(unit_type.offense, 1),
            defense_per_unit=round(unit_type.defense, 1),
            raw_op=round(mc.op_of(i)),
            raw_dp=round(mc.dp_of(i)),
            offense_missing_intel=missing['offense'],
            defense_missing_intel=missing['defense'],
        ))

    # Build offense bonuses
    offense_bonuses = OffenseBonusesVM(
        prestige=round(mc.prestige_bonus * 100, 2),
        racial=round(mc.racial_offense_bonus * 100, 2),
        buildings=round(mc.gryphon_nest_bonus * 100, 2),
        improvements=round(mc.forges_bonus * 100, 2),
        tech=round(mc.tech_offense_bonus * 100, 2),
        spell=round(mc.spell_offense_bonus * 100, 2),
        total=round(mc.offense_bonus * 100, 2),
    )

    # Build defense bonuses
    defense_bonuses = DefenseBonusesVM(
        racial=round(mc.racial_defense_bonus * 100, 2),
        buildings=round(mc.guard_tower_bonus * 100, 2),
        improvements=round(mc.walls_bonus * 100, 2),
        tech=round(mc.tech_defense_bonus * 100, 2),
        spell=round(mc.spell_defense_bonus * 100, 2),
        total=round(mc.defense_bonus * 100, 2),
    )

    # Build 5/4 breakdown
    breakdown = mc.five_over_four_breakdown()
    sent_units = [
        FiveOverFourUnitVM(
            unit_name=u['unit_name'],
            unit_type=u['unit_type'],
            amount_sent=u['amount_sent'],
            amount_home=u['amount_home'],
            op_contribution=round(u['op_contribution']),
            dp_lost=round(u['dp_lost']),
            dp_contribution=0,
        )
        for u in breakdown['sent']
    ]
    stayed_home_units = [
        FiveOverFourUnitVM(
            unit_name=u['unit_name'],
            unit_type=u['unit_type'],
            amount_sent=0,
            amount_home=u['amount_home'],
            op_contribution=0,
            dp_lost=0,
            dp_contribution=round(u['dp_contribution']),
        )
        for u in breakdown['stayed_home']
    ]
    sendable_op = round(breakdown['summary']['sendable_op'])
    remaining_dp = round(breakdown['summary']['remaining_dp'])
    is_valid = sendable_op <= round(remaining_dp * 5 / 4)

    five_over_four_breakdown = FiveOverFourBreakdownVM(
        sent_units=sent_units,
        stayed_home_units=stayed_home_units,
        sendable_op=sendable_op,
        remaining_dp=remaining_dp,
        is_valid=is_valid,
    )

    # Build military info
    five_four = mc.five_over_four
    military = MilitaryInfoVM(
        op=round(mc.op),
        raw_op=round(mc.raw_op),
        dp=round(mc.dp),
        raw_dp=round(mc.raw_dp),
        five_over_four_op=round(five_four[0]),
        five_over_four_dp=round(five_four[1]),
        draftees=mc.draftees,
        total_units=mc.total_units,
        offense_bonuses=offense_bonuses,
        defense_bonuses=defense_bonuses,
        units=units,
        five_over_four_breakdown=five_over_four_breakdown,
    )

    # Build ratio info
    ratios = RatioInfoVM(
        spy_units_equiv=rc.spy_units_equiv,
        spy_ratio_estimate=rc.spy_ratio_estimate,
        max_spy_ratio_estimate=rc.max_spy_ratio_estimate,
        wiz_units_equiv=rc.wiz_units_equiv,
        wiz_ratio_estimate=rc.wiz_ratio_estimate,
        max_wiz_ratio_estimate=rc.max_wiz_ratio_estimate,
        spywiz_networth=rc.spywiz_networth,
        spywiz_units=rc.spywiz_units,
    )

    # Castle ratings
    castle = dom.last_castle
    science_rating = round(castle.science_rating, 3) if castle else None
    keep_rating = round(castle.keep_rating, 3) if castle else None
    spires_rating = round(castle.spires_rating, 3) if castle else None
    forges_rating = round(castle.forges_rating, 3) if castle else None

    # Temple ratio
    temple_ratio = round(dom.buildings.ratio_of('temple') * 100, 1) if dom.buildings else None

    # Population
    population = dom.last_cs.peasants if dom.last_cs else None

    return DomInfoVM(
        code=dom.code,
        name=dom.name,
        realm=dom.realm,
        race=dom.race,
        land=dom.current_land,
        networth=dom.current_networth,
        population=population,
        ops_age=hours_since(dom.last_op),
        science_rating=science_rating,
        keep_rating=keep_rating,
        spires_rating=spires_rating,
        forges_rating=forges_rating,
        temple_ratio=temple_ratio,
        military=military,
        ratios=ratios,
    )