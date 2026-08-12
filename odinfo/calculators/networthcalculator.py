import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, and_

from odinfo.domain.models import DominionHistory
from odinfo.repositories.game import GameRepository
from odinfo.timeutils import current_od_time

logger = logging.getLogger('od-info.calculators')


@dataclass(frozen=True)
class NetworthDelta:
    """How far a dominion's networth moved, and the stretch it was measured over."""
    delta: int
    oldest: datetime
    latest: datetime

    @property
    def span(self) -> timedelta:
        return self.latest - self.oldest


def get_networth_deltas(repo: GameRepository, since=12) -> dict[int, NetworthDelta]:
    """How far each dominion's networth moved within the last `since` hours."""
    since_timestamp = current_od_time() + timedelta(hours=-since)
    logger.debug(f"Getting networth values since {since_timestamp}")
    session = repo.session

    # Subquery for latest timestamps per dominion
    latest_subq = select(
        DominionHistory.dominion_id,
        func.max(DominionHistory.timestamp).label('max_timestamp')
    ).filter(
        DominionHistory.timestamp >= since_timestamp
    ).group_by(
        DominionHistory.dominion_id
    ).subquery()

    latest_nws = session.execute(
        select(DominionHistory).join(
            latest_subq,
            and_(
                DominionHistory.dominion_id == latest_subq.c.dominion_id,
                DominionHistory.timestamp == latest_subq.c.max_timestamp
            )
        )
    ).scalars().all()

    # Subquery for oldest timestamps per dominion
    oldest_subq = select(
        DominionHistory.dominion_id,
        func.min(DominionHistory.timestamp).label('min_timestamp')
    ).filter(
        DominionHistory.timestamp >= since_timestamp
    ).group_by(
        DominionHistory.dominion_id
    ).subquery()

    oldest_nws = session.execute(
        select(DominionHistory).join(
            oldest_subq,
            and_(
                DominionHistory.dominion_id == oldest_subq.c.dominion_id,
                DominionHistory.timestamp == oldest_subq.c.min_timestamp
            )
        )
    ).scalars().all()

    # Create dictionaries keyed by dominion_id
    latest_dict = {record.dominion_id: record for record in latest_nws}
    oldest_dict = {record.dominion_id: record for record in oldest_nws}

    # Calculate deltas for dominions we saw at two different moments
    deltas = dict()
    for dominion_id in set(latest_dict) & set(oldest_dict):
        latest = latest_dict[dominion_id]
        oldest = oldest_dict[dominion_id]
        if latest.timestamp == oldest.timestamp:
            # One reading: a delta of zero would claim it held still, when in truth we
            # never saw it move.
            continue
        deltas[dominion_id] = NetworthDelta(latest.networth - oldest.networth,
                                            oldest.timestamp,
                                            latest.timestamp)
    return deltas