import sys

from odinfo.opsdata.db import Database
from odinfo.config import get_config


if __name__ == '__main__':
    database = Database()
    database.init(get_config().database_name)
    database.executescript(sys.argv[1])
    database.close()
