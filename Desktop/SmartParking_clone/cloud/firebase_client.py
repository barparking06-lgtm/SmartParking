# cloud/firebase_client.py
# =========================
# All Firebase operations in one place.
# Instead of scattering requests.get and requests.patch across files,
# every Firebase call goes through this class.

import requests
from datetime import datetime
from config import FIREBASE_URL


def _now_local_iso():
    """Return current local time in ISO 8601 with timezone offset.
    Example output: '2026-04-25T22:50:59+03:00'
    Human-readable in Firebase, unambiguous for parsing.
    """
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


class FirebaseClient:
    """Manages all calls to Firebase Realtime Database."""

    def __init__(self, url=None):
        self.url = url or FIREBASE_URL

    # ========== Orders ==========

    def get_all_orders(self):
        """Fetch all orders from Firebase.
        Returns a dict of orders, or None on failure.
        """
        try:
            response = requests.get(f"{self.url}/orders.json", timeout=5)
            return response.json()
        except Exception as e:
            print(f"[Firebase] Error getting orders: {e}")
            return None

    def verify_code(self, entered_code):
        """Check whether the entered code is valid.

        Valid code = exists in Firebase AND the user has not entered yet
        (enteredAt is None).

        Returns: (True, order_id, order_data) if valid
                 (False, None, None) if not valid
        """
        orders = self.get_all_orders()
        if not orders:
            return False, None, None

        for order_id, order in orders.items():
            # Compare as string -- the code can arrive as int or string
            if str(order.get("code")) == str(entered_code):
                # Make sure the user has not entered yet
                if order.get("enteredAt") is None:
                    return True, order_id, order

        return False, None, None

    def mark_entry(self, order_id):
        """Mark that the user entered the parking lot -- store the actual
        entry time. This timestamp is used later for billing.
        """
        entry_time = _now_local_iso()
        try:
            requests.patch(
                f"{self.url}/orders/{order_id}.json",
                json={"enteredAt": entry_time},
                timeout=5
            )
            return entry_time
        except Exception as e:
            print(f"[Firebase] Error marking entry: {e}")
            return None

    def mark_exit(self, order_id, exit_time, duration_min, amount):
        """Mark that the user exited the parking lot -- store payment details."""
        try:
            requests.patch(
                f"{self.url}/orders/{order_id}.json",
                json={
                    "exitedAt": exit_time,
                    "durationMinutes": duration_min,
                    "amountCharged": amount,
                    "paid": True
                },
                timeout=5
            )
            return True
        except Exception as e:
            print(f"[Firebase] Error marking exit: {e}")
            return False

    def delete_order(self, order_id):
        """Delete an order (e.g. after expiration)."""
        try:
            requests.delete(f"{self.url}/orders/{order_id}.json", timeout=5)
            return True
        except Exception as e:
            print(f"[Firebase] Error deleting order: {e}")
            return False

    # ========== Parking status ==========

    def update_parking_status(self, free_count, total, results):
        """Update parking lot status in Firebase.

        results = list of dicts with index, status, ratio for each space.
        """
        data = {
            "totalSpots": total,
            "occupiedSpots": total - free_count,
            "freeSpots": free_count,
            "isFull": free_count == 0,
            "lastUpdated": _now_local_iso(),
            "spaces": {}
        }
        for r in results:
            data["spaces"][f"space_{r['index']}"] = {
                "status": r["status"],
                "fillRatio": round(r["ratio"], 4)
            }
        try:
            requests.patch(f"{self.url}/parking.json", json=data, timeout=5)
        except Exception as e:
            print(f"[Firebase] Error updating parking status: {e}")

    def get_parking_status(self):
        """Fetch the current parking lot status."""
        try:
            response = requests.get(f"{self.url}/parking.json", timeout=5)
            return response.json()
        except Exception as e:
            print(f"[Firebase] Error getting parking status: {e}")
            return None