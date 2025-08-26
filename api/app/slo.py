"""In-memory SLO tracking utilities."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Deque, Dict, Tuple


class SLOTracker:
    """Track requests and errors per route within a rolling window."""

    def __init__(self, window_days: int = 30) -> None:
        self.window = timedelta(days=window_days)
        self.requests: Dict[str, Deque[Tuple[datetime, int]]] = defaultdict(deque)
        self.errors: Dict[str, Deque[Tuple[datetime, int]]] = defaultdict(deque)

    def _prune(self, q: Deque[Tuple[datetime, int]], now: datetime) -> None:
        cutoff = now - self.window
        while q and q[0][0] < cutoff:
            q.popleft()

    def _add(
        self, q: Deque[Tuple[datetime, int]], now: datetime, count: int = 1
    ) -> None:
        if q and q[-1][0].date() == now.date():
            ts, c = q[-1]
            q[-1] = (ts, c + count)
        else:
            q.append((now, count))

    def record(self, route: str, error: bool = False) -> None:
        now = datetime.utcnow()
        rq = self.requests[route]
        self._prune(rq, now)
        self._add(rq, now)
        if error:
            er = self.errors[route]
            self._prune(er, now)
            self._add(er, now)

    def report(self) -> dict[str, dict[str, float | int]]:
        now = datetime.utcnow()
        result: dict[str, dict[str, float | int]] = {}
        for route, rq in self.requests.items():
            self._prune(rq, now)
            total_r = sum(c for _, c in rq)
            er = self.errors.get(route, deque())
            self._prune(er, now)
            total_e = sum(c for _, c in er)
            budget = 1 - (total_e / total_r) if total_r else 1.0
            result[route] = {
                "requests": total_r,
                "errors": total_e,
                "error_budget": budget,
            }
        return result


slo_tracker = SLOTracker()
