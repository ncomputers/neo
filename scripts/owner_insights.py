#!/usr/bin/env python3
"""Weekly owner insights digest with email attachments.

Generates a week over week summary, produces rule based insights and sends
them via email with both CSV and PDF attachments. Database access is
intentionally stubbed for future expansion.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Mapping

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api.app.pdf.render import render_template  # type: ignore
from api.app.providers import email_stub  # type: ignore

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


def generate_insights(metrics: Mapping[str, Any]) -> List[str]:
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


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "insights"
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape()
)


def fetch_metrics(tenant: str, week_start: date) -> Dict[str, Any]:
    """Fetch metrics for ``tenant`` starting ``week_start``.

    This is a stub that returns zeroed metrics and should be replaced with
    real database queries in production.
    """

    return {
        "gross_sales": 0.0,
        "orders": 0,
        "prep_p50": 0.0,
        "prep_p95": 0.0,
        "sla_hit_rate": 0.0,
        "top_items": [],
        "coupon_orders": 0,
    }


def _render(template: str, **ctx: Any) -> str:
    return _env.get_template(template).render(**ctx)


def build_csv(metrics: Mapping[str, Any]) -> str:
    """Return CSV string for ``metrics``."""

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    top_items = metrics.get("top_items", [])
    flat = dict(metrics)
    flat["top_items"] = "; ".join(f"{n}({q})" for n, q in top_items)
    for key, val in flat.items():
        writer.writerow([key, val])
    return buf.getvalue()


def build_pdf(tenant: str, metrics: Mapping[str, Any], insights: List[str]) -> bytes:
    """Return PDF bytes for ``tenant`` using ``metrics`` and ``insights``."""

    pdf_bytes, _ = render_template(
        "insights/weekly_pdf.html",
        {"tenant": tenant, "metrics": metrics, "insights": insights},
    )
    return pdf_bytes


def send_email(tenant: str, metrics: Mapping[str, Any], insights: List[str]) -> None:
    """Send weekly insights email with attachments."""

    csv_data = build_csv(metrics).encode("utf-8")
    pdf_data = build_pdf(tenant, metrics, insights)
    html_body = _render(
        "email_weekly.html", tenant=tenant, metrics=metrics, insights=insights
    )
    text_body = _render(
        "email_weekly.txt", tenant=tenant, metrics=metrics, insights=insights
    )
    payload = {
        "subject": f"Weekly owner digest for {tenant}",
        "text": text_body,
        "html": html_body,
        "attachments": [
            ("weekly.csv", csv_data, "text/csv"),
            ("weekly.pdf", pdf_data, "application/pdf"),
        ],
    }
    target = os.getenv("OWNER_INSIGHTS_EMAIL")
    email_stub.send("owner.insights", payload, target)


def main(tenant: str, week_start: str) -> None:
    """Entry point for weekly owner insights."""

    day = datetime.strptime(week_start, "%Y-%m-%d").date()
    metrics = fetch_metrics(tenant, day)
    insights = generate_insights(metrics)
    send_email(tenant, metrics, insights)


def _parse_week_start(value: str) -> date:
    if value == "last_mon":
        today = date.today()
        return today - timedelta(days=today.weekday() + 7)
    return datetime.strptime(value, "%Y-%m-%d").date()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly owner insights")
    parser.add_argument(
        "--week_start",
        default="last_mon",
        help="ISO date for week start (Monday) or 'last_mon'",
    )
    parser.add_argument(
        "--tenants",
        nargs="+",
        default=["all"],
        help="Tenant identifiers (space/comma separated) or 'all'",
    )
    args = parser.parse_args()

    week_start = _parse_week_start(args.week_start)
    tenants: List[str] = []
    for item in args.tenants:
        tenants.extend(t for t in item.split(",") if t)

    for tenant in tenants:
        main(tenant, week_start.isoformat())


if __name__ == "__main__":
    _cli()
