"""
View models for the overview page.
"""

from dataclasses import dataclass

from odinfo.domain.models import Dominion
from odinfo.timeutils import hours_since


@dataclass
class OverviewRowVM:
    """View model for a row in the overview list."""
    code: int
    name: str
    race: str
    realm: int
    land: int
    networth: int
    player: str
    role: str
    ops_age: float
    nw_delta: int


def build_overview_list_vm(
    dominions: list[Dominion],
    nw_deltas: dict[int, int]
) -> list[OverviewRowVM]:
    """
    Build a list of OverviewRowVM from dominions.

    Returns list sorted by land descending.
    """
    result = []
    for dom in dominions:
        result.append(OverviewRowVM(
            code=dom.code,
            name=dom.name,
            race=dom.race,
            realm=dom.realm,
            land=dom.current_land,
            networth=dom.current_networth,
            player=dom.player or '',
            role=dom.role or 'unknown',
            ops_age=hours_since(dom.last_op),
            nw_delta=nw_deltas.get(dom.code, 0),
        ))

    return sorted(result, key=lambda r: r.land, reverse=True)