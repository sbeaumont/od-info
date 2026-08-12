"""
Report service for generating networth change reports.

This service handles report generation including networth changes
and Discord notifications.

Design principles:
- Single Responsibility: Only handles report generation and notifications
- Dependency Injection: Receives repository, works with fundamental data sources
"""

import logging
from datetime import timedelta
from operator import itemgetter

from odinfo.calculators.networthcalculator import NetworthDelta, get_networth_deltas
from odinfo.config import NW_DEFAULT_PERIOD
from odinfo.domain.models import Dominion
from odinfo.facade.discord import send_to_webhook
from odinfo.repositories.game import GameRepository

logger = logging.getLogger('od-info.report_service')

BOT_REALM = 0
TOP_BOTTOM_COUNT = 10


def format_span(span: timedelta) -> str:
    """The stretch a delta was measured over, as hours and minutes."""
    minutes = round(span / timedelta(minutes=1))
    return f"{minutes // 60}h{minutes % 60:02d}m"


class ReportService:
    """
    Service for generating reports about dominion networth changes.

    This service generates various networth-related reports and can
    send them to Discord. It works directly with the repository
    for fundamental data access.
    """

    def __init__(self, repo: GameRepository):
        """
        Create the report service.

        Args:
            repo: Repository for accessing dominion data.
        """
        self._repo = repo

    def _get_all_dominions(self) -> dict[int, Dominion]:
        """Every dominion worth reporting on, by code. Bots are not."""
        return {dom.code: dom for dom in self._repo.all_dominions() if dom.realm != BOT_REALM}

    def _get_nw_deltas(self, since: int = NW_DEFAULT_PERIOD) -> dict[int, NetworthDelta]:
        """Get networth deltas for all dominions."""
        return get_networth_deltas(self._repo, since=since)

    def _readings(self, since: int) -> tuple[dict[int, Dominion], dict[int, NetworthDelta]]:
        """The dominions to report on, and the deltas we have for them."""
        doms = self._get_all_dominions()
        readings = {code: reading
                    for code, reading in self._get_nw_deltas(since=since).items()
                    if code in doms}
        return doms, readings

    @staticmethod
    def _nw_row(dom: Dominion, reading: NetworthDelta) -> dict:
        return {
            'code': dom.code,
            'name': dom.name,
            'race': dom.race,
            'land': dom.current_land,
            'networth': dom.current_networth,
            'nwdelta': reading.delta,
            'span': format_span(reading.span),
            'realm': dom.realm
        }

    def count_without_delta(self, since: int = NW_DEFAULT_PERIOD) -> int:
        """How many dominions have too few readings in the period to give a delta."""
        doms = self._get_all_dominions()
        return len(set(doms) - set(self._get_nw_deltas(since=since)))

    def get_unchanged_nw(self, top: int | None = None, since: int = NW_DEFAULT_PERIOD) -> list[dict]:
        """
        Get dominions whose networth did not move, sorted by land size.

        Args:
            top: Maximum number of results, or None for all of them.
            since: Number of hours to look back.

        Returns:
            List of dicts with dominion info for those with zero networth change.
        """
        logger.debug("Getting Unchanged NW")
        doms, readings = self._readings(since)
        result = sorted((self._nw_row(doms[code], reading)
                         for code, reading in readings.items() if reading.delta == 0),
                        key=itemgetter('land'), reverse=True)
        return result[:top] if top else result

    def get_top_bot_nw(self, top: bool = True, filter_zeroes: bool = False, since: int = NW_DEFAULT_PERIOD) -> list[dict]:
        """
        Get top or bottom networth changers.

        Args:
            top: If True, get top gainers; if False, get top losers.
            filter_zeroes: If True, exclude dominions with zero change.
            since: Number of hours to look back.

        Returns:
            List of dicts with dominion info sorted by networth change.
        """
        logger.debug("Getting Top and Bot NW changes")
        doms, readings = self._readings(since)
        if filter_zeroes:
            readings = {code: reading
                        for code, reading in readings.items() if reading.delta != 0}
        ranked = sorted(readings.items(),
                        key=lambda item: item[1].delta,
                        reverse=top)[:TOP_BOTTOM_COUNT]
        return [self._nw_row(doms[code], reading) for code, reading in ranked]

    def send_top_bot_nw_to_discord(self):
        """
        Send networth change reports to Discord webhook.

        Sends three messages: the networth growers, the networth sinkers, and the
        largest dominions whose networth did not move.

        Returns:
            Response from the last webhook call.
        """
        def create_message(header, nw_list):
            msg_content = '\n'.join([
                f"{item['name']:<50} {item['realm']:>5} {item['nwdelta']:>9} "
                f"{item['span']:>7} {item['networth']:>9} {item['land']:>5}"
                for item in nw_list
            ])
            return (f"{header}\n```{'Dominion':<50} {'Realm':>5} {'Delta':>9} "
                    f"{'Span':>7} {'Networth':>9} {'Land':>5}\n\n{msg_content}```")

        header_top = f'**Top {TOP_BOTTOM_COUNT} Networth Growers since past {NW_DEFAULT_PERIOD} hours**'
        top10_message = create_message(header_top, self.get_top_bot_nw(filter_zeroes=True))
        header_bot = f'**Top {TOP_BOTTOM_COUNT} Networth *Sinkers* since past {NW_DEFAULT_PERIOD} hours**'
        bot10_message = create_message(header_bot, self.get_top_bot_nw(top=False, filter_zeroes=True))
        header_unchanged = (f'**Top {TOP_BOTTOM_COUNT} largest Networth *Unchanged* '
                            f'since past {NW_DEFAULT_PERIOD} hours**')
        unchanged_message = create_message(header_unchanged,
                                           self.get_unchanged_nw(top=TOP_BOTTOM_COUNT))
        discord_message = f"{top10_message}\n{bot10_message}"

        logger.debug("Sending to Discord webhook: %s", discord_message)
        webhook_response = send_to_webhook(discord_message)
        logger.debug("Webhook response: %s", webhook_response)

        logger.debug("Sending to Discord webhook: %s", unchanged_message)
        webhook_response = send_to_webhook(unchanged_message)
        logger.debug("Webhook response: %s", webhook_response)

        return webhook_response