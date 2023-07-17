import json
import os

from domain.dominion import grab_search


def update_networth(session, file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            doms = json.load(f)
    else:
        doms = dict()

    lines = grab_search(session)
    for line in lines:
        dom_code = line[2]
        if dom_code not in doms.keys():
            doms[dom_code] = dict()
        land_and_nw = [line[5], line[6]]
        if len(doms[dom_code].keys()) == 0:
            doms[dom_code][line[0]] = land_and_nw
        else:
            latest = max(doms[dom_code].keys())
            if (line[0] > latest) and (land_and_nw != doms[dom_code][latest]):
                doms[dom_code][line[0]] = land_and_nw

    with open(file_name, 'w') as f:
        json.dump(doms, f, indent=2)

    return doms


QRY_NW_SINCE = """
    select
        code, networth, {}(timestamp) as timestamp
    from
        DominionHistory
    where
        timestamp >= datetime('now', :since)
    group by
        code
    order by
        code
"""


def get_networth_deltas(db, since='-12 hours'):
    latest_nws = db.query(QRY_NW_SINCE.format('max'), {'since': since})
    oldest_nws = db.query(QRY_NW_SINCE.format('min'), {'since': since})
    deltas = dict()
    for latest, oldest in zip(latest_nws, oldest_nws):
        deltas[latest['code']] = latest['networth'] - oldest['networth']
    return deltas
