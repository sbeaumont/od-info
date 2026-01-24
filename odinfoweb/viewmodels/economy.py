"""
View models for the economy page.

These view models flatten the Economy calculator data for template consumption.
"""

from dataclasses import dataclass

from odinfo.calculators.economy import Economy
from odinfo.domain.models import Dominion


@dataclass
class EconomyVM:
    """View model for economy page."""
    domcode: int
    domname: str
    employed_peasants: int
    free_jobs: int
    peasant_income: int
    alchemy_income: int
    plat_total_bonus: float
    platinum_production: int
    plat_per_home: float


def build_economy_vm(dom: Dominion) -> EconomyVM:
    """
    Build an EconomyVM from a Dominion object.

    This factory function creates the Economy calculator internally
    and flattens its data into a view model.
    """
    econ = Economy(dom)

    return EconomyVM(
        domcode=dom.code,
        domname=dom.name,
        employed_peasants=econ.employed_peasants,
        free_jobs=econ.free_jobs,
        peasant_income=econ.peasant_income,
        alchemy_income=econ.alchemy_income,
        plat_total_bonus=round(econ.plat_total_bonus * 100, 3),
        platinum_production=econ.platinum_production,
        plat_per_home=round(econ.plat_per_home, 2),
    )