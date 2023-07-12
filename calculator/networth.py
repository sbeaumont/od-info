import json
import os

from calculator.scrapetools import login
from calculator.ops import grab_search
from config import NETWORTH_FILE
from datetime import datetime, timedelta
from calculator.dominion import name_for_code


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


def print_networth_trends(doms):
    def to_ts(ts_str):
        day_str, time_str = ts_str.split('.')
        return timedelta(days=int(day_str),
                         hours=int(time_str[:2]),
                         minutes=int(time_str[2:4]),
                         seconds=int(time_str[4:6]))

    nw_trends = list()
    for dom_code, networths in doms.items():
        sorted_ts = sorted(networths.keys())
        if len(sorted_ts) >= 2:
            last = to_ts(sorted_ts[-1])
            previous = to_ts(sorted_ts[-2])
            seconds = (last-previous).total_seconds()
            change_diff = networths[sorted_ts[-1]][1] - networths[sorted_ts[-2]][1]
            change_rate = round(change_diff / seconds, 4)
            nw_trends.append((change_rate, change_diff, networths[sorted_ts[-1]][1], name_for_code(dom_code), dom_code))

    change_rate_list = sorted(nw_trends, reverse=True)
    print("Top Growers\n")
    for dom in change_rate_list[:10]:
        print(dom)
    print("\nTop Sinkers\n")
    for dom in change_rate_list[-10:]:
        print(dom)


def main():
    session = login()
    doms = update_networth(session, NETWORTH_FILE)
    with open(NETWORTH_FILE) as f:
        doms = json.load(f)
    print_networth_trends(doms)


if __name__ == '__main__':
    main()
