# access/session_manager.py
import math
from datetime import datetime
from config import PRICE_PER_MINUTE
from cloud.email_service import EmailService


def _parse_iso(s):
    """Parse ISO 8601 -> tz-aware datetime. Handles both 'Z' and '+HH:MM'."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


class SessionManager:
    def __init__(self, firebase_client, mqtt_bridge):
        self.fb = firebase_client
        self.mqtt = mqtt_bridge
        self.pending_exit = None
        self.email = EmailService()

    def handle_entry(self, entered_code):
        valid, order_id, order = self.fb.verify_code(entered_code)
        if not valid:
            print("[Entry] ACCESS DENIED - Invalid code")
            self.mqtt.send_entry_display_invalid()
            return False, None

        entry_time = self.fb.mark_entry(order_id)
        if entry_time is None:
            print("[Entry] Error saving entry time")
            self.mqtt.send_entry_display_invalid()
            return False, None

        first_name = order.get("firstName", "Guest")
        print(f"[Entry] ACCESS GRANTED - Welcome {first_name}! "
              f"order={order_id} enteredAt={entry_time}")
        self.mqtt.send_entry_command(first_name)
        return True, order

    def handle_exit(self, entered_code):
        orders = self.fb.get_all_orders()
        if not orders:
            print("[Exit] No orders found")
            self.mqtt.send_exit_display_invalid()
            return False, 0, 0, None

        for order_id, order in orders.items():
            if (str(order.get("code")) == str(entered_code)
                    and order.get("enteredAt") is not None
                    and order.get("exitedAt") is None):

                # Both timestamps are tz-aware; subtraction is correct
                # regardless of timezone or DST.
                entry_time = _parse_iso(order["enteredAt"])
                exit_time = datetime.now().astimezone()

                duration = exit_time - entry_time
                total_seconds = duration.total_seconds()

                if total_seconds < 0:
                    print(f"[Exit] WARNING: negative duration {total_seconds:.1f}s")

                # Round UP -- every started minute is billed (standard practice).
                duration_minutes = max(1, math.ceil(total_seconds / 60))
                amount = round(duration_minutes * PRICE_PER_MINUTE, 2)

                first_name = order.get("firstName", "Guest")
                exit_time_str = exit_time.replace(microsecond=0).isoformat()

                print(f"[Exit] {first_name}: order={order_id} "
                      f"enteredAt={order['enteredAt']} "
                      f"exitedAt={exit_time_str} "
                      f"raw_seconds={total_seconds:.1f} "
                      f"duration_minutes={duration_minutes} "
                      f"amount={amount} NIS")

                self.mqtt.send_exit_show_amount(amount, first_name)

                self.pending_exit = {
                    "order_id": order_id,
                    "exit_time": exit_time_str,
                    "entry_time_dt": entry_time,
                    "exit_time_dt": exit_time,
                    "duration": duration_minutes,
                    "amount": amount,
                    "order": order,
                }
                return True, duration_minutes, amount, order

        print("[Exit] ACCESS DENIED - Invalid code or not entered yet")
        self.mqtt.send_exit_display_invalid()
        return False, 0, 0, None

    def complete_exit(self):
        if self.pending_exit is None:
            return False

        data = self.pending_exit
        order = data["order"]
        order_id = data["order_id"]

        self.fb.mark_exit(
            order_id,
            data["exit_time"],
            data["duration"],
            data["amount"],
        )

        self.email.send_exit_summary(
            order.get("email", ""),
            order.get("firstName", "Guest"),
            data["duration"],
            data["amount"],
            order_id,
            data["entry_time_dt"],
            data["exit_time_dt"],
        )

        print(f"[Exit] Session closed in Firebase (order={order_id})")
        self.pending_exit = None
        return True