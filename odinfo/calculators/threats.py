from dataclasses import dataclass

from odinfo.calculators.military import MilitaryCalculator
from odinfo.domain.models import Dominion


@dataclass
class Contender:
    """A dominion at one tick: its realm, its land and a calculator on its military home then."""
    code: int
    realm: int
    land: int
    mc: MilitaryCalculator


@dataclass
class Trigger:
    """A threat that has to send before an attacker can break the defender with its safe send."""
    code: int
    free: bool


@dataclass
class Strike:
    """What one attacker can send at the defender at one tick, as OP against the DP of the defender."""
    attacker: int
    defender_dp: int
    five_four_op: int
    safe_send_op: int
    held_by: list[int]
    triggers: list[Trigger]
    triggered_op: int | None
    triggered_dp: int | None

    @property
    def five_four_margin(self) -> int:
        return self.five_four_op - self.defender_dp

    @property
    def safe_send_margin(self) -> int:
        return self.safe_send_op - self.defender_dp

    @property
    def triggered_margin(self) -> int | None:
        return None if self.triggered_op is None else self.triggered_op - self.triggered_dp


def contenders_at(doms: list[Dominion], tick: int, invasions: dict[int, list]) -> list[Contender]:
    """A contender at the tick for every dominion that has a military, with invasions keyed by attacker."""
    return [Contender(dom.code, dom.realm, dom.land_at(tick, invasions.get(dom.code, [])),
                      MilitaryCalculator(dom, tick))
            for dom in doms if dom.military]


def in_range(target_land: int, attacker_land: int, min_range: float, max_range: float) -> bool:
    return min_range <= target_land / attacker_land * 100 <= max_range


def threats_to(attacker: Contender, contenders: list[Contender], min_range: float,
               max_range: float) -> list[tuple[Contender, int]]:
    """Dominions in another realm with the attacker in range, with their 5/4 send against it, strongest first."""
    threats = [(c, c.mc.five_four_op_with_temples(attacker.mc.defense_bonus))
               for c in contenders
               if c.realm != attacker.realm and in_range(attacker.land, c.land, min_range, max_range)]
    return sorted(threats, key=lambda threat: threat[1], reverse=True)


def safe_send(attacker: Contender, threat_op: int) -> int:
    """The OP the attacker can send while its home DP still beats the threat."""
    return min(attacker.mc.safe_op_versus(threat_op)[0], attacker.mc.five_over_four[0])


class Battlefield(object):
    """All contenders at one tick, with the threats to each of them kept once calculated."""

    def __init__(self, contenders: list[Contender], min_range: float, max_range: float, max_triggers: int):
        self.contenders = contenders
        self.min_range = min_range
        self.max_range = max_range
        self.max_triggers = max_triggers
        self._threats = {}

    def threats_to(self, contender: Contender) -> list[tuple[Contender, int]]:
        if contender.code not in self._threats:
            self._threats[contender.code] = threats_to(contender, self.contenders, self.min_range, self.max_range)
        return self._threats[contender.code]

    def is_free_sender(self, contender: Contender) -> bool:
        """Whether the home DP after a 5/4 send beats every threat to the dominion."""
        threats = self.threats_to(contender)
        return not threats or threats[0][1] <= contender.mc.five_over_four[1]

    def strike(self, attacker: Contender, defender: Contender) -> Strike:
        """The 5/4 send and safe send of the attacker at the defender, and the threats that have to send first."""
        defense_bonus = defender.mc.defense_bonus
        defender_dp = defender.mc.dp
        threats = self.threats_to(attacker)

        def op_at_defender(threat_index: int) -> int:
            threat_op = threats[threat_index][1] if threat_index < len(threats) else 0
            return attacker.mc.op_with_temples(safe_send(attacker, threat_op), defense_bonus)

        five_four_op = attacker.mc.five_four_op_with_temples(defense_bonus)
        safe_send_op = op_at_defender(0)
        triggers, triggered_op, triggered_dp = [], None, None
        if safe_send_op <= defender_dp:
            for count in range(1, min(len(threats), self.max_triggers) + 1):
                sent = [c for c, _ in threats[:count]]
                dp = defender.mc.five_over_four[1] if defender.code in [c.code for c in sent] else defender_dp
                op = op_at_defender(count)
                if op > dp:
                    triggers = [Trigger(c.code, self.is_free_sender(c)) for c in sent]
                    triggered_op, triggered_dp = op, dp
                    break

        held_by = [c.code for c, op in threats if op > attacker.mc.five_over_four[1]]
        return Strike(attacker.code, defender_dp, five_four_op, safe_send_op,
                      held_by, triggers, triggered_op, triggered_dp)

    def strikes_on(self, defender: Contender) -> list[Strike]:
        """A strike for every dominion in another realm that has the defender in range."""
        return [self.strike(c, defender)
                for c in self.contenders
                if c.realm != defender.realm and in_range(defender.land, c.land, self.min_range, self.max_range)]
