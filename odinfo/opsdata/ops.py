"""
The ops of one dominion, as the OpenDominion API gives them.
"""

import logging

logger = logging.getLogger('db-info.ops')


class Ops(object):
    """Convenience object to parse the copy_ops json structure."""
    def __init__(self, contents, dom_id):
        self.contents = contents
        self.dom_id = dom_id

    def q_exists(self, q_str, start_node=None) -> bool:
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            if path in current_node:
                current_node = current_node[path]
                if current_node is None:
                    return False
            else:
                return False
        return True

    def q(self, q_str, start_node=None):
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            try:
                current_node = current_node[path]
            except KeyError:
                logger.error("Tried to find %s in %s", path, current_node)
        return current_node

    @property
    def has_clearsight(self) -> bool:
        return self.q_exists('clear_sight.name')

    @property
    def has_vision(self) -> bool:
        return self.q_exists('vision.techs')

    @property
    def has_barracks(self) -> bool:
        return self.q_exists('barracks_spy.units')

    @property
    def has_castle(self) -> bool:
        return self.q_exists('castle_spy.total')

    @property
    def has_land(self) -> bool:
        return self.q_exists('land_spy.totalLand')

    @property
    def has_survey(self) -> bool:
        return self.q_exists('survey_dominion.constructed')

    @property
    def has_revelation(self) -> bool:
        return self.q_exists('revelation.spells')