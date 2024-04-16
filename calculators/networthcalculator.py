from domain.models import DominionHistory
from sqlalchemy import func
from datetime import datetime, timedelta
import logging


logger = logging.getLogger('od-info.calculators')


def get_networth_deltas(db, since=12):
    since_timestamp = datetime.now() + timedelta(hours=-since)
    logger.debug(f"Getting networth values since {since_timestamp}")
    latest_nws = db.session.execute(db.select(DominionHistory, func.max(DominionHistory.timestamp))
                                    .filter(DominionHistory.timestamp >= since_timestamp)
                                    .group_by(DominionHistory.dominion_id)).scalars()
    oldest_nws = db.session.execute(db.select(DominionHistory, func.min(DominionHistory.timestamp))
                                    .filter(DominionHistory.timestamp >= since_timestamp)
                                    .group_by(DominionHistory.dominion_id)).scalars()
    deltas = dict()
    for latest, oldest in zip(latest_nws, oldest_nws):
        deltas[latest.dominion_id] = latest.networth - oldest.networth
    return deltas

