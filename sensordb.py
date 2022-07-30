import time
import sqlite3
from sqlite3 import Error
from contextlib import contextmanager

VER_TABLE_TEMPLATE = """CREATE TABLE IF NOT EXISTS version (
    timestamp INTEGER NOT NULL,
    version INTEGER NOT NULL
)"""

VERSION_INSERT_TEMPLATE = """INSERT INTO version values (?, ?)"""

VERSION_VERSION_QUERY_TEMPLATE = """SELECT * FROM version WHERE version=?"""

RUN_TABLE_TEMPLATE = """CREATE TABLE IF NOT EXISTS run (
    start INTEGER NOT NULL,
    end INTEGER NOT NULL
)"""

RUN_INSERT_TEMPLATE = """INSERT INTO run values (?, ?)"""

RUN_LAST_QUERY_TEMPLATE = """SELECT ROWID FROM run WHERE start=?"""

RUN_LAST_UPDATE_TEMPLATE = """UPDATE run SET end = ? WHERE ROWID=?"""

TABLE_TEMPLATE = """CREATE TABLE IF NOT EXISTS {} (
    timestamp INTEGER PRIMARY KEY,
    value REAL NOT NULL
) WITHOUT ROWID"""

TABLE_INSERT_TEMPLATE = """INSERT INTO {} values (?, ?)"""

def timestamp():
    """ get the time in milliseconds since epoch """
    return int(time.time_ns() / 1000000.0)

class SensorDB(object):
    data_version = 1
    def __init__(self, db_file, table_names):
        self._fname = db_file
        self._table_names = table_names
        self._conn = None
        self._run_rowid = -1

    def __enter__(self):
        """ create a database connection to a SQLite database """
        self._conn = sqlite3.connect(self._fname)
        print("sqlite3 version:", sqlite3.version)
        self.create_tables(self._table_names)
        self.start_run()
        return self

    def __exit__(self, ty, val, tb):
        self.end_run()
        self._conn.close()
        return False

    def set_version(self):
        cur = self._conn.cursor()
        cur.execute(VERSION_VERSION_QUERY_TEMPLATE, (SensorDB.data_version,))
        result = cur.fetchall()
        if len(result) == 0:
            cur.execute(VERSION_INSERT_TEMPLATE, (timestamp(), SensorDB.data_version))
            result = [[-1,SensorDB.data_version],]
            self._conn.commit()
        elif len(result) != 1:
            raise RuntimeError("should not have multiple versions in version table")
        print("sensordb data version is: {}".format(result[0][1]))

    def start_run(self):
        t = timestamp()
        cur = self._conn.cursor()
        cur.execute(RUN_INSERT_TEMPLATE, (t, -1))
        self._conn.commit()
        cur.execute(RUN_LAST_QUERY_TEMPLATE, (t,))
        self._run_rowid = cur.fetchone()[0]
        print("last runid:", self._run_rowid)

    def end_run(self):
        cur = self._conn.cursor()
        cur.execute(RUN_LAST_UPDATE_TEMPLATE, (timestamp(), self._run_rowid))
        self._conn.commit()
        self._run_rowid = -1

    def create_tables(self, sensor_table_names):
        """ create tables needed for ingesting data """
        table_names = ['version', 'run']
        table_names.extend(sensor_table_names)
        try:
            cur = self._conn.cursor()
            for table in table_names:
                if table == 'version':
                    sql = VER_TABLE_TEMPLATE
                elif table == 'run':
                    sql = RUN_TABLE_TEMPLATE
                else:
                    sql = TABLE_TEMPLATE.format(table)
                #print("sql:'{}'".format(sql))
                cur.execute(sql)
                #print("{} table created".format(table))
            self._conn.commit()
            self.set_version()
        finally:
            cur = None

    def insert_data(self, table_name, timestamp, val):
        cur = self._conn.cursor()
        sql = TABLE_INSERT_TEMPLATE.format(table_name)
        #print("tbl: {} timestamp: {} val: {}".format(table_name, timestamp, val))
        cur.execute(sql, (timestamp, val))
        self._conn.commit()
