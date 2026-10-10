# config.py
# ==========
# All configuration for the system in one place.

# ---- Firebase ----
FIREBASE_URL = "https://smartparkingbar-default-rtdb.firebaseio.com"

# ---- MQTT ----
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_ENTRY = "parking/entry"               # commands for entry barrier
MQTT_TOPIC_EXIT = "parking/exit"                 # commands for exit barrier
MQTT_TOPIC_ENTRY_DISPLAY = "parking/entry_display"   # entry LCD updates (Step 12)
MQTT_TOPIC_EXIT_DISPLAY = "parking/exit_display"     # exit LCD updates (Step 12)

# ---- Parking lot ----
TOTAL_SPOTS = 6
PRICE_PER_MINUTE = 0.10
RESERVATION_TIMEOUT_SEC = 120

# ---- Camera ----
CAMERA_RESOLUTION = (1640, 1232)
PARKING_CHECK_INTERVAL = 5

# ---- Entry keypad (GPIO BCM) ----
ENTRY_KEYPAD_ROWS = [17, 27, 22, 10]
ENTRY_KEYPAD_COLS = [9, 11, 25, 8]

# ---- Exit keypad (GPIO BCM) ----
EXIT_KEYPAD_ROWS = [12, 16, 20, 21]
EXIT_KEYPAD_COLS = [5, 6, 13, 19]

# ---- Keypad tuning (Step 12) ----
KEYPAD_DEBOUNCE_MS = 50
KEYPAD_RELEASE_POLL_MS = 20

# ---- Email ----
EMAIL_SENDER = "barparking06@gmail.com"
EMAIL_APP_PASSWORD = "lxjb asdx kvje osfq"

# ---- Spot occupancy detection ----
FILL_RATIO_THRESHOLD = 0.15
PARKING_SPACES_FILE = "data/parking_spaces.json"