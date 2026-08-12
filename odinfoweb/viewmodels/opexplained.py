"""
View model for the "How OP and DP are calculated" page.

The page explains the calculation in the game's own terms. Everything on it that is a
number the tool reads from a data file is passed in from here rather than written into
the template, so the page cannot drift away from what the calculators actually use.
"""

from dataclasses import dataclass

from odinfo.domain.refdata import (Spells, ARES_BONUS, BARRACKS_SPY_FUZZ, BUILD_TICKS,
                                   GN_OFFENSE_BONUS, MAX_GRYPHON_NEST_BONUS,
                                   GT_DEFENSE_FACTOR, MAX_GUARD_TOWER_BONUS,
                                   TEMPLE_BONUS_PER_PERC, MAX_TEMPLE_BONUS)


@dataclass
class BuildingBonusVM:
    """A building whose bonus scales with the share of land it occupies."""
    name: str
    effect: str
    per_percent: float
    max_bonus_percent: float


@dataclass
class AssumedSpellVM:
    """A racial self-spell the tool assumes is up, because it cannot see it."""
    race: str
    offense_percent: float
    defense_percent: float


@dataclass
class OpExplainedVM:
    barracks_spy_error_percent: float
    ares_bonus_percent: float
    build_ticks: int
    buildings: list[BuildingBonusVM]
    assumed_spells: list[AssumedSpellVM]


def _pretty_race(race_key: str) -> str:
    """spells.yml keys a race as 'dark-elf'; players know it as 'Dark Elf'."""
    return race_key.replace('-', ' ').title()


def build_op_explained_vm() -> OpExplainedVM:
    spells = Spells().spells
    offense_spells = spells['offense']
    defense_spells = spells['defense']

    races = sorted(set(offense_spells) | set(defense_spells))
    assumed = [AssumedSpellVM(race=_pretty_race(race),
                              offense_percent=offense_spells.get(race, 0),
                              defense_percent=defense_spells.get(race, 0))
               for race in races if race != 'all']

    return OpExplainedVM(
        # The game shows a barracks spy value somewhere in [true * fuzz, true / fuzz].
        barracks_spy_error_percent=round((1 - BARRACKS_SPY_FUZZ) * 100, 1),
        ares_bonus_percent=round(ARES_BONUS * 100, 1),
        build_ticks=BUILD_TICKS,
        buildings=[
            BuildingBonusVM('Gryphon Nests', 'Offensive power',
                            GN_OFFENSE_BONUS, MAX_GRYPHON_NEST_BONUS * 100),
            BuildingBonusVM('Guard Towers', 'Defensive power',
                            GT_DEFENSE_FACTOR, MAX_GUARD_TOWER_BONUS * 100),
            BuildingBonusVM('Temples', "Target's defensive power reduced by",
                            TEMPLE_BONUS_PER_PERC, MAX_TEMPLE_BONUS * 100),
        ],
        assumed_spells=assumed,
    )