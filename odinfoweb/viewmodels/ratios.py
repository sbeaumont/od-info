"""
View models for the ratios page.
"""

from dataclasses import dataclass

from odinfo.calculators.military import RatioCalculator
from odinfo.domain.models import Dominion
from odinfo.timeutils import hours_since


@dataclass
class RatioRowVM:
    """View model for a row in the ratios list."""
    code: int
    name: str
    realm: int
    land: int
    race: str
    networth: int
    wpa: float | None
    spa: float | None
    ops_age: float


def build_ratio_list_vm(dominions: list[Dominion], max_ops_age: int = 100) -> list[RatioRowVM]:
    """
    Build a list of RatioRowVM from dominions.

    Filters out dominions that can't be calculated or have ops older than max_ops_age.
    Returns list sorted by spa descending.
    """
    result = []
    for dom in dominions:
        rc = RatioCalculator(dom)
        ops_age = hours_since(dom.last_op)
        if rc.can_calculate and ops_age < max_ops_age:
            result.append(RatioRowVM(
                code=dom.code,
                name=dom.name,
                realm=dom.realm,
                land=dom.current_land,
                race=dom.race,
                networth=dom.current_networth,
                wpa=dom.current_wpa,
                spa=rc.spy_ratio_actual,
                ops_age=ops_age,
            ))

    return sorted(result, key=lambda r: r.spa or 0, reverse=True)