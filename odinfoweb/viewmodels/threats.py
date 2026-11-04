"""
View models for the threats page.
"""

from collections import defaultdict
from dataclasses import dataclass, replace

from odinfo.calculators.threats import Battlefield, Strike, contenders_at
from odinfo.domain.domainhelper import range_limit
from odinfo.domain.models import Dominion, TownCrier
from odinfo.domain.refdata import BUILD_TICKS, DAILY_LAND_BONUS, RETURN_TICKS
from odinfo.exceptions import ODInfoException
from odinfo.timeutils import hours_since, ticks_since
from odinfoweb.viewmodels.targets import ATTACK_EVENTS

THREAT_STATUSES = ('now', 'triggered', 'five_four', 'potential')


@dataclass
class ThreatCellVM:
    """One attacker at one tick: the margin to show, its status and the tooltip text."""
    margin: int | None
    status: str
    tooltip: str


@dataclass
class ThreatRowVM:
    """One attacker with a cell for every tick from now to the horizon."""
    code: int
    name: str
    realm: int
    race: str
    ops_age: int | None
    sent_after_bs: bool
    land: int
    limit: int
    in_range: bool
    cells: list[ThreatCellVM]

    @property
    def threat(self) -> bool:
        """Whether a send breaks the defender at one tick, or a 5/4 send comes close enough to be a potential threat."""
        return any(cell.status in THREAT_STATUSES for cell in self.cells)


TOOLTIP_NAMES = 3


def thousands(value: int) -> str:
    return f'{value / 1000:.0f}k'


def name_list(names: list[str]) -> str:
    """The first few names, and how many more there are."""
    shown = ', '.join(names[:TOOLTIP_NAMES])
    return f'{shown} +{len(names) - TOOLTIP_NAMES} more' if len(names) > TOOLTIP_NAMES else shown


def threat_cell(s: Strike, names: dict[int, str], potential_margin: float) -> ThreatCellVM:
    """The status, margin and tooltip of one strike, potential when its 5/4 send is within potential_margin % of the DP."""
    if s.safe_send_op is not None and s.safe_send_margin > 0:
        return ThreatCellVM(s.safe_send_margin, 'now',
                            f'safe {thousands(s.safe_send_op)} vs DP {thousands(s.defender_dp)}')
    if s.triggers:
        after = ', '.join(f"{names[t.code]} ({'free' if t.free else 'held'})" for t in s.triggers)
        return ThreatCellVM(s.triggered_margin, 'triggered',
                            f'safe {thousands(s.triggered_op)} vs DP {thousands(s.triggered_dp)} · after {after}')
    if s.five_four_margin > 0:
        held = name_list([names[code] for code in s.held_by])
        return ThreatCellVM(s.five_four_margin, 'five_four',
                            f'5/4 {thousands(s.five_four_op)} · safe {thousands(s.safe_send_op)} · held: {held}')
    potential = s.five_four_op >= (1 - potential_margin / 100) * s.defender_dp
    return ThreatCellVM(s.five_four_margin, 'potential' if potential else 'none',
                        f'5/4 {thousands(s.five_four_op)} vs DP {thousands(s.defender_dp)}')


def latest_send_after_bs(dom: Dominion, sends: list[TownCrier]) -> TownCrier | None:
    """The latest hit or bounce by the dominion after its last BS, while its army can still be out."""
    last_bs = dom.last_barracks
    later = [e for e in sends
             if (last_bs is None or e.timestamp > last_bs.timestamp)
             and ticks_since(e.timestamp) < RETURN_TICKS]
    return max(later, key=lambda e: e.timestamp) if later else None


