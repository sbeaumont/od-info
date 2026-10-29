"""
View models for the targets page.
"""

from dataclasses import dataclass
from datetime import timedelta
from statistics import median

from odinfo.calculators.military import MilitaryCalculator
from odinfo.domain.models import Dominion, TownCrier
from odinfo.timeutils import current_od_time, hours_since

# Hits under 75% get the bottom-feeding penalties
MIN_RANGE = 75
MAX_RANGE = 250
EXPLORE_WINDOW = 24
# Land from a hit arrives with the returning units, so an invasion this long ago can still add land
LAND_ARRIVAL_WINDOW = EXPLORE_WINDOW + 12
ATTACK_EVENTS = ('invasion', 'bounce')


@dataclass
class TargetRowVM:
    """View model for a single row in the targets list."""
    code: int
    name: str
    realm: int
    race: str
    land: int
    networth: int
    nw_per_acre: float
    nw_vs_race: float
    range_percent: float
    sent_age: int | None
    sent_land: int | None
    sent_bounced: bool
    hit_age: int | None
    hit_land: int | None
    hit_bounced: bool
    explored: int | None
    estimated_dp: int
    dp: int | None
    dp_per_acre: float | None
    dp_incomplete: bool
    draftees: int | None
    ops_age: int | None


def explored_land(dom: Dominion, sent: list[TownCrier], hit: list[TownCrier]) -> int | None:
    """Land growth in the explore window plus land lost to hits, or None if invasions could add land."""
    if any(hours_since(e.timestamp) < LAND_ARRIVAL_WINDOW for e in sent):
        return None
    window_start = current_od_time() - timedelta(hours=EXPLORE_WINDOW)
    readings = [h for h in dom.history if h.timestamp >= window_start]
    if len(readings) < 2:
        return None
    land_lost = sum(e.amount or 0 for e in hit if e.timestamp >= window_start)
    return readings[0].land - readings[-1].land + land_lost


def build_targets_vm(dominions: list[Dominion], attacker_land: int, events: list[TownCrier]) -> list[TargetRowVM]:
    """Rows for every dominion in range of the attacker, sorted by estimated DP."""
    attacks = sorted((e for e in events if e.event_type in ATTACK_EVENTS),
                     key=lambda e: e.timestamp, reverse=True)
    sent_by = {}
    hit_on = {}
    for event in attacks:
        sent_by.setdefault(event.origin, []).append(event)
        hit_on.setdefault(event.target, []).append(event)

    nw_per_acre = {dom.code: dom.current_networth / dom.current_land for dom in dominions}
    race_medians = {race: median(nw_per_acre[d.code] for d in dominions if d.race == race)
                    for race in {d.race for d in dominions}}

    result = []
    for dom in dominions:
        range_percent = dom.current_land / attacker_land * 100
        if not MIN_RANGE <= range_percent <= MAX_RANGE:
            continue
        sent = sent_by.get(dom.code, [])
        hit = hit_on.get(dom.code, [])
        last_sent = sent[0] if sent else None
        last_hit = hit[0] if hit else None
        cs = dom.last_cs
        mc = MilitaryCalculator(dom)
        has_ops = mc.army is not None
        result.append(TargetRowVM(
            code=dom.code,
            name=dom.name,
            realm=dom.realm,
            race=dom.race,
            land=dom.current_land,
            networth=dom.current_networth,
            nw_per_acre=round(nw_per_acre[dom.code], 1),
            nw_vs_race=round((nw_per_acre[dom.code] / race_medians[dom.race] - 1) * 100, 1),
            range_percent=round(range_percent, 1),
            sent_age=hours_since(last_sent.timestamp) if last_sent else None,
            sent_land=last_sent.amount if last_sent else None,
            sent_bounced=bool(last_sent) and last_sent.event_type == 'bounce',
            hit_age=hours_since(last_hit.timestamp) if last_hit else None,
            hit_land=last_hit.amount if last_hit else None,
            hit_bounced=bool(last_hit) and last_hit.event_type == 'bounce',
            explored=explored_land(dom, sent, hit),
            estimated_dp=mc.estimated_dp,
            dp=mc.paid_dp if has_ops else None,
            dp_per_acre=round(mc.paid_dp / dom.current_land, 1) if has_ops else None,
            dp_incomplete=bool(mc.missing_intel_for_stats()['defense']) if has_ops else False,
            draftees=cs.military_draftees if cs else None,
            ops_age=hours_since(dom.last_op) if dom.last_op else None,
        ))

    return sorted(result, key=lambda r: r.estimated_dp)
