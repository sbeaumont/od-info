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

from odinfo.calculators.military import MilitaryCalculator, RatioCalculator
from odinfo.domain.military import barracks_spies_in_tick
from odinfo.domain.models import Dominion
from odinfo.domain.refdata import BUILD_TICKS
from odinfo.repositories.game import GameRepository
from odinfo.timeutils import hours_since
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

    def military_list(self, current_day: int, defense_bonus: float, versus_op: int = 0,
                      top: int = 20) -> list[MilitaryRowVM]:
        """
        Get military overview for top dominions.

        Args:
            current_day: Current game day (for boat protection calculations).
            defense_bonus: The defender's own DP bonus as a decimal, which is what a
                target's temples eat into. Used for the +Tmps columns.
            versus_op: OP value to calculate safe OP/DP against (0 for default).
            top: Number of top dominions to include.

        Returns:
            List of MilitaryRowVM view models for each dominion.
        """
        logger.debug("Computing military_list for versus_op=%s, top=%s, dp_bonus=%s",
                     versus_op, top, defense_bonus)
        all_doms = list(self._repo.dominions_in_play())[:top]
        mil_calcs = sorted(
            [MilitaryCalculator(dom) for dom in all_doms],
            key=lambda d: d.dom.current_networth,
            reverse=True
        )
        mc_list = [d for d in mil_calcs if d.military]
        result_list = []

        for mc in mc_list:
            five_four_op, five_four_dp = mc.five_over_four
            boat_stuff = mc.boats(current_day)

            # Get refined paid strength (uses midpoint estimates)
            refined_paid_op, refined_paid_dp, confidence = self.refine_paid_strength(mc.dom)
            paid_op = refined_paid_op if refined_paid_op is not None else mc.paid_op
            paid_dp = refined_paid_dp if refined_paid_dp is not None else mc.paid_dp

            current_op, current_dp, current_confidence = self.calculate_current_strength(mc.dom)
            if current_confidence:
                confidence = current_confidence

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
                five_four_op_with_temples=mc.five_four_op_with_temples(defense_bonus),
                temples=mc.temple_bonus,
                boats_amount=boat_stuff[0],
                boats_prt=boat_stuff[1],
                boats_sendable=boat_stuff[2],
                boats_capacity=boat_stuff[3],
                paid_until='?' if mc.military.paid_until is None else mc.military.paid_until,
                draftees=mc.draftees,
                raw_op=mc.raw_op,
                paid_op=paid_op,
                raw_dp=mc.raw_dp,
                paid_dp=paid_dp,
                normal_op=mc.normal_op if versus_op == 0 else mc.safe_op_versus(versus_op)[0],
                normal_dp=mc.normal_dp if versus_op == 0 else mc.safe_op_versus(versus_op)[1],
                normal_op_with_temples=mc.normal_op_with_temples(versus_op, defense_bonus),
                networth=mc.dom.current_networth,
                has_incomplete_intel=mc.has_incomplete_intel(),
                has_bs_worst_case=mc.military.has_bs_worst_case,
                current_op=current_op,
                current_dp=current_dp,
                confidence=confidence,
            )
            result_list.append(row)

        return result_list

    def defense_bonus(self, dom: Dominion) -> float:
        """A dominion's own DP bonus as a decimal, from guard towers, walls, spells and techs."""
        return MilitaryCalculator(dom).defense_bonus

    def calculate_current_strength(self, dom: Dominion) -> tuple[int | None, int | None, str | None]:
        """Calculate current strength from refined BS data.

        Requires multiple BS observations from the same tick to actually
        narrow the fuzz range. With a single BS, the estimate is no better
        than the standard calculation.

        Args:
            dom: Dominion to calculate current strength for.

        Returns:
            Tuple of (current_op, current_dp, confidence_string).
            Returns (None, None, None) if fewer than 2 BS observations available.
        """
        if not dom.last_barracks:
            return None, None, None

        mc = MilitaryCalculator(dom, tick=0)
        return mc.current_op(), mc.current_dp(), mc.military.confidence

    def refine_paid_strength(self, dom: Dominion) -> tuple[int | None, int | None, str | None]:
        """Calculate refined OP/DP at the paid_until tick.

        Requires multiple BS observations from the same tick to actually
        narrow the fuzz range. With a single BS, the CS-based calculation
        is more accurate, so returns None to let callers use that instead.

        Args:
            dom: Dominion to calculate paid strength for.

        Returns:
            Tuple of (paid_op, paid_dp, confidence_string).
            Returns (None, None, None) if fewer than 2 BS observations available.
        """
        last_bs = dom.last_barracks
        if not last_bs or len(barracks_spies_in_tick(dom, last_bs.timestamp)) < 2:
            return None, None, None

        mc = MilitaryCalculator(dom, tick=last_bs.paid_until)
        return mc.current_op(), mc.current_dp(), mc.military.confidence

    def strength_forecast(self, dom: Dominion) -> list[tuple[int, int, int]]:
        """Project OP and DP for the next 12 ticks.

        Args:
            dom: Dominion to forecast.

        Returns:
            List of (tick, op, dp) tuples for ticks 0-12 from now.
        """
        if not dom.last_barracks:
            return []

        forecast = []
        for future_tick in range(BUILD_TICKS + 1):
            mc = MilitaryCalculator(dom, tick=future_tick)
            forecast.append((future_tick, mc.current_op(), mc.current_dp()))
        return forecast

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