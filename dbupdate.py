import sys

from opsdata.db import Database
from config import DATABASE


if __name__ == '__main__':
    database = Database()
    database.init(DATABASE)
    database.executescript(sys.argv[1])
    database.close()
