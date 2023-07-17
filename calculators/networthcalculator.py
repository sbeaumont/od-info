

NETWORTH_VALUES = {
    'land': 20,
    'buildings': 5,
    'specs': 5,
    'spywiz': 5
}


QRY_NW_SINCE = """
    select
        dominion, networth, {}(timestamp) as timestamp
    from
        DominionHistory
    where
        timestamp >= datetime('now', :since)
    group by
        dominion
    order by
        dominion
"""


def get_networth_deltas(db, since='-12 hours'):
    latest_nws = db.query(QRY_NW_SINCE.format('max'), {'since': since})
    oldest_nws = db.query(QRY_NW_SINCE.format('min'), {'since': since})
    deltas = dict()
    for latest, oldest in zip(latest_nws, oldest_nws):
        deltas[latest['dominion']] = latest['networth'] - oldest['networth']
    return deltas


# Don't need this since we already get it from ops, but it's there if we need it...

# class NetworthCalculator(object):
#     def __init__(self, ops):
#         self.ops = ops
#
#     @property
#     def networth(self) -> int:
#         if self.ops.q('status.military_spies'):
#             networth = 0
#             networth += self.ops.land * NETWORTH_VALUES['land']
#             networth += self.ops.buildings.total * NETWORTH_VALUES['buildings']
#
#             networth += self.ops.military.amount(1) * NETWORTH_VALUES['specs']
#             networth += self.ops.military.amount(2) * NETWORTH_VALUES['specs']
#             networth += self.ops.military.amount(3) * self.ops.race.def_elite.networth
#             networth += self.ops.military.amount(4) * self.ops.race.off_elite.networth
#
#             networth += self.ops.q('status.military_spies') * NETWORTH_VALUES['spywiz']
#             networth += self.ops.q('status.military_assassins') * NETWORTH_VALUES['spywiz']
#             networth += self.ops.q('status.military_wizards') * NETWORTH_VALUES['spywiz']
#             networth += self.ops.q('status.military_archmages') * NETWORTH_VALUES['spywiz']
#             return round(networth)
#         else:
#             return self.q("status.networth")
#