def build_threats_vm(dominions: list[Dominion], events: list[TownCrier], defender_code: int, min_range: float,
                     max_range: float, max_triggers: int, potential_margin: float,
                     land_bonus_tick: int | None, home_dp: int | None) -> list[ThreatRowVM]:
    """The dominions that have the defender below their range, then the ones with the defender in range at one tick,
    each largest range limit first. A home_dp is the DP the defender keeps at home after a send now."""
    names = {dom.code: dom.name for dom in dominions}
    invasions, sends = defaultdict(list), defaultdict(list)
    for event in events:
        if event.event_type == 'invasion':
            invasions[event.origin].append(event)
        if event.event_type in ATTACK_EVENTS:
            sends[event.origin].append(event)
    if not next(dom for dom in dominions if dom.code == defender_code).military:
        raise ODInfoException(f"{names[defender_code]} has no CS or BS, so there is no military to defend with. "
                              f"Realmies who do not share advisors have no ops.")
    ticks = range(BUILD_TICKS + 1)
    strikes_per_tick, out_of_range_per_tick, contenders_per_tick, defenders = [], [], [], []
    dp_now = None
    for tick in ticks:
        contenders = contenders_at(dominions, tick, invasions)
        defender = {c.code: c for c in contenders}[defender_code]
        if dp_now is None:
            dp_now = defender.mc.dp
        changes = {}
        if land_bonus_tick is not None and tick >= land_bonus_tick:
            changes['land'] = defender.land + DAILY_LAND_BONUS
        if home_dp is not None:
            changes['home_dp'] = home_dp + defender.mc.dp - dp_now
        if changes:
            changed = replace(defender, **changes)
            contenders = [changed if c is defender else c for c in contenders]
            defender = changed
        battlefield = Battlefield(contenders, min_range, max_range, max_triggers)
        strikes_per_tick.append({s.attacker: s for s in battlefield.strikes_on(defender)})
        out_of_range_per_tick.append({s.attacker: s for s in battlefield.strikes_out_of_range(defender)})
        contenders_per_tick.append({c.code: c for c in contenders})
        defenders.append(defender)

    doms = {dom.code: dom for dom in dominions}

    def row(code: int, cells: list[ThreatCellVM], in_range: bool) -> ThreatRowVM:
        dom = doms[code]
        back_at = dom.military.back_at
        sent = latest_send_after_bs(dom, sends[code])
        for tick, cell in enumerate(cells):
            if cell.margin is None:
                continue
            limit = range_limit(contenders_per_tick[tick][code].land, min_range)
            cell.tooltip += f' · {min_range:g}% at {limit} acres, defender {defenders[tick].land - limit:+d}'
            if back_at is not None and tick < back_at:
                cell.tooltip += f' · army out, back at +{back_at}'
            if sent is not None and tick < RETURN_TICKS - ticks_since(sent.timestamp):
                cell.tooltip += f' · sent {hours_since(sent.timestamp)}h ago, after the last BS: take a BS'
            confidence = contenders_per_tick[tick][code].mc.military.confidence
            if confidence:
                cell.tooltip += f' · {confidence}'
        land = contenders_per_tick[0][code].land
        return ThreatRowVM(code, dom.name, dom.realm, dom.race, hours_since(dom.last_op) if dom.last_op else None,
                           sent is not None, land, range_limit(land, min_range), in_range, cells)

    def cells(per_tick: list[dict[int, Strike]], code: int) -> list[ThreatCellVM]:
        return [threat_cell(per_tick[tick][code], names, potential_margin) if code in per_tick[tick]
                else ThreatCellVM(None, 'out', '') for tick in ticks]

    in_range_codes = {code for strikes in strikes_per_tick for code in strikes}
    out_of_range_codes = {code for strikes in out_of_range_per_tick for code in strikes} - in_range_codes
    in_range_rows = [row(code, cells(strikes_per_tick, code), True) for code in in_range_codes]
    out_of_range_rows = [row(code, cells(out_of_range_per_tick, code), False) for code in out_of_range_codes]
    return sorted(out_of_range_rows + in_range_rows, key=lambda r: (r.in_range, -r.limit))
