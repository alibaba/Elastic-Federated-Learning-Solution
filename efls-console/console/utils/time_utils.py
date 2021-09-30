# -*- coding: utf8 -*-

from datetime import datetime, timedelta

from console.constant import DB_TIMEZONE_HOUR


def get_time_version() -> str:
    dt = datetime.utcnow() + timedelta(hours=DB_TIMEZONE_HOUR)
    return dt.strftime('%Y%m%d%H%M%S')
