QRY_NW_SINCE = """
    select
        dominion, land, networth, {}(timestamp) as timestamp
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


