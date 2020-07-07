"""Connection to database and perform queries for the actual file data."""
# Python imports
import json
import logging
import os
from builtins import print
from datetime import datetime
from typing import List, Tuple, Dict

# 3rd party modules
import psycopg2
from pypika import Query, Table, Field, Parameter

# Local imports
from crawler.services.config import Config
import crawler.communication as communication

_logger = logging.getLogger(__name__)

def measure_time(func):
    """Decorator for time measurement of DatabaseConnection objects.

    This decorator is used for roughly estimate the time spent for database
    operations. It can wrap arbitrary methods of DatabaseConnection objects.

    Args:
        func (function): function to wrap

    """

    def decorator(self, *args, **kwargs):
        if self._measure_time:
            start = datetime.now()
            result = func(self, *args, **kwargs)
            end = datetime.now()
            self._time += (end - start).total_seconds()
        else:
            result = func(self, *args, **kwargs)
        return result

    return decorator


class DatabaseConnectionTableFiles:

    def __init__(self, db_info: dict, measure_time: bool) -> None:
        """Initialize the connection to Postgres Database.

        Args:
            db_info (dict): connection data of the database
            measure_time (bool): measure time for database operations

        Raises:
            VallueError: when creating the connection failed

        """

        try:
            self.con = psycopg2.connect(
                user=db_info['user'],
                password=db_info['password'],
                host=db_info['host'],
                port=db_info['port'],
                database=db_info['dbname']
            )
        except Exception as err:
            raise ValueError(f'Files database initialization error: {err}')

        self._time = 0
        self._measure_time = measure_time


    @measure_time
    def insert_new_record_files(self, insert_values: List[Tuple[str]]) -> None:
        """Insert a new record to the 'files' table based on the ExifTool output.

        Args: insert_values (List[Tuple[str]): A list of tuples. Each tuple contains the values for each row to be
                                                inserted.

        """
        # Construct the SQL query for inserting the new files into the 'files' table (Done in a single query for
        # performance purposes)
        query = 'INSERT INTO "files" ("crawl_id","dir_path","name","type","size","metadata","creation_time", ' \
                '"access_time","modification_time","deleted","deleted_time","file_hash", "in_metadata") VALUES '
        curs = self.con.cursor()
        for insert in insert_values:
            query += curs.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s),", insert).decode('utf8')
        # Execute the constructed query (Rollback and raise in case of error)
        try:
            curs.execute(query[:-1])
        except:
            _logger.warning('"Error inserting new files into the database"')
            curs.close()
            self.con.rollback()
            raise
        curs.close()
        self.con.commit()
        return

    def close(self) -> None:
        self.con.close()

    @measure_time
    def check_directory(self, path: str, current_hashes: List[str]) -> List[int]:
        """checks the database for a given directory. Returns all the most recent ids.

        Args:
            path (str): directory path to be checked
            current_hashes (List[str]): list of all hashes from current files
        Returns:
            List(int): file ids that are supposed to be deleted
        """
        files = Table('files')
        query = Query.from_(files) \
            .select('id', 'crawl_id', 'dir_path', 'name', 'file_hash') \
            .where(files.dir_path == Parameter('%s'))
        curs = self.con.cursor()
        query = curs.mogrify(str(query), (path,))
        try:
            curs.execute(query)
            get = curs.fetchall()
        except:
            return []
        curs.close()
        self.con.commit()

        # Find the second highest crawl id (remove max first as it is the current crawl)
        id_set = set([x[1] for x in get])
        id_set.remove(max(id_set))
        if len(id_set) == 0:
            return []
        recent_crawl = max(id_set)
        # Make list with every file_id in that directory/crawl
        file_ids = [x[0] for x in get if x[1] == recent_crawl and x[-1] in current_hashes]
        return file_ids

    @measure_time
    def set_deleted(self, file_ids: List[int]) -> None:
        """Set every file in file_ids deleted and deleted_time value.

        Args:
            file_ids (List[int): List of file ids to be deleted
        Returns:
        """
        if len(file_ids) < 1:
            return
        files = Table('files')
        query = Query.update(files) \
            .set(files.deleted, 'True') \
            .set(files.deleted_time, datetime.now()) \
            .where(files.id.isin(Parameter('%s')))
        curs = self.con.cursor()
        query = curs.mogrify(str(query), (tuple(file_ids),))
        try:
            curs.execute(query)
            curs.close()
            self.con.commit()
        except Exception as e:
            print(e)
            _logger.warning('"Error updating file deletion"')
            curs.close()
            self.con.rollback()