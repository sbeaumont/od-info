from datetime import timedelta
from domain.dominion import name_for_code


NETWORTH_VALUES = {
    'land': 20,
    'buildings': 5,
    'specs': 5,
    'spywiz': 5
}


class NetworthCalculator(object):
    def __init__(self, ops):
        self.ops = ops

    @property
    def networth(self) -> int:
        if self.ops.q('status.military_spies'):
            networth = 0
            networth += self.ops.land * NETWORTH_VALUES['land']
            networth += self.ops.buildings.total * NETWORTH_VALUES['buildings']

            networth += self.ops.military.amount(1) * NETWORTH_VALUES['specs']
            networth += self.ops.military.amount(2) * NETWORTH_VALUES['specs']
            networth += self.ops.military.amount(3) * self.ops.race.def_elite.networth
            networth += self.ops.military.amount(4) * self.ops.race.off_elite.networth

            networth += self.ops.q('status.military_spies') * NETWORTH_VALUES['spywiz']
            networth += self.ops.q('status.military_assassins') * NETWORTH_VALUES['spywiz']
            networth += self.ops.q('status.military_wizards') * NETWORTH_VALUES['spywiz']
            networth += self.ops.q('status.military_archmages') * NETWORTH_VALUES['spywiz']
            return round(networth)
        else:
            return self.q("status.networth")

    def trends(self, doms):
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

        return sorted(nw_trends, reverse=True)


class MilitaryCalculator(object):
    def __init__(self, ops):
        self.ops = ops

    def spywiz_estimate(self) -> int:
        networth = self.ops.q('status.networth')
        networth -= self.ops.land * NETWORTH_VALUES['land']
        networth -= self.ops.buildings.total * NETWORTH_VALUES['buildings']

        networth -= self.ops.military.amount(1) * NETWORTH_VALUES['specs']
        networth -= self.ops.military.amount(2) * NETWORTH_VALUES['specs']
        networth -= self.ops.military.amount(3) * self.ops.race.def_elite.networth
        networth -= self.ops.military.amount(4) * self.ops.race.off_elite.networth

        return round(networth / NETWORTH_VALUES['spywiz'])


def main():
    session = login()
    doms = update_networth(session, NETWORTH_FILE)
    with open(NETWORTH_FILE) as f:
        doms = json.load(f)
    print_networth_trends(doms)


if __name__ == '__main__':
    main()
