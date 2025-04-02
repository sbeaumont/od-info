"""
Database access, including necessary initialization, teardown and logging.
"""

import os
import sqlite3
import logging

logger = logging.getLogger('od-info.db')


class Database(object):
    def __init__(self):
        self._conn: sqlite3.Connection | None = None

    def teardown(self):
        self._conn.close()
        self._conn = None

    def init(self, location: str, schema_file: str=None) -> bool:
        """Returns true if an init was needed so app knows to also do init stuff."""
        needs_schema_init = not os.path.exists(location)
        if needs_schema_init:
            logger.info(f"Initializing new database for file name {location}")
            if not os.path.exists(os.path.dirname(location)):
                os.makedirs(os.path.dirname(location))
        else:
            logger.info(f"Starting database from existing file {location}")

        self._conn: sqlite3.Connection = sqlite3.connect(location)
        self.conn.row_factory = sqlite3.Row
        if needs_schema_init:
            if schema_file:
                with open(schema_file) as f:
                    logger.info(f"Initializing schema from file {schema_file}")
                    self.conn.cursor().executescript(f.read())
                    self.conn.commit()
            else:
                raise ValueError("Database %s needs initialization but no schema file was given.", location)
        return needs_schema_init

    @property
    def conn(self):
        if not self._conn:
            raise Exception("Accessing database connection before init.")
        return self._conn

    def close(self):
        self.conn.close()

    def execute(self, sql: str, params: dict | list | tuple):
        cur = self.conn.cursor()
        print(f"Executing {sql} with {params}")
        cur.execute(sql, params)
        self.conn.commit()

    def executemany(self, sql: str, params: dict | list | tuple):
        cur = self.conn.cursor()
        # print(f"Executing {sql} with {params}")
        cur.executemany(sql, params)
        self.conn.commit()

    def executescript(self, scriptfilename: str):
        with open(scriptfilename) as f:
            self.conn.executescript(f.read())

    def query(self, sql: str, params: dict | list | tuple = None, one=False):
        with self.conn as conn:
            if params:
                cur = conn.execute(sql, params)
            else:
                cur = conn.execute(sql)

            if one:
                result = cur.fetchone()
                if result and all(result[k] is None for k in result.keys()):
                    result = None
            else:
                result = cur.fetchall()
        return result

    def cursor(self):
        return self.conn.cursor()
