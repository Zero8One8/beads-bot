"""
Исправленная БД с thread-safety
"""
import sqlite3
import threading
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from src.config import Config

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe работа с SQLite."""
    
    _local = threading.local()
    
    def __init__(self, db_path: str = str(Config.DB_PATH)):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить соединение для текущего потока."""
        if not hasattr(self._local, 'connection') or not self._local.connection:
            self._local.connection = self._create_connection()
        return self._local.connection
    
    def _create_connection(self) -> sqlite3.Connection:
        """Создать новое соединение."""
        db_path = Path(self.db_path)
        if db_path.parent and not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        
        # Оптимизация для production
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA temp_store = MEMORY")
        
        logger.debug(f"DB connection created for thread {threading.get_ident()}")
        return conn
    
    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager для соединения."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(f"DB integrity error: {e}")
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"DB error: {e}")
            raise
    
    @contextmanager
    def cursor(self):
        """Context manager для курсора."""
        conn = self.get_connection()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB cursor error: {e}")
            raise
    
    def close(self):
        """Закрыть соединение для текущего потока."""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._local.connection = None


# Глобальный экземпляр БД
db = Database()
