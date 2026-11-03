"""
View models for the About pages.

Numbers these pages quote are read from the data files rather than written into the
templates, so the explanation cannot drift away from what the tool actually does.
"""

from dataclasses import dataclass

from odinfo.config import (NW_PERIODS, NW_DEFAULT_PERIOD, NW_ROW_COUNTS,
                           NW_UNCHANGED_DEFAULT, THREAT_MAX_TRIGGERS)
from odinfo.domain.refdata import BUILD_TICKS, CONQUEST_LAND_FACTOR, DAILY_LAND_BONUS, LAND_ARRIVAL_TICKS
from odinfo.services.report_service import BOT_REALM, TOP_BOTTOM_COUNT
from odinfoweb.viewmodels.targets import MIN_RANGE, MAX_RANGE


@dataclass
class PhilosophyVM:
    build_ticks: int


def build_philosophy_vm() -> PhilosophyVM:
    return PhilosophyVM(build_ticks=BUILD_TICKS)


@dataclass
class NWTrackerVM:
    periods: tuple[int, ...]
    row_counts: tuple[int, ...]
    unchanged_default: int
    top_bottom_count: int
    discord_period: int
    bot_realm: int


def build_nw_tracker_vm() -> NWTrackerVM:
    return NWTrackerVM(periods=NW_PERIODS,
                       row_counts=NW_ROW_COUNTS,
                       unchanged_default=NW_UNCHANGED_DEFAULT,
                       top_bottom_count=TOP_BOTTOM_COUNT,
                       discord_period=NW_DEFAULT_PERIOD,
                       bot_realm=BOT_REALM)


@dataclass
class ThreatsExplainedVM:
    horizon: int
    min_range: int
    max_range: int
    daily_land_bonus: int
    conquest_land_factor: int
    land_arrival_ticks: int
    max_triggers: int


def build_threats_explained_vm() -> ThreatsExplainedVM:
    return ThreatsExplainedVM(horizon=BUILD_TICKS,
                              min_range=MIN_RANGE,
                              max_range=MAX_RANGE,
                              daily_land_bonus=DAILY_LAND_BONUS,
                              conquest_land_factor=CONQUEST_LAND_FACTOR,
                              land_arrival_ticks=LAND_ARRIVAL_TICKS,
                              max_triggers=THREAT_MAX_TRIGGERS)