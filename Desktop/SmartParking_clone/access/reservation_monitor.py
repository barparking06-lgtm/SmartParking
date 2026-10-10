# access/reservation_monitor.py
import time
import requests
from datetime import datetime, timezone
from config import RESERVATION_TIMEOUT_SEC, FIREBASE_URL
from cloud.email_service import EmailService


class ReservationMonitor:
    def __init__(self, firebase_client):
        self.fb = firebase_client
        self.email = EmailService()

    def check_expired(self):
        orders = self.fb.get_all_orders()
        if not orders:
            return

        now = datetime.now(timezone.utc)
        for order_id, order in orders.items():
            # Only check orders that haven't entered yet and aren't already expired
            if order.get("enteredAt") is not None:
                continue
            if order.get("status") == "expired":
                continue

            ordered_at_str = order.get("orderedAt", "")
            if not ordered_at_str:
                continue

            try:
                ordered_at = datetime.fromisoformat(
                    ordered_at_str.replace("Z", "+00:00")
                )
                elapsed = (now - ordered_at).total_seconds()

                if elapsed > RESERVATION_TIMEOUT_SEC:
                    first_name = order.get("firstName", "Guest")
                    email = order.get("email", "")
                    print(f"[Reservation] EXPIRED: {first_name} "
                          f"(order {order_id}, ordered {int(elapsed)}s ago)")

                    # Local time string with timezone offset
                    expired_at = (datetime.now()
                                  .astimezone()
                                  .replace(microsecond=0)
                                  .isoformat())

                    # Mark expired AND remove the code so it can't be used
                    # for entry anymore. The rest of the order is kept for
                    # history (firstName, email, orderedAt, etc.).
                    try:
                        # 1. Set expired status + timestamp
                        requests.patch(
                            f"{FIREBASE_URL}/orders/{order_id}.json",
                            json={
                                "status": "expired",
                                "paid": "expired",
                                "expiredAt": expired_at
                            },
                            timeout=5
                        )
                        # 2. Delete just the 'code' field. In Firebase REST,
                        # PATCHing a field to null deletes it.
                        requests.patch(
                            f"{FIREBASE_URL}/orders/{order_id}.json",
                            json={"code": None},
                            timeout=5
                        )
                        print(f"[Reservation] Cleared code for {order_id}")
                    except Exception as e:
                        print(f"[Reservation] Firebase update error: {e}")

                    # Send expiry email -- include the order_id as a reference
                    if email:
                        self.email.send_reservation_expired(
                            email, first_name, order_id
                        )

            except Exception as e:
                print(f"[Reservation] Error checking order {order_id}: {e}")

    def run(self, interval=30):
        print("[Reservation] Monitor started (checking every 30s)")
        while True:
            try:
                self.check_expired()
            except Exception as e:
                print(f"[Reservation] Error: {e}")
            time.sleep(interval)