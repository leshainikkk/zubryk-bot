import threading

from psycopg2.pool import ThreadedConnectionPool

from zubryk.config import APP_TIMEZONE, DATABASE_URL

_pool = None
_lock = threading.Lock()


def db_connect():
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:
                if not DATABASE_URL:
                    raise RuntimeError("Укажите DATABASE_URL в .env")
                _pool = ThreadedConnectionPool(
                    1, 20, dsn=DATABASE_URL, connect_timeout=5,
                    options=f"-c timezone={APP_TIMEZONE}",
                )
    return _pool.getconn()


def db_release(conn):
    if not conn.closed:
        conn.rollback()
    _pool.putconn(conn)
