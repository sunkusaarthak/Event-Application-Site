import sys
import mysql.connector
from mysql.connector import pooling, Error
import logging

logger = logging.getLogger("DBManager")

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class DBManager:
    def __init__(self, config, pool_name="mypool", pool_size=3):
        """
        Initialize the DBManager with a connection pool.
        :param config: MySQL connection parameters
        :param pool_name: Name of the pool
        :param pool_size: Number of connections to keep in pool
        """
        try:
            logger.debug(f"Creating MySQL connection pool: name={pool_name}, size={pool_size}, config={config}")
            self.pool = pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=pool_size,
                pool_reset_session=True,
                **config
            )
            logger.info("MySQL connection pool created successfully.")
        except Error as e:
            logger.error(f"Error creating connection pool: {e}")
            raise

    def get_connection(self):
        try:
            logger.debug("Getting connection from pool...")
            return self.pool.get_connection()
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise