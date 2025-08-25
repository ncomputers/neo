from __future__ import annotations

import hashlib
import logging
import os
import random
import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

SLOW_QUERY_MS = int(os.getenv("DB_SLOW_QUERY_MS", "200"))
SAMPLE_RATE = 0.01

logger = logging.getLogger("obs")


def add_query_logger(engine: Engine, tenant: str) -> None:
    """Attach timing-based logging to ``engine`` for ``tenant``."""
    target = engine.sync_engine if hasattr(engine, "sync_engine") else engine

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):  # type: ignore[no-untyped-def]
        context._query_start_time = time.perf_counter()

    def after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):  # type: ignore[no-untyped-def]
        total_ms = (time.perf_counter() - context._query_start_time) * 1000
        sql = " ".join(statement.split())
        if len(sql) > 200:
            sql = sql[:197] + "..."
        params_hash = hashlib.sha256(repr(parameters).encode()).hexdigest()[:8]
        if total_ms > SLOW_QUERY_MS:
            logger.warning(
                "slow query %dms tenant=%s sql=%s params=%s",
                int(total_ms),
                tenant,
                sql,
                params_hash,
            )
        elif random.random() < SAMPLE_RATE:
            logger.info(
                "query %dms tenant=%s sql=%s params=%s",
                int(total_ms),
                tenant,
                sql,
                params_hash,
            )

    event.listen(target, "before_cursor_execute", before_cursor_execute)
    event.listen(target, "after_cursor_execute", after_cursor_execute)
