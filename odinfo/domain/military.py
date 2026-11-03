from datetime import timedelta
from math import inf

from odinfo.domain.refdata import BARRACKS_SPY_FUZZ
from odinfo.timeutils import hours_since, ticks_between, ticks_since, truncate_to_tick

UNIT_NRS = range(1, 5)


def barracks_spies_in_tick(dom, tick_time) -> list:
    """The BS ops of a dominion within the tick of tick_time."""
    tick_start = truncate_to_tick(tick_time)
    tick_end = tick_start + timedelta(hours=1)
    return [bs for bs in dom.barracks_spy if tick_start <= bs.timestamp < tick_end]


def refine_unit_estimate(observations: list[int]) -> tuple[float, float, float]:
    """Combine multiple BS observations to get tighter bounds on true value.

    The game shows a value somewhere in [true * fuzz, true / fuzz], so every observation
    puts the true value in [observed * fuzz, observed / fuzz]. The highest observation
    raises the floor and the lowest one lowers the ceiling, which is what makes several
    observations of the same tick worth more than one.

    Args:
        observations: List of observed values for a single unit type.

    Returns:
        Tuple of (lower_bound, upper_bound, error_pct).
        error_pct is the percentage error (half the range as % of midpoint).
    """
    if not observations:
        return 0, 0, 0

    lower_bound = max(observations) * BARRACKS_SPY_FUZZ
    upper_bound = min(observations) / BARRACKS_SPY_FUZZ

    # An observation of zero units means zero units, there is nothing to be wrong about.
    midpoint = (lower_bound + upper_bound) / 2
    error_pct = (upper_bound - lower_bound) / midpoint * 100 / 2 if midpoint else 0

    return lower_bound, upper_bound, max(0, error_pct)


def confidence(refined_home: dict, arrived_returning: dict) -> str:
    """The confidence string of refined estimates: the max error percentage across all of them."""
    max_error = 0.0

    for key, (lower, upper, error_pct) in refined_home.items():
        max_error = max(max_error, error_pct)

    for key, (lower, upper, error_pct) in arrived_returning.items():
        max_error = max(max_error, error_pct)

    if max_error < 1:
        return "locked"
    else:
        return f"±{round(max_error)}%"


