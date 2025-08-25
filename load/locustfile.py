import os
import uuid

from locust import HttpUser, between, task

TABLE_TOKEN = os.getenv("TABLE_TOKEN", "T-001")
MENU_PATH = f"/g/{TABLE_TOKEN}/menu"
ORDER_PATH = f"/g/{TABLE_TOKEN}/order"
BILL_PATH = f"/g/{TABLE_TOKEN}/bill"


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
