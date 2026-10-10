import cv2
import time
from camera.capture_frame import init_camera, capture_frame
from camera.marker_registration import MarkerRegistration
from camera.parking_detector import (
    load_parking_spaces, preprocess_frame,
    analyze_space_occupancy, get_free_count, draw_results
)

print("Loading parking spaces...")
spaces = load_parking_spaces()
print(f"Found {len(spaces)} spaces")

print("Loading marker registration...")
reg = MarkerRegistration()

print("Starting camera...")
picam2 = init_camera()

print("Live preview starting...")
print("Press q to quit")

while True:
    frame = capture_frame(picam2)
    corrected, ok = reg.correct_frame(frame)
    if ok:
        use = corrected
    else:
        use = frame
    clean = preprocess_frame(use)
    results = analyze_space_occupancy(spaces, clean)
    free = get_free_count(results)
    total = len(results)
    display = draw_results(use.copy(), results)
    tag = "OK" if ok else "RAW"
    cv2.putText(display, f"[{tag}] Free: {free}/{total}",
        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    small = cv2.resize(display, None, fx=0.5, fy=0.5)
    cv2.imshow("Smart Parking Live", small)
    if cv2.waitKey(200) & 0xFF == ord("q"):
        break
picam2.stop()
cv2.destroyAllWindows()
print("Done")