class Military(object):
    """The units and draftees of a dominion, from its CS and BS ops."""

    def __init__(self, dom, units: dict, draftees: float, timestamp, paid_until: int | None = None,
                 confidence: str | None = None):
        self.dom = dom
        self.units = units
        self.draftees = draftees
        self.timestamp = timestamp
        self.paid_until = paid_until
        self.confidence = confidence

    @classmethod
    def of(cls, dom) -> 'Military | None':
        """The paid military of a dominion, or None without a CS or BS."""
        cs, bs = dom.last_cs, dom.last_barracks
        if cs and bs:
            if cls.from_cs(cs, bs):
                result = cs.military
                # Add remaining training troops from last BS that hadn't completed by CS time
                for i in UNIT_NRS:
                    result[f'unit{i}'] += bs.aged_amount_training_for_unit_at_time(i, cs.timestamp)
                result['paid_until'] = bs.paid_until
            else:
                result = bs.military
                # Keep the exact CS count for each unit that the newer BS does not contradict.
                cs_military = cs.military
                for i in UNIT_NRS:
                    if bs.allows_amount(i, cs_military[f'unit{i}']):
                        result[f'unit{i}'] = cs_military[f'unit{i}'] + bs.paid_training(i)
        elif cs:
            result = cs.military
        elif bs:
            result = bs.military
        else:
            return None
        return cls(dom,
                   {f'unit{i}': result[f'unit{i}'] for i in UNIT_NRS},
                   result['draftees'],
                   result['timestamp'],
                   result.get('paid_until'))

    @staticmethod
    def from_cs(cs, bs) -> bool:
        """Whether the military starts from the CS rather than the BS."""
        cs_age = hours_since(cs.timestamp)
        bs_age = hours_since(bs.timestamp)
        return (cs_age < 1) or (cs_age <= bs_age)

    @property
    def has_bs_worst_case(self) -> bool:
        """Whether a unit count in the military is the BS worst case."""
        cs, bs = self.dom.last_cs, self.dom.last_barracks
        if not bs:
            return False
        if not cs:
            return True
        if self.from_cs(cs, bs):
            return False
        cs_military = cs.military
        return not all(bs.allows_amount(i, cs_military[f'unit{i}']) for i in UNIT_NRS)

    def amount(self, unit_nr: int) -> float:
        return self.units[f'unit{unit_nr}']

    def at(self, tick: int) -> 'Military':
        """The units home at a tick from now, refined from the BS ops of the last BS tick."""
        last_bs = self.dom.last_barracks
        if not last_bs:
            return self
        bs_list = barracks_spies_in_tick(self.dom, last_bs.timestamp)
        refined_home, returning, from_tick = self.starting_point(bs_list)
        elapsed = ticks_since(last_bs.timestamp) + tick
        arrived_returning = self.arrived_returning_units(bs_list, elapsed, from_tick, returning)
        arrived_training = self.arrived_training_units(last_bs, elapsed, from_tick)
        lower, upper, _ = refined_home['draftees']
        return Military(self.dom,
                        self.refined_amounts(refined_home, arrived_returning, arrived_training),
                        (lower + upper) / 2,
                        self.timestamp,
                        self.paid_until,
                        confidence(refined_home, arrived_returning))

    def refined_home_units(self, barracks_spies: list) -> dict:
        """Get refined home unit estimates from multiple BS observations.

        Args:
            barracks_spies: List of BarracksSpy objects from the same tick.

        Returns:
            Dict with keys 'draftees', 'unit1'-'unit4', each containing
            (lower, upper, error_pct) tuple.
        """
        if not barracks_spies:
            return {}

        result = {}

        # Gather observations for each unit type
        draftee_obs = [bs.draftees for bs in barracks_spies]
        result['draftees'] = refine_unit_estimate(draftee_obs)

        for i in UNIT_NRS:
            unit_obs = [getattr(bs, f'home_unit{i}') for bs in barracks_spies]
            result[f'unit{i}'] = refine_unit_estimate(unit_obs)

        return result

    def clear_sight_units(self, barracks_spies: list, clear_sight, from_tick: int) -> tuple[dict, dict]:
        """Home units at the time of a CS, and the BS returning units still away then.

        Args:
            barracks_spies: List of BarracksSpy objects from the same tick.
            clear_sight: A CS taken in or after the tick of the BS.
            from_tick: Ticks between the BS and the CS.

        Returns:
            Tuple of (home, returning). Home is in the shape of refined_home_units(),
            returning is (lower, upper, error_pct) of each unit still away at the CS.
        """
        def bounds(lower, upper):
            midpoint = (lower + upper) / 2
            return lower, upper, (upper - lower) / midpoint * 100 / 2 if midpoint else 0

        military = clear_sight.military
        bs_home = self.refined_home_units(barracks_spies) if from_tick == 0 else {}
        remaining = self.arrived_returning_units(barracks_spies, inf, from_tick)

        home = {'draftees': (military['draftees'], military['draftees'], 0)}
        returning = {}
        for i in UNIT_NRS:
            key = f'unit{i}'
            total = military[key]
            returning_lower, returning_upper, _ = remaining.get(key, (0, 0, 0))
            lower, upper = total - returning_upper, total - returning_lower
            bs_lower, bs_upper, _ = bs_home.get(key, (0, inf, 0))
            # The CS is newer, so its range stands alone when it falls outside the BS home range.
            if bs_lower <= upper and lower <= bs_upper:
                lower, upper = max(lower, bs_lower), min(upper, bs_upper)
            home[key] = bounds(lower, upper)
            if key in remaining:
                returning[key] = bounds(total - upper, total - lower)
        return home, returning

    def starting_point(self, barracks_spies: list) -> tuple[dict, dict, int]:
        """Home units, the returning units still away, and the tick after the BS they hold at."""
        last_bs, last_cs = self.dom.last_barracks, self.dom.last_cs
        if last_cs and last_cs.timestamp >= last_bs.timestamp:
            from_tick = ticks_between(last_bs.timestamp, last_cs.timestamp)
            home, returning = self.clear_sight_units(barracks_spies, last_cs, from_tick)
            return home, returning, from_tick
        return self.refined_home_units(barracks_spies), {}, 0

    def arrived_returning_units(self, barracks_spies: list, ticks_since_bs: int, from_tick: int = 0,
                                totals: dict = None) -> dict:
        """Get refined returning units that have arrived home since BS was taken.

        Args:
            barracks_spies: List of BarracksSpy objects from the same tick.
            ticks_since_bs: Hours elapsed since the BS was taken.
            from_tick: Units arrived by this tick are left out.
            totals: Returning units after from_tick from clear_sight_units(), to share out.

        Returns:
            Dict with keys 'unit1'-'unit4', each containing
            (lower, upper, error_pct) tuple for total arrived units.
        """
        if not barracks_spies:
            return {}

        result = {}

        for i in UNIT_NRS:
            unit_key = f'unit{i}'

            # Collect all ticks that have arrived (tick <= age)
            arrived_ticks = set()
            for bs in barracks_spies:
                if bs.returning and unit_key in bs.returning:
                    for tick in bs.returning[unit_key].keys():
                        if from_tick < int(tick) <= ticks_since_bs:
                            arrived_ticks.add(tick)

            # Sum up refined values for all arrived ticks
            total_lower = 0
            total_upper = 0
            max_error = 0

            for tick in arrived_ticks:
                observations = []
                for bs in barracks_spies:
                    if bs.returning and unit_key in bs.returning:
                        val = bs.returning[unit_key].get(tick, 0)
                        if val > 0:
                            observations.append(val)
                if observations:
                    lower, upper, error = refine_unit_estimate(observations)
                    total_lower += lower
                    total_upper += upper
                    max_error = max(max_error, error)

            if total_lower > 0 or total_upper > 0:
                result[unit_key] = (total_lower, total_upper, max_error)

        if totals:
            remaining = self.arrived_returning_units(barracks_spies, inf, from_tick)
            for key, (lower, upper, _) in result.items():
                share = (lower + upper) / (remaining[key][0] + remaining[key][1])
                total_lower, total_upper, error = totals[key]
                result[key] = (total_lower * share, total_upper * share, error)

        return result

    def arrived_training_units(self, latest_bs, ticks_since_bs: int, from_tick: int = 0) -> dict:
        """Get training units that have arrived home since BS was taken.

        Args:
            latest_bs: BarracksSpy object.
            ticks_since_bs: Hours elapsed since the BS was taken.
            from_tick: Units arrived by this tick are left out.

        Returns:
            Dict with keys 'unit1'-'unit4' containing exact arrived amounts.
        """
        if not latest_bs:
            return {}

        result = {}
        for i in UNIT_NRS:
            unit_key = f'unit{i}'
            key = f'unit{i}'
            if latest_bs.training and key in latest_bs.training:
                arrived = sum(
                    amount for tick, amount in latest_bs.training[key].items()
                    if from_tick < int(tick) <= ticks_since_bs
                )
                if arrived > 0:
                    result[unit_key] = arrived
        return result

    @staticmethod
    def refined_amounts(refined_home: dict, arrived_returning: dict, arrived_training: dict) -> dict:
        """Compute effective unit amounts from refined BS data.

        Returns:
            Dict mapping 'unit1'-'unit4' to effective amounts (float).
        """
        amounts = {}
        for i in UNIT_NRS:
            key = f'unit{i}'
            amount = 0

            # Refined home (midpoint)
            if key in refined_home:
                lower, upper, _ = refined_home[key]
                amount = (lower + upper) / 2

            # Arrived training (exact)
            if key in arrived_training:
                amount += arrived_training[key]

            # Arrived returning (refined midpoint)
            if key in arrived_returning:
                lower, upper, _ = arrived_returning[key]
                amount += (lower + upper) / 2

            amounts[key] = amount
        return amounts