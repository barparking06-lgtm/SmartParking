# esp32_comm/mqtt_bridge.py
# ==========================
# Pi -> ESP32 command channel via MQTT.

import json
import paho.mqtt.client as mqtt
from config import (
    MQTT_BROKER, MQTT_PORT,
    MQTT_TOPIC_ENTRY, MQTT_TOPIC_EXIT,
    MQTT_TOPIC_ENTRY_DISPLAY, MQTT_TOPIC_EXIT_DISPLAY,
)


class MQTTBridge:
    """Pi -> ESP32 commands over MQTT."""

    def __init__(self):
        self.client = mqtt.Client()
        self.connected = False

    def connect(self):
        """Connect to the MQTT broker."""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.client.loop_start()
            self.connected = True
            print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            print(f"[MQTT] Connection failed: {e}")
            self.connected = False

    # ===== Existing entry/exit barrier commands =====

    def send_entry_command(self, first_name):
        """Open the entry barrier; ESP32 also greets the driver on the entry LCD."""
        message = {"action": "open_entry", "firstName": first_name}
        self._publish(MQTT_TOPIC_ENTRY, message)

    def send_close_entry_command(self):
        message = {"action": "close_entry"}
        self._publish(MQTT_TOPIC_ENTRY, message)

    def send_exit_show_amount(self, amount, first_name):
        """Show the amount due on the exit LCD and wait for the RFID card scan."""
        message = {
            "action": "show_amount",
            "amount": amount,
            "firstName": first_name,
        }
        self._publish(MQTT_TOPIC_EXIT, message)

    def send_exit_open_command(self):
        message = {"action": "open_exit"}
        self._publish(MQTT_TOPIC_EXIT, message)

    def send_close_exit_command(self):
        message = {"action": "close_exit"}
        self._publish(MQTT_TOPIC_EXIT, message)

    # ===== Step 12: keypad input mirroring on the LCDs =====

    def send_entry_display_buffer(self, buffer):
        """Mirror the current entry-keypad input on the entry LCD.
        `buffer` is the string typed so far, e.g. '' or '12' or '1234'.
        """
        message = {"action": "show_buffer", "buffer": buffer}
        self._publish(MQTT_TOPIC_ENTRY_DISPLAY, message)

    def send_entry_display_invalid(self):
        """Show 'Invalid code' on the entry LCD (auto-clears after ~2.5s)."""
        message = {"action": "show_invalid"}
        self._publish(MQTT_TOPIC_ENTRY_DISPLAY, message)

    def send_exit_display_buffer(self, buffer):
        """Mirror the current exit-keypad input on the exit LCD."""
        message = {"action": "show_buffer", "buffer": buffer}
        self._publish(MQTT_TOPIC_EXIT_DISPLAY, message)

    def send_exit_display_invalid(self):
        """Show 'Invalid code' on the exit LCD (auto-clears after ~2.5s)."""
        message = {"action": "show_invalid"}
        self._publish(MQTT_TOPIC_EXIT_DISPLAY, message)

    # ===== Internals =====

    def _publish(self, topic, message):
        if not self.connected:
            print("[MQTT] Not connected! Trying to reconnect...")
            self.connect()

        payload = json.dumps(message)
        result = self.client.publish(topic, payload)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[MQTT] Sent to {topic}: {payload}")
        else:
            print(f"[MQTT] Failed to send to {topic}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        print("[MQTT] Disconnected")