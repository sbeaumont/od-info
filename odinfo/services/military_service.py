"""
Military service for military-related queries and calculations.

This service handles military intelligence queries including
OP/DP calculations, boat capacity, and related statistics.

Design principles:
- Single Responsibility: Only handles military-related queries
- Dependency Injection: Receives repository, doesn't fetch external data
- Pure calculations: Receives current_day as parameter rather than fetching it
"""

import logging
from datetime import timedelta

from odinfo.calculators.military import MilitaryCalculator, RatioCalculator
from odinfo.domain.models import Dominion, BarracksSpy
from odinfo.repositories.game import GameRepository
from odinfo.timeutils import hours_since, truncate_to_tick
from odinfoweb.viewmodels.military import MilitaryRowVM, RealmieRowVM

logger = logging.getLogger('od-info.military_service')


class MilitaryService:
    """
    Service for military-related queries and calculations.

    This service provides military intelligence including OP/DP calculations,
    boat capacity analysis, and target assessment. It works directly with
    the repository for data access.
    """

    def __init__(self, repo: GameRepository):
        """
        Create the military service.

        Args:
            repo: Repository for accessing dominion data.
        """
        self._repo = repo

    def military_list(self, current_day: int, versus_op: int = 0, top: int = 20,
                      include_current_strength: bool = False) -> list[MilitaryRowVM]:
        """
        Get military overview for top dominions.

        Args:
            current_day: Current game day (for boat protection calculations).
            versus_op: OP value to calculate safe OP/DP against (0 for default).
            top: Number of top dominions to include.
            include_current_strength: If True, calculate current strength from
                refined BS data. This is expensive (queries archives).

        Returns:
            List of MilitaryRowVM view models for each dominion.
        """
        logger.debug("Computing military_list for versus_op=%s, top=%s, current=%s",
                     versus_op, top, include_current_strength)
        all_doms = list(self._repo.all_dominions())[:top]
        mil_calcs = sorted(
            [MilitaryCalculator(dom) for dom in all_doms],
            key=lambda d: d.dom.current_networth,
            reverse=True
        )
        mc_list = [d for d in mil_calcs if d.army]
        result_list = []

        for mc in mc_list:
            five_four_op, five_four_dp = mc.five_over_four
            boat_stuff = mc.boats(current_day)

            # Calculate current strength only if requested
            if include_current_strength:
                current_op, current_dp, confidence = self.calculate_current_strength(mc.dom)
            else:
                current_op, current_dp, confidence = None, None, None

            row = MilitaryRowVM(
                code=mc.dom.code,
                name=mc.dom.name,
                realm=mc.dom.realm,
                race=mc.dom.race,
                ops_age=hours_since(mc.dom.last_op),
                land=mc.dom.current_land,
                hittable_75_percent=mc.hittable_75_percent,
                five_over_four_op=five_four_op,
                five_over_four_dp=five_four_dp,
                five_four_op_with_temples=mc.five_four_op_with_temples,
                temples=mc.temple_bonus,
                boats_amount=boat_stuff[0],
                boats_prt=boat_stuff[1],
                boats_sendable=boat_stuff[2],
                boats_capacity=boat_stuff[3],
                paid_until=mc.army.get('paid_until', '?'),
                draftees=mc.draftees,
                raw_op=mc.raw_op,
                paid_op=mc.paid_op,
                raw_dp=mc.raw_dp,
                paid_dp=mc.paid_dp,
                safe_op=mc.safe_op if versus_op == 0 else mc.safe_op_versus(versus_op)[0],
                safe_dp=mc.safe_dp if versus_op == 0 else mc.safe_op_versus(versus_op)[1],
                safe_op_with_temples=mc.safe_op_with_temples(versus_op),
                networth=mc.dom.current_networth,
                has_incomplete_intel=mc.has_incomplete_intel(),
                current_op=current_op,
                current_dp=current_dp,
                confidence=confidence,
            )
            result_list.append(row)

        return result_list

    def calculate_current_strength(self, dom: Dominion) -> tuple[int | None, int | None, str | None]:
        """Calculate current strength from refined BS data.

        Args:
            dom: Dominion to calculate current strength for.

        Returns:
            Tuple of (current_op, current_dp, confidence_string).
            Returns (None, None, None) if no BS data available.
        """
        last_bs = dom.last_barracks
        if not last_bs:
            return None, None, None

        bs_list = self.get_barracks_spies_in_tick(dom, last_bs.timestamp)
        if not bs_list:
            return None, None, None

        mc = MilitaryCalculator(dom)
        ticks_since_bs = int(hours_since(last_bs.timestamp))

        refined_home = mc.refined_home_units(bs_list)
        if not refined_home:
            return None, None, None

        arrived_returning = mc.arrived_returning_units(bs_list, ticks_since_bs)
        arrived_training = mc.arrived_training_units(last_bs, ticks_since_bs)

        current_op = mc.current_op(refined_home, arrived_returning, arrived_training)
        current_dp = mc.current_dp(refined_home, arrived_returning, arrived_training)

        confidence = self._calculate_confidence(refined_home, arrived_returning)

        return current_op, current_dp, confidence

    def strength_forecast(self, dom: Dominion) -> list[tuple[int, int, int]]:
        """Project OP and DP for the next 12 ticks.

        Args:
            dom: Dominion to forecast.

        Returns:
            List of (tick, op, dp) tuples for ticks 0-12 from now.
        """
        last_bs = dom.last_barracks
        if not last_bs:
            return []

        bs_list = self.get_barracks_spies_in_tick(dom, last_bs.timestamp)
        if not bs_list:
            return []

        mc = MilitaryCalculator(dom)
        ticks_since_bs = int(hours_since(last_bs.timestamp))

        refined_home = mc.refined_home_units(bs_list)
        if not refined_home:
            return []

        forecast = []
        for future_tick in range(13):
            total_elapsed = ticks_since_bs + future_tick

            arrived_returning = mc.arrived_returning_units(bs_list, total_elapsed)
            arrived_training = mc.arrived_training_units(last_bs, total_elapsed)

            op = mc.current_op(refined_home, arrived_returning, arrived_training)
            dp = mc.current_dp(refined_home, arrived_returning, arrived_training)

            forecast.append((future_tick, op, dp))

        return forecast

    def _calculate_confidence(self, refined_home: dict, arrived_returning: dict) -> str:
        """Calculate confidence string from refined estimates.

        Returns the max error percentage across all refined values.
        """
        max_error = 0.0

        for key, (lower, upper, error_pct) in refined_home.items():
            max_error = max(max_error, error_pct)

        for key, (lower, upper, error_pct) in arrived_returning.items():
            max_error = max(max_error, error_pct)

        if max_error < 1:
            return "locked"
        else:
            return f"±{round(max_error)}%"

    def top_op(self, mil_calc_result: list[MilitaryRowVM]) -> MilitaryRowVM | None:
        """
        Find the dominion with highest 5/4 OP from a military list.

        Args:
            mil_calc_result: Result from military_list().

        Returns:
            MilitaryRowVM with highest 5/4 OP, or None if list is empty.
        """
        if not mil_calc_result:
            return None

        topop = mil_calc_result[0]
        for mc in mil_calc_result[1:]:
            if mc.five_over_four_op > topop.five_over_four_op:
                topop = mc
        return topop

    def realmies_with_blops_info(self, realmie_doms: list, current_day: int) -> list[RealmieRowVM]:
        """
        Get realmies with military calculator info including blops (boats).

        Args:
            realmie_doms: List of Dominion objects for realm members.
            current_day: Current game day (for boat protection calculations).

        Returns:
            List of RealmieRowVM view models for each realmie.
        """
        logger.debug("Getting Realmies with blops info")
        mc_list = [MilitaryCalculator(dom) for dom in realmie_doms if dom.last_cs]
        result_list = []

        for mc in mc_list:
            boat_info = mc.boats(current_day)

            # SPA from ClearSight (may be None if no ClearSight available)
            rc = RatioCalculator(mc.dom)

            row = RealmieRowVM(
                code=mc.dom.code,
                name=mc.dom.name,
                player=mc.dom.player,
                land=mc.dom.current_land,
                hittable_75_percent=mc.hittable_75_percent,
                max_sendable_op=boat_info[2] if boat_info else 0,
                paid_dp=mc.paid_dp,
                wpa=mc.dom.current_wpa,
                spa=rc.spy_ratio_actual,
                docks=mc.dom.navy['docks'] if mc.dom.navy else None,
                boats_protected=boat_info[1] if boat_info else 0,
                boats_total=boat_info[0] if boat_info else 0,
                ares=mc.dom.magic.ares if mc.dom.magic else None,
            )
            result_list.append(row)

        return sorted(result_list, key=lambda x: x.land, reverse=True)

    def get_barracks_spies_in_tick(self, dom: Dominion, tick_time) -> list[BarracksSpy]:
        """Get all BarracksSpy records for a dominion within a specific tick.

        Args:
            dom: Dominion to query.
            tick_time: Any timestamp within the desired tick.

        Returns:
            List of BarracksSpy records with timestamps in the same tick (hour).
        """
        tick_start = truncate_to_tick(tick_time)
        tick_end = tick_start + timedelta(hours=1)

        return [
            bs for bs in dom.barracks_spy
            if tick_start <= bs.timestamp < tick_end
        ]