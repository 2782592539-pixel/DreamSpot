"""SQLite connection management."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from backend.config import get_settings


def get_db_path() -> Path:
    return Path(get_settings().db_path)


# Register adapters so datetimes are stored as ISO strings and read back
# as datetime objects (avoids Python 3.12 deprecation warning).
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("timestamp", lambda s: datetime.fromisoformat(s.decode("utf-8")))


@contextmanager
def get_connection():
    """Yield a SQLite connection with row factory and WAL mode."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()
