from pathlib import Path
import sqlite3


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, autocommit=False)
    return conn
