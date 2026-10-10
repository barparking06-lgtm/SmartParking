import threading
import time
import json
import paho.mqtt.client as mqtt

from config import (
    ENTRY_KEYPAD_ROWS, ENTRY_KEYPAD_COLS,
    EXIT_KEYPAD_ROWS, EXIT_KEYPAD_COLS,
    PARKING_CHECK_INTERVAL,
    MQTT_BROKER, MQTT_PORT
)
from camera.capture_frame import init_camera, capture_frame
from camera.parking_detector import (
    load_parking_spaces, preprocess_frame,
    analyze_space_occupancy, get_free_count
)
from camera.marker_registration import MarkerRegistration
from cloud.firebase_client import FirebaseClient
from esp32_comm.mqtt_bridge import MQTTBridge
from access.keypad_reader import KeypadReader
from access.session_manager import SessionManager
from access.reservation_monitor import ReservationMonitor


def parking_monitor(picam2, spaces, firebase, registration):
    total = len(spaces)
    while True:
        try:
            frame_bgr = capture_frame(picam2)
            corrected, success = registration.correct_frame(frame_bgr)
            if success:
                clean = preprocess_frame(corrected)
            else:
                clean = preprocess_frame(frame_bgr)
            results = analyze_space_occupancy(spaces, clean)
            free_count = get_free_count(results)
            status_list = [r["status"] for r in results]
            firebase.update_parking_status(free_count, total, results)
            timestamp = time.strftime("%H:%M:%S")
            tag = "OK" if success else "RAW"
            print(f"[{timestamp}] [{tag}] Free: {free_count}/{total} | {status_list}")
        except Exception as e:
            print(f"[Monitor] Error: {e}")
        time.sleep(PARKING_CHECK_INTERVAL)


def entry_listener(session_manager, keypad):
    while True:
        try:
            code = keypad.read_code(4)
            session_manager.handle_entry(code)
        except Exception as e:
            print(f"[Entry] Error: {e}")


def exit_listener(session_manager, keypad):
    while True:
        try:
            code = keypad.read_code(4)
            success, duration, amount, order = session_manager.handle_exit(code)
            if success:
                print("[Exit] Waiting for RFID payment from ESP32...")
        except Exception as e:
            print(f"[Exit] Error: {e}")


def on_rfid_message(client, userdata, msg):
    session = userdata
    try:
        data = json.loads(msg.payload)
        if data.get("status") == "paid":
            print("[RFID] Payment confirmed by ESP32!")
            session.complete_exit()
    except Exception as e:
        print(f"[RFID] Error: {e}")


def main():
    print("=" * 50)
    print("  Smart Parking System")
    print("=" * 50)
    print("[Init] Loading parking spaces...")
    spaces = load_parking_spaces()
    print(f"[Init] Found {len(spaces)} parking spaces")
    print("[Init] Loading marker registration...")
    registration = MarkerRegistration()
    print("[Init] Marker registration ready")
    print("[Init] Starting camera...")
    picam2 = init_camera()
    print("[Init] Connecting to Firebase...")
    firebase = FirebaseClient()
    print("[Init] Connecting to MQTT broker...")
    mqtt_bridge = MQTTBridge()
    mqtt_bridge.connect()

    print("[Init] Setting up keypads...")
    # Step 12: each keypad mirrors its input on its own LCD via MQTT.
    # The lambdas wire the keypad's on_buffer_change callback to the
    # matching display-publish method on the MQTT bridge.
    entry_keypad = KeypadReader(
        ENTRY_KEYPAD_ROWS, ENTRY_KEYPAD_COLS,
        on_buffer_change=lambda buf: mqtt_bridge.send_entry_display_buffer(buf)
    )
    exit_keypad = KeypadReader(
        EXIT_KEYPAD_ROWS, EXIT_KEYPAD_COLS,
        on_buffer_change=lambda buf: mqtt_bridge.send_exit_display_buffer(buf)
    )

    session = SessionManager(firebase, mqtt_bridge)
    rfid_listener = mqtt.Client(userdata=session)
    rfid_listener.on_message = on_rfid_message
    rfid_listener.connect(MQTT_BROKER, MQTT_PORT)
    rfid_listener.subscribe("parking/rfid_ok")
    rfid_listener.loop_start()
    print("[Init] RFID listener ready")
    res_monitor = ReservationMonitor(firebase)
    print("[Init] System ready")

    monitor_thread = threading.Thread(
        target=parking_monitor,
        args=(picam2, spaces, firebase, registration),
        daemon=True
    )
    monitor_thread.start()
    entry_thread = threading.Thread(
        target=entry_listener,
        args=(session, entry_keypad),
        daemon=True
    )
    entry_thread.start()
    exit_thread = threading.Thread(
        target=exit_listener,
        args=(session, exit_keypad),
        daemon=True
    )
    exit_thread.start()
    reservation_thread = threading.Thread(
        target=res_monitor.run,
        daemon=True
    )
    reservation_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[System] Shutting down...")
        mqtt_bridge.disconnect()
        rfid_listener.loop_stop()
        picam2.stop()
        entry_keypad.cleanup()
        exit_keypad.cleanup()
        print("[System] Done.")


if __name__ == "__main__":
    main()