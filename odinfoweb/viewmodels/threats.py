"""
View models for the threats page.
"""

from collections import defaultdict
from dataclasses import dataclass, replace

from odinfo.calculators.threats import Battlefield, Strike, contenders_at
from odinfo.domain.models import Dominion, TownCrier
from odinfo.domain.refdata import BUILD_TICKS, DAILY_LAND_BONUS
from odinfo.exceptions import ODInfoException
from odinfo.timeutils import hours_since

STATUS_ORDER = ('now', 'triggered', 'five_four', 'none', 'out')


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
    cells: list[ThreatCellVM]

    @property
    def sort_key(self) -> tuple:
        """Most urgent first: the worst status, then the first tick with it, then the largest margin."""
        return min((STATUS_ORDER.index(cell.status), tick, -(cell.margin or 0))
                   for tick, cell in enumerate(self.cells))


TOOLTIP_NAMES = 3


def thousands(value: int) -> str:
    return f'{value / 1000:.0f}k'


def name_list(names: list[str]) -> str:
    """The first few names, and how many more there are."""
    shown = ', '.join(names[:TOOLTIP_NAMES])
    return f'{shown} +{len(names) - TOOLTIP_NAMES} more' if len(names) > TOOLTIP_NAMES else shown


def threat_cell(s: Strike, names: dict[int, str]) -> ThreatCellVM:
    """The status, margin and tooltip of one strike."""
    if s.safe_send_margin > 0:
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
    return ThreatCellVM(s.five_four_margin, 'none',
                        f'5/4 {thousands(s.five_four_op)} vs DP {thousands(s.defender_dp)}')


def build_threats_vm(dominions: list[Dominion], events: list[TownCrier], defender_code: int, min_range: float,
                     max_range: float, max_triggers: int, land_bonus_tick: int | None) -> list[ThreatRowVM]:
    """A row for every dominion that has the defender in range at one or more ticks, most urgent first."""
    names = {dom.code: dom.name for dom in dominions}
    invasions = defaultdict(list)
    for event in events:
        if event.event_type == 'invasion':
            invasions[event.origin].append(event)
    if not next(dom for dom in dominions if dom.code == defender_code).military:
        raise ODInfoException(f"{names[defender_code]} has no CS or BS, so there is no military to defend with. "
                              f"Realmies who do not share advisors have no ops.")
    ticks = range(BUILD_TICKS + 1)
    strikes_per_tick = []
    for tick in ticks:
        contenders = contenders_at(dominions, tick, invasions)
        defender = {c.code: c for c in contenders}[defender_code]
        if land_bonus_tick is not None and tick >= land_bonus_tick:
            claimed = replace(defender, land=defender.land + DAILY_LAND_BONUS)
            contenders = [claimed if c is defender else c for c in contenders]
            defender = claimed
        battlefield = Battlefield(contenders, min_range, max_range, max_triggers)
        strikes_per_tick.append({s.attacker: s for s in battlefield.strikes_on(defender)})

    doms = {dom.code: dom for dom in dominions}
    cells: dict[int, list[ThreatCellVM]] = {}
    for code in {code for strikes in strikes_per_tick for code in strikes}:
        back_at = doms[code].military.back_at
        cells[code] = []
        for tick in ticks:
            strike = strikes_per_tick[tick].get(code)
            if strike is None:
                cells[code].append(ThreatCellVM(None, 'out', ''))
                continue
            cell = threat_cell(strike, names)
            if back_at is not None and tick < back_at:
                cell.tooltip += f' · army out, back at +{back_at}'
            cells[code].append(cell)

    rows = [ThreatRowVM(code, doms[code].name, doms[code].realm, doms[code].race,
                        hours_since(doms[code].last_op) if doms[code].last_op else None, row_cells)
            for code, row_cells in cells.items()]
    return sorted(rows, key=lambda row: row.sort_key)
