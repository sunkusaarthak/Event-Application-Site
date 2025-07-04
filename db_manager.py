import mysql.connector
from mysql.connector import pooling, Error
import logging

# Optional: File-based logging for DB errors
logging.basicConfig(filename='db_errors.log', level=logging.ERROR,
                    format='%(asctime)s [%(levelname)s] %(message)s')


class DBManager:
    def __init__(self, config, pool_name="mypool", pool_size=3):
        """
        Initialize the DBManager with a connection pool.
        :param config: MySQL connection parameters
        :param pool_name: Name of the pool
        :param pool_size: Number of connections to keep in pool
        """
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=pool_size,
                pool_reset_session=True,
                **config
            )
        except Error as e:
            logging.error(f"Error creating connection pool: {e}")
            raise

    def get_connection(self):
        """
        Get a connection from the pool.
        """
        try:
            return self.pool.get_connection()
        except Error as e:
            logging.error(f"Error getting connection from pool: {e}")
            raise