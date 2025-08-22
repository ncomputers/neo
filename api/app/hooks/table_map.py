import json
from datetime import datetime, timezone

from ..models_tenant import Table


async def publish_table_state(table: Table) -> None:
    """Publish table position and state to the real-time map channel."""
    from ..main import redis_client  # lazy import to avoid circular deps

    channel = f"rt:table_map:{table.tenant_id}"
    payload = {
        "table_id": str(table.id),
        "code": table.code,
        "state": table.state,
        "x": table.pos_x,
        "y": table.pos_y,
        "ts": datetime.now(timezone.utc).timestamp(),
    }
    try:
        await redis_client.publish(channel, json.dumps(payload))
    except Exception:  # pragma: no cover - best effort
        pass
