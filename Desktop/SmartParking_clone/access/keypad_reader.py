# access/keypad_reader.py
# ========================
# Reads a 4-digit code from a 4x4 matrix keypad.
#
# Step 12 features:
#   - # clears/cancels immediately at any time
#   - Software debounce + wait-for-release: one physical press = one event
#   - Optional on_buffer_change callback fires on every digit/clear,
#     so the caller can mirror the input on an LCD via MQTT.

import RPi.GPIO as GPIO
import time
import sys
from config import KEYPAD_DEBOUNCE_MS, KEYPAD_RELEASE_POLL_MS


class KeypadReader:
    """Reads a 4-digit code from a matrix keypad."""

    def __init__(self, row_pins, col_pins, on_buffer_change=None):
        """
        row_pins: list of 4 GPIO pins for rows
        col_pins: list of 4 GPIO pins for columns
        on_buffer_change: optional callback(buffer_str) that fires on
                          every change to the input buffer.
        """
        self.ROWS = row_pins
        self.COLS = col_pins
        self.on_buffer_change = on_buffer_change

        self.KEYS = [
            ['1', '2', '3', 'A'],
            ['4', '5', '6', 'B'],
            ['7', '8', '9', 'C'],
            ['*', '0', '#', 'D']
        ]

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        for row in self.ROWS:
            GPIO.setup(row, GPIO.OUT)
            GPIO.output(row, GPIO.HIGH)

        for col in self.COLS:
            GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _scan_once(self):
        """Scan the matrix once, return the pressed key or None.
        Raw read -- no debounce, no release-wait."""
        for i, row in enumerate(self.ROWS):
            GPIO.output(row, GPIO.LOW)
            for j, col in enumerate(self.COLS):
                if GPIO.input(col) == GPIO.LOW:
                    GPIO.output(row, GPIO.HIGH)
                    return self.KEYS[i][j]
            GPIO.output(row, GPIO.HIGH)
        return None

    def read_key(self):
        """Read a single key press, returning only after key release.
        One physical press = one logical event."""
        key = self._scan_once()
        if key is None:
            return None

        time.sleep(KEYPAD_DEBOUNCE_MS / 1000.0)
        key_confirm = self._scan_once()
        if key_confirm != key:
            return None

        # Wait for release
        while self._scan_once() is not None:
            time.sleep(KEYPAD_RELEASE_POLL_MS / 1000.0)

        return key

    def _notify(self, buffer):
        """Fire the buffer-change callback if one is set."""
        if self.on_buffer_change:
            try:
                self.on_buffer_change(buffer)
            except Exception as e:
                print(f"[Keypad] on_buffer_change error: {e}")

    def read_code(self, length=4):
        """Wait until the user enters a code of `length` digits.

        # = immediate clear/cancel.
        After `length` digits the code is auto-accepted.

        Each digit press and each clear fires on_buffer_change(buffer)
        so the LCD can mirror the user's input.
        """
        code = ""
        print(f"Enter {length}-digit code (# to clear):")
        sys.stdout.flush()

        # We deliberately do NOT publish an empty buffer here at the start.
        # That way the LCD keeps showing whatever it was showing (idle screen,
        # or "Invalid code" feedback from the previous attempt) until the user
        # actually starts typing.

        while True:
            key = self.read_key()
            if key is None:
                time.sleep(0.02)
                continue

            if key == '#':
                # Immediate clear/cancel. Only notify the LCD if there was
                # actually something to clear -- avoids overwriting useful
                # screens with "Code: _ _ _ _" when the user just walked up
                # and pressed # by mistake.
                if code:
                    code = ""
                    print("\nCleared.")
                    sys.stdout.flush()
                    self._notify(code)
                continue

            if key.isdigit():
                code += key
                print(f"Entered: {'*' * len(code)}")
                sys.stdout.flush()
                self._notify(code)

                if len(code) == length:
                    print(f"Code entered: {code}")
                    sys.stdout.flush()
                    return code

    def cleanup(self):
        """Release GPIO pins."""
        GPIO.cleanup()