from odinfo.domain.models import DominionHistory
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

from odinfo.timeutils import current_od_time

logger = logging.getLogger('od-info.calculators')


def get_latest_and_oldest_nw(db, since=12):
    since_timestamp = current_od_time() + timedelta(hours=-since)
    logger.debug(f"Getting networth values since {since_timestamp}")
    latest_nws = db.session.execute(db.select(DominionHistory, func.max(DominionHistory.timestamp))
                                    .filter(DominionHistory.timestamp >= since_timestamp)
                                    .group_by(DominionHistory.dominion_id)).scalars()
    oldest_nws = db.session.execute(db.select(DominionHistory, func.min(DominionHistory.timestamp))
                                    .filter(DominionHistory.timestamp >= since_timestamp)
                                    .group_by(DominionHistory.dominion_id)).scalars()
    return latest_nws, oldest_nws


def get_networth_deltas(db, since=12):
    since_timestamp = current_od_time() + timedelta(hours=-since)
    logger.debug(f"Getting networth values since {since_timestamp}")

    # First, use the rewritten queries for consistent cross-database behavior
    latest_subq = db.select(
        DominionHistory.dominion_id,
        func.max(DominionHistory.timestamp).label('max_timestamp')
    ).filter(
        DominionHistory.timestamp >= since_timestamp
    ).group_by(
        DominionHistory.dominion_id
    ).subquery()

    latest_nws = db.session.execute(
        db.select(DominionHistory).join(
            latest_subq,
            db.and_(
                DominionHistory.dominion_id == latest_subq.c.dominion_id,
                DominionHistory.timestamp == latest_subq.c.max_timestamp
            )
        )
    ).scalars().all()

    oldest_subq = db.select(
        DominionHistory.dominion_id,
        func.min(DominionHistory.timestamp).label('min_timestamp')
    ).filter(
        DominionHistory.timestamp >= since_timestamp
    ).group_by(
        DominionHistory.dominion_id
    ).subquery()

    oldest_nws = db.session.execute(
        db.select(DominionHistory).join(
            oldest_subq,
            db.and_(
                DominionHistory.dominion_id == oldest_subq.c.dominion_id,
                DominionHistory.timestamp == oldest_subq.c.min_timestamp
            )
        )
    ).scalars().all()

    # Create dictionaries keyed by dominion_id instead of using zip
    latest_dict = {record.dominion_id: record for record in latest_nws}
    oldest_dict = {record.dominion_id: record for record in oldest_nws}

    # Calculate deltas for dominions that appear in both results
    deltas = {}
    for dominion_id in set(latest_dict) & set(oldest_dict):
        latest = latest_dict[dominion_id]
        oldest = oldest_dict[dominion_id]
        deltas[dominion_id] = latest.networth - oldest.networth
    return deltas

