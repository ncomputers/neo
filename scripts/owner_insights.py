#!/usr/bin/env python3
"""Weekly owner insights digest.

Generates a week over week report for key operational metrics and
produces simple rule based insights. Database access and delivery
mechanisms are intentionally stubbed for future expansion.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Mapping

MetricDict = Mapping[str, float]


@dataclass
class Delta:
    value: float
    delta: float
    arrow: str


def compute_deltas(current: MetricDict, previous: MetricDict) -> Dict[str, Delta]:
    """Return week over week deltas with arrow indicators."""

    result: Dict[str, Delta] = {}
    for key, curr in current.items():
        prev = previous.get(key, 0.0)
        diff = curr - prev
        arrow = "→"
        if curr > prev:
            arrow = "↑"
        elif curr < prev:
            arrow = "↓"
        result[key] = Delta(value=curr, delta=diff, arrow=arrow)
    return result


def generate_insights(metrics: Mapping[str, float]) -> List[str]:
    """Return a list of insight strings based on simple heuristics."""

    insights: List[str] = []
    sla_hit = metrics.get("sla_hit_rate", 0.0)
    if sla_hit < 0.85:
        insights.append(
            "SLA hit rate below 85%—consider menu batching or staffing tweaks."
        )

    cancellations = metrics.get("cancellations_by_item", {})
    total_cancels = sum(cancellations.values())
    for item, qty in cancellations.items():
        if total_cancels and qty / total_cancels > 0.3:
            insights.append(
                f"{item} causes over 30% of cancellations—consider disabling or fixing prep."
            )
            break

    coupon_pct = metrics.get("coupon_order_pct")
    aov_delta = metrics.get("aov_delta")
    if (
        coupon_pct is not None
        and coupon_pct > 0.1
        and aov_delta is not None
        and aov_delta < 0
    ):
        insights.append(
            "New coupon drives >10% orders but lowers AOV—consider capping usage."
        )

    clicks = metrics.get("referral_clicks", 0.0)
    conv = metrics.get("referral_conversions", 0.0)
    if clicks > 0 and conv == 0:
        insights.append(
            "Referral link got clicks but no conversions—consider a follow-up CTA."
        )

    return insights


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly owner insights")
    parser.add_argument(
        "--week_start", required=True, help="ISO date for week start (Monday)"
    )
    parser.add_argument("--tenant", default="all", help="Tenant identifier or 'all'")
    args = parser.parse_args()

    week_start = datetime.strptime(args.week_start, "%Y-%m-%d").date()
    week_end = week_start + timedelta(days=6)
    print(
        f"Generating insights for {args.tenant} from {week_start.isoformat()} to {week_end.isoformat()}"
    )


if __name__ == "__main__":
    _cli()
