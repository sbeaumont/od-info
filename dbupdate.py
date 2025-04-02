import sys

from odinfo.opsdata.db import Database
from odinfo.config import DATABASE_NAME


if __name__ == '__main__':
    database = Database()
    database.init(DATABASE_NAME)
    database.executescript(sys.argv[1])
    database.close()
