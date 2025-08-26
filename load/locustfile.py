import os
import uuid

import gevent
from locust import HttpUser, between, events, task

TABLE_TOKEN = os.getenv("TABLE_TOKEN", "T-001")
MENU_PATH = f"/g/{TABLE_TOKEN}/menu"
ORDER_PATH = f"/g/{TABLE_TOKEN}/order"
BILL_PATH = f"/g/{TABLE_TOKEN}/bill"
TENANT = os.getenv("TENANT", "demo")
SSE_PATH = f"/api/outlet/{TENANT}/tables/map/stream"

P95_MENU_MS = 200
P95_ORDER_MS = 400


class GuestUser(HttpUser):
    """Simulate guest interactions for menu, orders and bills."""

    host = os.environ.get("HOST", "http://localhost:8000")
    wait_time = between(1, 5)
    _etag: str | None = None

    @task
    def view_menu(self) -> None:
        """Fetch the menu using conditional requests to exercise 304s."""

        headers = {}
        if self._etag:
            headers["If-None-Match"] = self._etag
        resp = self.client.get(MENU_PATH, headers=headers)
        if resp.status_code == 200 and "ETag" in resp.headers:
            self._etag = resp.headers["ETag"]

    @task
    def place_order(self) -> None:
        """Place an order using an idempotency key."""

        payload = {"items": [{"item_id": "1", "qty": 1}]}
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        self.client.post(ORDER_PATH, json=payload, headers=headers)

    @task
    def generate_bill(self) -> None:
        """Generate a bill and apply a sample coupon."""

        self.client.get(BILL_PATH)
        self.client.get(BILL_PATH, params={"coupon": "SAVE5"})


class TableStreamUser(HttpUser):
    """Maintain a steady SSE connection for table map updates."""

    host = os.environ.get("HOST", "http://localhost:8000")
    wait_time = between(60, 60)
    _reader = None

    def on_start(self) -> None:  # pragma: no cover - streaming
        resp = self.client.get(SSE_PATH, stream=True, name="table_sse")
        self._reader = gevent.spawn(lambda: [line for line in resp.iter_lines()])

    @task
    def listen(self) -> None:  # pragma: no cover - streaming
        gevent.sleep(60)

    def on_stop(self) -> None:  # pragma: no cover - streaming
        if self._reader:
            self._reader.kill()


@events.test_stop.add_listener
def verify_thresholds(environment, **kwargs) -> None:
    """Fail the test run when p95 targets are not met."""

    failures: list[str] = []
    menu = environment.stats.get(MENU_PATH, "GET")
    if menu and menu.get_response_time_percentile(0.95) > P95_MENU_MS:
        failures.append(f"menu p95>{P95_MENU_MS}ms")
    order = environment.stats.get(ORDER_PATH, "POST")
    if order and order.get_response_time_percentile(0.95) > P95_ORDER_MS:
        failures.append(f"order p95>{P95_ORDER_MS}ms")
    if failures:
        print("Performance thresholds not met:", ", ".join(failures))
        environment.process_exit_code = 1
