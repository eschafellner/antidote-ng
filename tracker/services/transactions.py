from collections.abc import Callable
import random
import sqlite3
import time
from typing import TypeVar

from django.db import OperationalError, connection, transaction


Result = TypeVar("Result")


def run_write_transaction(operation: Callable[[], Result], *, attempts: int = 8) -> Result:
    """Wiederholt bei einem vorübergehenden Schreibkonflikt die gesamte Transaktion."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if connection.in_atomic_block:
        # Ein Savepoint kann den Snapshot der äußeren Transaktion nicht erneuern.
        with transaction.atomic():
            return operation()

    for attempt in range(attempts - 1):
        try:
            with transaction.atomic():
                return operation()
        except OperationalError as exc:
            if not _is_write_conflict(exc):
                raise
            time.sleep(random.uniform(0.01, min(0.02 * 2**attempt, 0.25)))

    with transaction.atomic():
        return operation()


def _is_write_conflict(error: OperationalError) -> bool:
    cause = error.__cause__
    sqlite_code = getattr(cause, "sqlite_errorcode", None)
    if sqlite_code is not None:
        return (sqlite_code & 0xFF) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
    sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    return sqlstate in ("40001", "40P01")
