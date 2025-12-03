import logging
from datetime import timedelta

from sqlalchemy import func, select, and_

from odinfo.domain.models import DominionHistory
from odinfo.repositories.game import GameRepository
from odinfo.timeutils import current_od_time

logger = logging.getLogger('od-info.calculators')


def get_latest_and_oldest_nw(repo: GameRepository, since=12):
    since_timestamp = current_od_time() + timedelta(hours=-since)
    logger.debug(f"Getting networth values since {since_timestamp}")
    session = repo.session
    latest_nws = session.execute(
        select(DominionHistory, func.max(DominionHistory.timestamp))
        .filter(DominionHistory.timestamp >= since_timestamp)
        .group_by(DominionHistory.dominion_id)
    ).scalars()
    oldest_nws = session.execute(
        select(DominionHistory, func.min(DominionHistory.timestamp))
        .filter(DominionHistory.timestamp >= since_timestamp)
        .group_by(DominionHistory.dominion_id)
    ).scalars()
    return latest_nws, oldest_nws


def get_networth_deltas(repo: GameRepository, since=12):
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

    # Calculate deltas for dominions that appear in both results
    deltas = {}
    for dominion_id in set(latest_dict) & set(oldest_dict):
        latest = latest_dict[dominion_id]
        oldest = oldest_dict[dominion_id]
        deltas[dominion_id] = latest.networth - oldest.networth
    return deltas

