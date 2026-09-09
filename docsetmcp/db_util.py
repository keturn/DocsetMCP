from pathlib import Path
import sqlite3


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, autocommit=False)
    return conn


def escape_like_pattern(s: str, escape: str = "\x1b") -> str:
    """Escape special characters for SQL LIKE patterns.

    Must be used in conjunction with an ESCAPE clause in the SQL query, e.g.:
    ... LIKE ? ESCAPE char(0x1B)
    """
    return s.replace(escape, escape + escape).replace("%", escape + "%").replace("_", escape + "_")


def make_unique[T](small_list: list[T]) -> list[T]:
    """Make a list unique while preserving order.

    Modifies the list in place.
    """
    for i in range(len(small_list) - 1, 1, -1):
        if small_list[i] in small_list[:i]:
            small_list.pop(i)
    return small_list
