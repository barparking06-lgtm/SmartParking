import time
import RPi.GPIO as GPIO

from config import (
    ENTRY_KEYPAD_ROWS, ENTRY_KEYPAD_COLS,
    EXIT_KEYPAD_ROWS, EXIT_KEYPAD_COLS
)

from access.keypad_reader import KeypadReader


def main():
    print("=" * 50)
    print("Keypad GPIO test")
    print("=" * 50)
    print("This test uses the same KeypadReader class as main.py")
    print("Therefore debounce and wait-for-release are identical to the real system.")
    print()
    print("Expected keypad layout:")
    print("1 2 3 A")
    print("4 5 6 B")
    print("7 8 9 C")
    print("* 0 # D")
    print()
    print("Press Ctrl+C to stop.")
    print()

    print("ENTRY rows:", ENTRY_KEYPAD_ROWS)
    print("ENTRY cols:", ENTRY_KEYPAD_COLS)
    print("EXIT rows :", EXIT_KEYPAD_ROWS)
    print("EXIT cols :", EXIT_KEYPAD_COLS)
    print()

    entry_keypad = KeypadReader(ENTRY_KEYPAD_ROWS, ENTRY_KEYPAD_COLS)
    exit_keypad = KeypadReader(EXIT_KEYPAD_ROWS, EXIT_KEYPAD_COLS)

    try:
        while True:
            key = entry_keypad.read_key()
            if key:
                print(f"ENTRY keypad: {key}")

            key = exit_keypad.read_key()
            if key:
                print(f"EXIT keypad : {key}")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nTest stopped by user.")

    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
