"""
Helpers for the Town Crier scraper.
"""

from odinfo.exceptions import ODInfoException


def expect_not_none(result, description: str):
    """Fail loudly when a BS4 lookup that should have matched returned None.

    Wrap any find()/find_parent()/select_one()/etc. call whose None result
    would otherwise cause a confusing AttributeError downstream. The
    description is what makes the error useful, so it is required: pass the
    exact lookup we were trying to perform.
    """
    if result is None:
        raise ODInfoException(f"Expected a match but found none: {description}")
    return result
