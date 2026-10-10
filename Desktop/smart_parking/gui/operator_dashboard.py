import tkinter as tk
from tkinter import ttk
import requests
import time
import threading
import json
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from config import FIREBASE_URL, MQTT_BROKER, MQTT_PORT


class OperatorDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bar Parking - Operator Dashboard")
        self.root.geometry("800x900")
        self.root.configure(bg="#f5f5f5")

        self.system_status = {
            "firebase": {"status": "Checking...", "color": "gray"},
            "mqtt": {"status": "Checking...", "color": "gray"},
            "esp32": {"status": "Checking...", "color": "gray"},
            "camera": {"status": "Checking...", "color": "gray"},
            "entry_sensor": {"status": "Checking...", "color": "gray"},
            "exit_sensor": {"status": "Checking...", "color": "gray"},
            "rfid": {"status": "Checking...", "color": "gray"},
            "pca9685": {"status": "Checking...", "color": "gray"},
            "lcd_entry": {"status": "Checking...", "color": "gray"},
            "lcd_exit": {"status": "Checking...", "color": "gray"},
        }

        self.esp32_last_seen = 0
        self.setup_mqtt_monitor()
        self.build_gui()
        self.update_data()

    def setup_mqtt_monitor(self):
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
            self.mqtt_client.loop_start()
            self.system_status["mqtt"]["status"] = "Connected"
            self.system_status["mqtt"]["color"] = "#27ae60"
        except Exception:
            self.system_status["mqtt"]["status"] = "Disconnected"
            self.system_status["mqtt"]["color"] = "#e74c3c"

    def on_mqtt_connect(self, client, userdata, flags, rc):
        client.subscribe("parking/heartbeat")
        client.subscribe("parking/entry")
        client.subscribe("parking/exit")
        client.subscribe("parking/rfid_ok")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)

            if msg.topic == "parking/heartbeat":
                self.esp32_last_seen = time.time()
                self.system_status["esp32"]["status"] = "Connected"
                self.system_status["esp32"]["color"] = "#27ae60"

                components = {
                    "entry_sensor": "Entry Ultrasonic",
                    "exit_sensor": "Exit Ultrasonic",
                    "rfid": "RFID Reader",
                    "pca9685": "PCA9685 Servos",
                    "lcd_entry": "LCD Entry",
                    "lcd_exit": "LCD Exit",
                }
                for key, name in components.items():
                    if key in data:
                        if data[key] == "ok":
                            self.system_status[key]["status"] = "OK"
                            self.system_status[key]["color"] = "#27ae60"
                        else:
                            self.system_status[key]["status"] = "ERROR"
                            self.system_status[key]["color"] = "#e74c3c"

            else:
                self.esp32_last_seen = time.time()
                self.system_status["esp32"]["status"] = "Connected"
                self.system_status["esp32"]["color"] = "#27ae60"

        except:
            pass

    def build_gui(self):
        canvas = tk.Canvas(self.root, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.main_frame = tk.Frame(canvas, bg="#f5f5f5")
        self.main_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Header
        header = tk.Frame(self.main_frame, bg="#2E5090", pady=15)
        header.pack(fill="x", padx=10, pady=(10, 5))
        tk.Label(header, text="Bar Parking", font=("Arial", 20, "bold"),
                bg="#2E5090", fg="white").pack()
        tk.Label(header, text="Operator Dashboard", font=("Arial", 12),
                bg="#2E5090", fg="#b0c4de").pack()

        # Parking Status
        self.build_section_label("Parking Status")

        cards_frame = tk.Frame(self.main_frame, bg="#f5f5f5")
        cards_frame.pack(fill="x", padx=10, pady=5)
        self.total_label = self.build_card(cards_frame, "Total Spots", "6", "#3498db", 0)
        self.free_label = self.build_card(cards_frame, "Free", "0", "#27ae60", 1)
        self.occupied_label = self.build_card(cards_frame, "Occupied", "0", "#e74c3c", 2)

        spaces_frame = tk.LabelFrame(self.main_frame, text=" Parking Spaces ",
            font=("Arial", 11, "bold"), bg="white", fg="#333", padx=10, pady=10)
        spaces_frame.pack(fill="x", padx=10, pady=5)

        self.space_labels = []
        grid = tk.Frame(spaces_frame, bg="white")
        grid.pack()
        for i in range(6):
            lbl = tk.Label(grid, text=f"  {i+1}  \nFREE", font=("Arial", 11, "bold"),
                          bg="#27ae60", fg="white", width=8, height=3, relief="raised")
            lbl.grid(row=0, column=i, padx=4, pady=4)
            self.space_labels.append(lbl)

        rev_frame = tk.Frame(self.main_frame, bg="#f5f5f5")
        rev_frame.pack(fill="x", padx=10, pady=5)
        self.revenue_label = self.build_card(rev_frame, "Today's Revenue", "0 NIS", "#8e44ad", 0)
        self.cars_label = self.build_card(rev_frame, "Cars Today", "0", "#e67e22", 1)
        self.expired_label = self.build_card(rev_frame, "Expired Today", "0", "#95a5a6", 2)

        orders_frame = tk.LabelFrame(self.main_frame, text=" Active Orders (Currently Parked) ",
            font=("Arial", 11, "bold"), bg="white", fg="#333", padx=10, pady=10)
        orders_frame.pack(fill="x", padx=10, pady=5)
        self.orders_list = tk.Frame(orders_frame, bg="white")
        self.orders_list.pack(fill="x")

        # System Diagnostics
        self.build_section_label("System Diagnostics")

        diag_frame = tk.LabelFrame(self.main_frame, text=" Component Status ",
            font=("Arial", 11, "bold"), bg="white", fg="#333", padx=10, pady=10)
        diag_frame.pack(fill="x", padx=10, pady=5)

        self.diag_labels = {}
        components = [
            ("firebase", "Firebase Database"),
            ("mqtt", "MQTT Broker (Mosquitto)"),
            ("esp32", "ESP32 Controller"),
            ("camera", "Camera Module"),
            ("pca9685", "PCA9685 Servo Driver *"),
            ("entry_sensor", "Entry Ultrasonic Sensor"),
            ("exit_sensor", "Exit Ultrasonic Sensor"),
            ("rfid", "RFID Reader"),
            ("lcd_entry", "LCD Entry Display"),
            ("lcd_exit", "LCD Exit Display"),
        ]

        for i, (key, name) in enumerate(components):
            row = tk.Frame(diag_frame, bg="white")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, font=("Arial", 11), bg="white",
                    fg="#333", anchor="w", width=25).pack(side="left")
            status_lbl = tk.Label(row, text="Checking...", font=("Arial", 11, "bold"),
                                 bg="white", fg="gray", anchor="e", width=15)
            status_lbl.pack(side="right")
            dot = tk.Label(row, text="\u25CF", font=("Arial", 14), bg="white", fg="gray")
            dot.pack(side="right", padx=5)
            self.diag_labels[key] = {"label": status_lbl, "dot": dot}

        # Note about motors
        tk.Label(diag_frame,
            text="* Motors cannot be tested remotely - only the driver board is monitored",
            font=("Arial", 9), bg="white", fg="#999").pack(anchor="w", pady=(5, 0))

        self.update_time_label = tk.Label(self.main_frame,
            text="Last update: --:--:--", font=("Arial", 10),
            bg="#f5f5f5", fg="#999")
        self.update_time_label.pack(pady=10)

    def build_section_label(self, text):
        frame = tk.Frame(self.main_frame, bg="#f5f5f5")
        frame.pack(fill="x", padx=10, pady=(15, 0))
        tk.Label(frame, text=text, font=("Arial", 14, "bold"),
                bg="#f5f5f5", fg="#2E5090").pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(5, 0))

    def build_card(self, parent, title, value, color, col):
        card = tk.Frame(parent, bg=color, padx=15, pady=10)
        card.grid(row=0, column=col, padx=5, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        tk.Label(card, text=title, font=("Arial", 10), bg=color, fg="white").pack()
        lbl = tk.Label(card, text=value, font=("Arial", 22, "bold"), bg=color, fg="white")
        lbl.pack()
        return lbl

    def update_data(self):
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        self.root.after(5000, self.update_data)

    def _fetch_and_update(self):
        try:
            resp = requests.get(f"{FIREBASE_URL}/parking.json", timeout=5)
            parking = resp.json()
            self.system_status["firebase"]["status"] = "Connected"
            self.system_status["firebase"]["color"] = "#27ae60"

            if parking:
                total = parking.get("totalSpots", 6)
                free = parking.get("freeSpots", 0)
                occupied = parking.get("occupiedSpots", 0)
                spaces = parking.get("spaces", {})
                last_updated = parking.get("lastUpdated", "")
                if last_updated:
                    self.system_status["camera"]["status"] = "Active"
                    self.system_status["camera"]["color"] = "#27ae60"
                self.root.after(0, lambda: self._update_parking(total, free, occupied, spaces))

            resp2 = requests.get(f"{FIREBASE_URL}/orders.json", timeout=5)
            orders = resp2.json()
            self.root.after(0, lambda: self._update_orders(orders if orders else {}))

        except Exception:
            self.system_status["firebase"]["status"] = "Error"
            self.system_status["firebase"]["color"] = "#e74c3c"
            self.system_status["camera"]["status"] = "Unknown"
            self.system_status["camera"]["color"] = "gray"

        if self.esp32_last_seen > 0 and time.time() - self.esp32_last_seen > 30:
            self.system_status["esp32"]["status"] = "No response"
            self.system_status["esp32"]["color"] = "#e74c3c"
            for key in ["entry_sensor", "exit_sensor", "rfid", "pca9685", "lcd_entry", "lcd_exit"]:
                self.system_status[key]["status"] = "Unknown"
                self.system_status[key]["color"] = "#e74c3c"
        elif self.esp32_last_seen == 0:
            self.system_status["esp32"]["status"] = "Waiting..."
            self.system_status["esp32"]["color"] = "#f39c12"

        self.root.after(0, self._update_diagnostics)
        now = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self.update_time_label.config(text=f"Last update: {now}"))

    def _update_parking(self, total, free, occupied, spaces):
        self.total_label.config(text=str(total))
        self.free_label.config(text=str(free))
        self.occupied_label.config(text=str(occupied))
        for i in range(min(6, len(self.space_labels))):
            space = spaces.get(f"space_{i}", {})
            status = space.get("status", "FREE")
            if status == "OCCUPIED":
                self.space_labels[i].config(text=f"  {i+1}  \nOCCUPIED", bg="#e74c3c")
            else:
                self.space_labels[i].config(text=f"  {i+1}  \nFREE", bg="#27ae60")

    def _update_orders(self, orders):
        for widget in self.orders_list.winfo_children():
            widget.destroy()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        revenue = 0.0
        cars_today = 0
        expired_today = 0
        active_orders = []

        for order_id, order in orders.items():
            if order.get("paid") == True and order.get("exitedAt", ""):
                exit_date = order.get("exitedAt", "")[:10]
                if exit_date == today:
                    revenue += order.get("amountCharged", 0)
                    cars_today += 1
            if order.get("status") == "expired":
                expired_date = order.get("expiredAt", "")[:10]
                if expired_date == today:
                    expired_today += 1
            if (order.get("enteredAt") is not None
                    and order.get("exitedAt") is None
                    and order.get("status") != "expired"):
                active_orders.append(order)

        self.revenue_label.config(text=f"{round(revenue, 2)} NIS")
        self.cars_label.config(text=str(cars_today))
        self.expired_label.config(text=str(expired_today))

        if not active_orders:
            tk.Label(self.orders_list, text="No cars currently parked",
                    font=("Arial", 11), bg="white", fg="#999").pack(pady=10)
        else:
            hdr = tk.Frame(self.orders_list, bg="#eee")
            hdr.pack(fill="x")
            tk.Label(hdr, text="Name", font=("Arial", 10, "bold"),
                    bg="#eee", width=15, anchor="w").pack(side="left", padx=5)
            tk.Label(hdr, text="Car", font=("Arial", 10, "bold"),
                    bg="#eee", width=12, anchor="w").pack(side="left", padx=5)
            tk.Label(hdr, text="Entered", font=("Arial", 10, "bold"),
                    bg="#eee", width=10, anchor="w").pack(side="left", padx=5)
            for order in active_orders:
                row = tk.Frame(self.orders_list, bg="white")
                row.pack(fill="x")
                name = f"{order.get('firstName', '')} {order.get('lastName', '')}"
                car = order.get("carNumber", "")
                entered = order.get("enteredAt", "")
                if entered:
                    try: entered = entered[11:16]
                    except: pass
                tk.Label(row, text=name, font=("Arial", 10),
                        bg="white", width=15, anchor="w").pack(side="left", padx=5, pady=2)
                tk.Label(row, text=car, font=("Arial", 10),
                        bg="white", width=12, anchor="w").pack(side="left", padx=5, pady=2)
                tk.Label(row, text=entered, font=("Arial", 10),
                        bg="white", width=10, anchor="w").pack(side="left", padx=5, pady=2)

    def _update_diagnostics(self):
        for key, widgets in self.diag_labels.items():
            status = self.system_status[key]
            widgets["label"].config(text=status["status"], fg=status["color"])
            widgets["dot"].config(fg=status["color"])

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/home/weaamadan/Desktop/smart_parking")
    app = OperatorDashboard()
    app.run()
