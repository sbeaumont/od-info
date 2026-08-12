"""
View models for the About pages.

Numbers these pages quote are read from the data files rather than written into the
templates, so the explanation cannot drift away from what the tool actually does.
"""

from dataclasses import dataclass

from odinfo.domain.refdata import BUILD_TICKS


@dataclass
class PhilosophyVM:
    build_ticks: int


def build_philosophy_vm() -> PhilosophyVM:
    return PhilosophyVM(build_ticks=BUILD_TICKS)