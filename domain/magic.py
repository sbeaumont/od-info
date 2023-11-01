from opsdata.schema import query_revelation, hours_until
from domain.unknown import Unknown


class Magic(object):
    def __init__(self, dom, data):
        self.dom = dom
        self.spells = data

    @property
    def ares(self) -> int | None:
        for spell in self.spells:
            if spell['spell'] == 'ares_call':
                return hours_until(spell['expires'])
        return None


def revelation_for(db, dom) -> Magic | Unknown:
    data = query_revelation(db, dom.code)
    if data:
        return Magic(dom, data)
    else:
        return Unknown()
