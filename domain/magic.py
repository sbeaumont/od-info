from opsdata.schema import query_revelation, current_od_time
from domain.unknown import Unknown


class Magic(object):
    def __init__(self, dom, data):
        self.dom = dom
        self.spells = data

    @property
    def ares(self) -> int | None:
        for spell in self.spells:
            if ('ares_call' == spell['spell']) and (current_od_time(True) < spell['expires']):
                return spell['expires']
        return None


def revelation_for(db, dom):
    data = query_revelation(db, dom.code)
    if data:
        return Magic(dom, data)
    else:
        return Unknown()
