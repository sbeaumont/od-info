"""
View models for military-related views.

View models are data transfer objects that represent the data needed
by templates. They provide:
- Type safety through dataclasses
- Clear interface between service layer and templates
- Potential for computed/formatted properties
"""

from dataclasses import dataclass


@dataclass
class MilitaryRowVM:
    """View model for a single row in the military overview table."""
    code: int
    name: str
    realm: int
    race: str
    ops_age: float
    land: int
    hittable_75_percent: int
    five_over_four_op: int
    five_over_four_dp: int
    five_four_op_with_temples: int
    temples: float
    boats_amount: int
    boats_prt: int
    boats_sendable: int
    boats_capacity: int
    paid_until: str
    draftees: int
    raw_op: int
    op: int
    raw_dp: int
    dp: int
    safe_op: int
    safe_dp: int
    safe_op_with_temples: int
    networth: int
    has_incomplete_intel: bool

    @property
    def temples_percent(self) -> float:
        """Temple bonus as a percentage, rounded to 1 decimal."""
        return round(self.temples * 100, 1)


@dataclass
class RealmieRowVM:
    """View model for a single row in the realmies overview."""
    code: int
    name: str
    player: str | None
    land: int
    hittable_75_percent: int
    max_sendable_op: int
    dp: int
    wpa: float | None
    spa: float | None
    docks: int | None
    boats_protected: float
    boats_total: float
    ares: int | None