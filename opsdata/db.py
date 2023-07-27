import os
import sqlite3


class Database(object):
    def __init__(self):
        self._conn = None

    def teardown(self):
        self._conn.close()
        self._conn = None

    def init(self, location: str, schema_file: str) -> bool:
        """Returns true if an init was needed so app knows to also do init stuff."""
        needs_schema_init = not os.path.exists(location)
        self._conn: sqlite3.Connection = sqlite3.connect(location)
        self.conn.row_factory = sqlite3.Row
        if needs_schema_init:
            with open(schema_file) as f:
                self.conn.cursor().executescript(f.read())
                self.conn.commit()
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
        # print(f"Executing {sql} with {params}")
        cur.execute(sql, params)
        self.conn.commit()

    def query(self, sql: str, params: dict | list | tuple = None, one=False):
        with self.conn as conn:
            if params:
                cur = conn.execute(sql, params)
            else:
                cur = conn.execute(sql)
            result = cur.fetchall()
        if one and len(result) != 1:
            print("Warning, expected exactly one result in", result, "for", sql, params)
        return result[0] if one else result

    def cursor(self):
        return self.conn.cursor()
