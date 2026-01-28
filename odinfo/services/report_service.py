"""
Report service for generating networth change reports.

This service handles report generation including networth changes
and Discord notifications.

Design principles:
- Single Responsibility: Only handles report generation and notifications
- Dependency Injection: Receives repository, works with fundamental data sources
"""

import logging
from operator import itemgetter

from odinfo.calculators.networthcalculator import get_networth_deltas
from odinfo.facade.discord import send_to_webhook
from odinfo.repositories.game import GameRepository

logger = logging.getLogger('od-info.report_service')


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

    def _get_all_dominions(self) -> list:
        """Get all dominions sorted by land size."""
        doms = list(self._repo.all_dominions())
        return sorted(doms, key=lambda x: x.current_land, reverse=True)

    def _get_nw_deltas(self, since: int = 12) -> dict:
        """Get networth deltas for all dominions."""
        return get_networth_deltas(self._repo, since=since)

    def get_unchanged_nw(self, top: int = 50, since: int = 12) -> list[dict]:
        """
        Get dominions with unchanged networth, sorted by land size.

        Args:
            top: Maximum number of results to return.
            since: Number of hours to look back.

        Returns:
            List of dicts with dominion info for those with zero networth change.
        """
        logger.debug("Getting Unchanged NW")
        doms = self._get_all_dominions()
        nw_deltas = self._get_nw_deltas(since=since)
        selected_doms = [d for d, nwd in nw_deltas.items() if nwd == 0]
        relevant_doms = [d for d in doms if d.code in selected_doms]
        result = []
        for row in relevant_doms:
            nw_row = {
                'code': row.code,
                'name': row.name,
                'race': row.race,
                'land': row.current_land,
                'networth': row.current_networth,
                'nwdelta': nw_deltas[row.code],
                'realm': row.realm
            }
            result.append(nw_row)
        return sorted(result, key=itemgetter('land'), reverse=True)[:top]

    def get_top_bot_nw(self, top: bool = True, filter_zeroes: bool = False, since: int = 12) -> list[dict]:
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
        doms = self._get_all_dominions()
        nw_deltas = self._get_nw_deltas(since=since)
        sorted_deltas = sorted(nw_deltas.items(), key=lambda x: x[1], reverse=top)[:10]
        selected_doms = [d[0] for d in sorted_deltas]
        relevant_doms = [d for d in doms if d.code in selected_doms]
        result = []
        for row in relevant_doms:
            nw_row = {
                'code': row.code,
                'name': row.name,
                'race': row.race,
                'land': row.current_land,
                'networth': row.current_networth,
                'nwdelta': nw_deltas[row.code],
                'realm': row.realm
            }
            result.append(nw_row)
        if filter_zeroes:
            result = [dom for dom in result if dom['nwdelta'] != 0]
        return sorted(result, key=itemgetter('nwdelta'), reverse=top)

    def send_top_bot_nw_to_discord(self):
        """
        Send networth change reports to Discord webhook.

        Sends three messages:
        1. Top 10 networth growers
        2. Top 10 networth losers
        3. Top 10 largest unchanged networthsaliases

        Returns:
            Response from the last webhook call.
        """
        def create_message(header, nw_list):
            msg_content = '\n'.join([
                f"{item['name']:<50} {item['realm']:>5} {item['nwdelta']:>9} {item['networth']:>9} {item['land']:>5}"
                for item in nw_list
            ])
            return f"{header}\n```{'Dominion':<50} {'Realm':>5} {'Delta':>9} {'Networth':>9} {'Land':>5}\n\n{msg_content}```"

        header_top = '**Top 10 Networth Growers since past 12 hours**'
        top10_message = create_message(header_top, self.get_top_bot_nw(filter_zeroes=True))
        header_bot = '**Top 10 Networth *Sinkers* since past 12 hours**'
        bot10_message = create_message(header_bot, self.get_top_bot_nw(top=False, filter_zeroes=True))
        nr_networth_unchanged = 10
        header_unchanged = f'**Top {nr_networth_unchanged} largest Networth *Unchanged* since past 12 hours**'
        unchanged_message = create_message(header_unchanged, self.get_unchanged_nw(top=nr_networth_unchanged))
        discord_message = f"{top10_message}\n{bot10_message}"

        logger.debug("Sending to Discord webhook: %s", discord_message)
        webhook_response = send_to_webhook(discord_message)
        logger.debug("Webhook response: %s", webhook_response)

        logger.debug("Sending to Discord webhook: %s", unchanged_message)
        webhook_response = send_to_webhook(unchanged_message)
        logger.debug("Webhook response: %s", webhook_response)

        return webhook_response