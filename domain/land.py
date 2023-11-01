import json
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

    def ratio_of(self, land_type: str) -> float:
        return self._data[land_type] / self.dom.total_land * 100

    @property
    def incoming(self) -> int:
        result = 0
        incoming = json.loads(self._data['incoming'])
        for landtype in LAND_TYPES:
            if landtype in incoming:
                result += sum(incoming[landtype].values())
        return result


def land_for(db, dom) -> Land | Unknown:
    data = query_land(db, dom.code, latest=True)
    if data:
        return Land(dom, data)
    else:
        return Unknown()
