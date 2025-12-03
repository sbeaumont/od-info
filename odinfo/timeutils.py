import re
from datetime import datetime, timedelta
from math import trunc

from odinfo.config import DATE_TIME_FORMAT, get_config


def cleanup_timestamp(timestamp: str) -> datetime:
    """Ensures that a timestamp has a YYYY-MM-DD HH:MM:SS format."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", timestamp)
    if m:
        clean_ts = f"{m.group(1)} {m.group(2)}"
        return datetime.strptime(clean_ts, DATE_TIME_FORMAT)
    else:
        return datetime.now()


def row_s_to_dict(row_s):
    if row_s:
        if isinstance(row_s, list):
            return [dict(zip(row.keys(), row)) for row in row_s]
        else:
            return dict(zip(row_s.keys(), row_s))
    else:
        return dict()


def current_od_time(as_str=False) -> datetime | str:
    dt = datetime.now().replace(microsecond=0) + timedelta(hours=get_config().local_time_shift)
    if as_str:
        return dt.strftime(DATE_TIME_FORMAT)
    else:
        return dt


def hours_until(timestamp):
    return hours_since(timestamp, future=True) + 1


def hours_since(timestamp, future=False):
    if timestamp:
        if future:
            delta = timestamp - current_od_time()
        else:
            delta = current_od_time() - timestamp
        delta_hours = delta / timedelta(hours=1)
        return trunc(delta_hours)
    else:
        return 999


def add_duration(timestamp: str, duration: int, whole_hour=False) -> str:
    timestamp_dt = datetime.strptime(timestamp, DATE_TIME_FORMAT)
    duration_td = timedelta(hours=duration)
    new_dt = timestamp_dt + duration_td
    if whole_hour:
        new_dt = new_dt.replace(minute=0, second=0)
    return new_dt.strftime(DATE_TIME_FORMAT)
