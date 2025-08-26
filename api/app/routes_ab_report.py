from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from prometheus_client import REGISTRY

router = APIRouter()


@router.get("/exp/ab/report")
async def ab_report(
    experiment: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(..., alias="to"),
) -> dict:
    """Return exposure and conversion stats for an experiment."""
    # Validate date strings but they are otherwise unused.
    try:
        datetime.fromisoformat(from_)
        datetime.fromisoformat(to)
    except ValueError:
        pass

    exposures_samples = []
    conversions_samples = []
    for metric in REGISTRY.collect():
        if metric.name == "ab_exposures":
            exposures_samples = [
                s
                for s in metric.samples
                if s.name.endswith("_total")
                and s.labels.get("experiment") == experiment
            ]
        elif metric.name == "ab_conversions":
            conversions_samples = [
                s
                for s in metric.samples
                if s.name.endswith("_total")
                and s.labels.get("experiment") == experiment
            ]

    exposure_map = {s.labels["variant"]: s.value for s in exposures_samples}
    conversion_map = {s.labels["variant"]: s.value for s in conversions_samples}

    stats: list[dict] = []
    for variant in sorted(set(exposure_map) | set(conversion_map)):
        exposures = exposure_map.get(variant, 0.0)
        conversions = conversion_map.get(variant, 0.0)
        conv_rate = conversions / exposures if exposures else 0.0
        stats.append(
            {
                "name": variant,
                "exposures": exposures,
                "conversions": conversions,
                "conv_rate": conv_rate,
                "lift_vs_control": 0.0,
            }
        )

    control_rate = next((s["conv_rate"] for s in stats if s["name"] == "control"), 0.0)
    for s in stats:
        if s["name"] == "control" or control_rate == 0:
            s["lift_vs_control"] = 0.0
        else:
            s["lift_vs_control"] = s["conv_rate"] / control_rate - 1

    return {"variant_stats": stats}
