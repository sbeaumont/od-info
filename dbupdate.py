import sys

from odinfo.opsdata.db import Database
from odinfo.config import get_config
from odinfo.services.od_api import database_url


if __name__ == '__main__':
    database = Database()
    database.init(database_url(get_config(), print))
    database.executescript(sys.argv[1])
    database.close()
