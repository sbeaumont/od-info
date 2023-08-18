from opsdata.schema import query_land
from domain.unknown import Unknown

LAND_TYPES = (
    'plain',
    'mountain',
    'swamp',
    'cavern',
    'forest',
    'hill',
    'water'
)


class Land(object):
    def __init__(self, dom, data):
        self.dom = dom
        self._data = data

    def __str__(self):
        lands = [f"{t}:{self._data[t]}" for t in LAND_TYPES]
        return f"Land({'|'.join(lands)})"

    @property
    def total(self):
        return self._data['total']

    def ratio_of(self, land_type):
        return self._data[land_type] / self.dom.total_land * 100


def land_for(db, dom):
    data = query_land(db, dom.code, latest=True)
    if data:
        return Land(dom, data)
    else:
        return Unknown()
