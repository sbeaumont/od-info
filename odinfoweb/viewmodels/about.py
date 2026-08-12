"""
View models for the About pages.

Numbers these pages quote are read from the data files rather than written into the
templates, so the explanation cannot drift away from what the tool actually does.
"""

from dataclasses import dataclass

from odinfo.config import (NW_PERIODS, NW_DEFAULT_PERIOD, NW_ROW_COUNTS,
                           NW_UNCHANGED_DEFAULT)
from odinfo.domain.refdata import BUILD_TICKS
from odinfo.services.report_service import BOT_REALM, TOP_BOTTOM_COUNT


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