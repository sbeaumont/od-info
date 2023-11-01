from opsdata.schema import query_vision
from domain.refdata import TechTree
from domain.unknown import Unknown


class Technology(object):
    def __init__(self, dom, data):
        self.dom = dom
        self._data = data
        self.tech_tree = TechTree()

    @property
    def researched(self):
        return self._data['techs']

    @property
    def pop_bonus(self):
        return self.value_for_perk('max_population')

    def value_for_perk(self, perk_name):
        return self.tech_tree.value_for_perk(perk_name, self.researched)


def tech_for(db, dom) -> Technology | Unknown:
    vision_data = query_vision(db, dom.code, latest=True)
    if vision_data:
        return Technology(dom, vision_data)
    else:
        return Unknown()
